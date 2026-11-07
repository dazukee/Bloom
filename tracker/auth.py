"""User accounts: sign-up rules, password hashing, login, lockout, recovery codes.

Pure logic: no customtkinter, no file access. Functions that change an account
change the `users` dict in place; the app then saves it with storage.py.

Security rules (OWASP Password Storage Cheat Sheet):
    - Never store a password or recovery code, only a salted hash of it.
    - Hash with PBKDF2-HMAC-SHA256 and PBKDF2_ITERATIONS rounds.
    - Use a new random salt for every secret.
    - Compare hashes with hmac.compare_digest, never with ==.
    - A wrong username and a wrong password get the same message.

Shapes (storage.py converts dates and times to and from text):
    users = {"version": 1, "users": [user, ...], "last_username": str | None}
    user = {
        "user_id": "u_3f9a1c2b", "username": "maria_c", "created_on": date,
        "password": {"salt": hex, "hash": hex, "iterations": int},
        "recovery": {"salt": hex, "hash": hex, "iterations": int},
        "failed_attempts": int, "locked_until": datetime | None,
    }
"""

import hashlib
import hmac
import math
import secrets
from datetime import date, datetime, timedelta

PBKDF2_ITERATIONS = 600_000  # OWASP's figure for PBKDF2-HMAC-SHA256.
SALT_BYTES = 16
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 20
PASSWORD_MIN_LENGTH = 8
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 30
# No 0/O or 1/I/L, so a code copied by hand is not misread.
RECOVERY_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
RECOVERY_CODE_GROUPS = 3
RECOVERY_CODE_GROUP_LENGTH = 4

LOGIN_FAILED = "Incorrect username or password."
RECOVERY_FAILED = "Incorrect username or recovery code."
WRONG_CURRENT_PASSWORD = "Your current password is incorrect."


class AuthError(Exception):
    """A sign-up, login or recovery problem; str(error) is shown to the user."""


def check_username_rules(username: str) -> None:
    """Check a new username: 3-20 letters, digits or "_" (T23, T24).

    Raises:
        ValueError: "Username must be 3 to 20 characters." or
            "Username can only use letters, numbers and _."
    """
    if not USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH:
        raise ValueError("Username must be 3 to 20 characters.")
    for character in username:
        is_plain = character.isascii() and character.isalnum()
        if not (is_plain or character == "_"):
            raise ValueError("Username can only use letters, numbers and _.")


def check_password_rules(password: str, confirm: str) -> None:
    """Check a new password and its confirmation (T25, T26).

    Raises:
        ValueError: "Password must be at least 8 characters.",
            "Password needs at least one letter and one number." or
            "Passwords do not match."
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError("Password must be at least 8 characters.")
    has_letter = False
    has_digit = False
    for character in password:
        if character.isalpha():
            has_letter = True
        elif character.isdigit():
            has_digit = True
    if not (has_letter and has_digit):
        raise ValueError("Password needs at least one letter and one number.")
    if password != confirm:
        raise ValueError("Passwords do not match.")


def password_strength(password: str) -> int:
    """Return a rough strength, 0 (weak) to 3 (strong), to encourage longer passwords.

    Length matters most (OWASP); a mix of character kinds helps a little. The
    rules for accepting a password are in check_password_rules.
    """
    kinds = sum(
        (
            any(c.islower() for c in password),
            any(c.isupper() for c in password),
            any(c.isdigit() for c in password),
            any(not c.isalnum() for c in password),
        )
    )
    if len(password) < PASSWORD_MIN_LENGTH or kinds < 2:
        return 0
    if len(password) >= 16 or (len(password) >= 12 and kinds >= 3):
        return 3
    if len(password) >= 12 or kinds >= 3:
        return 2
    return 1


def find_user(users: dict, username: str) -> dict | None:
    """Return the account with this username, ignoring capitals and outer spaces."""
    wanted = username.strip().lower()
    for user in users["users"]:
        if user["username"].lower() == wanted:
            return user
    return None


def make_user_id(users: dict) -> str:
    """Return a new id such as "u_3f9a1c2b" that no account uses yet."""
    taken = {user["user_id"] for user in users["users"]}
    while True:
        user_id = "u_" + secrets.token_hex(4)
        if user_id not in taken:
            return user_id


def hash_secret(secret: str, salt: bytes, iterations: int) -> str:
    """Return the PBKDF2-HMAC-SHA256 hash of a password or code, as hex text."""
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
    return digest.hex()


def make_secret_record(secret: str) -> dict:
    """Return {"salt", "hash", "iterations"} for a new secret, with a fresh salt.

    PBKDF2_ITERATIONS is read when called, so tests can lower it to run fast.
    """
    salt = secrets.token_bytes(SALT_BYTES)
    iterations = PBKDF2_ITERATIONS
    return {
        "salt": salt.hex(),
        "hash": hash_secret(secret, salt, iterations),
        "iterations": iterations,
    }


def secret_matches(secret: str, record: dict | None) -> bool:
    """Return True when the secret produces the hash stored in the record."""
    if not record:
        return False
    salt = bytes.fromhex(record["salt"])
    candidate = hash_secret(secret, salt, record["iterations"])
    return hmac.compare_digest(candidate, record["hash"])


def make_recovery_code() -> str:
    """Return a new one-time recovery code such as "7KQ2-M9XD-4TPH"."""
    groups = []
    for _ in range(RECOVERY_CODE_GROUPS):
        group = ""
        for _ in range(RECOVERY_CODE_GROUP_LENGTH):
            group += secrets.choice(RECOVERY_CODE_ALPHABET)
        groups.append(group)
    return "-".join(groups)


def normalize_recovery_code(text: str) -> str:
    """Return a typed code in the form that gets hashed (T30).

    " 7kq2 m9xd-4tph " gives "7KQ2M9XD4TPH".
    """
    return text.upper().replace(" ", "").replace("-", "")


def register_user(
    users: dict, username: str, password: str, confirm: str, today: date
) -> tuple[dict, str]:
    """Create an account and return it with its first recovery code (T21, T22).

    The code is shown once on screen and never stored.

    Raises:
        ValueError: From the rule checks.
        AuthError: "That username is taken."
    """
    username = username.strip()
    check_username_rules(username)
    check_password_rules(password, confirm)
    if find_user(users, username) is not None:
        raise AuthError("That username is taken.")
    code = make_recovery_code()
    user = {
        "user_id": make_user_id(users),
        "username": username,
        "created_on": today,
        "password": make_secret_record(password),
        "recovery": make_secret_record(normalize_recovery_code(code)),
        "failed_attempts": 0,
        "locked_until": None,
    }
    users["users"].append(user)
    return user, code


def _check_not_locked(user: dict, now: datetime) -> None:
    """Raise AuthError while the account is locked after too many attempts."""
    locked_until = user.get("locked_until")
    if locked_until is not None and locked_until > now:
        seconds = math.ceil((locked_until - now).total_seconds())
        raise AuthError(f"Too many attempts. Try again in {seconds} seconds.")


def _record_failure(user: dict, now: datetime) -> None:
    """Count a failed attempt; lock the account at MAX_FAILED_ATTEMPTS."""
    user["failed_attempts"] = user.get("failed_attempts", 0) + 1
    if user["failed_attempts"] >= MAX_FAILED_ATTEMPTS:
        user["locked_until"] = now + timedelta(seconds=LOCKOUT_SECONDS)
        user["failed_attempts"] = 0


def check_login(users: dict, username: str, password: str, now: datetime) -> dict:
    """Return the account when the username and password are right (T27, T28).

    Steps:
        1. Unknown username: AuthError(LOGIN_FAILED), after hashing anyway so
           both failures take about the same time.
        2. Locked until after `now`: AuthError("Too many attempts...").
        3. Wrong password: count it; 5 failures lock the account for 30 s.
        4. Right password: reset the counters and return the user.
    The app saves `users` after every attempt so a restart keeps the lockout.
    """
    user = find_user(users, username)
    if user is None:
        hash_secret(password, b"timing-equaliser", PBKDF2_ITERATIONS)
        raise AuthError(LOGIN_FAILED)
    _check_not_locked(user, now)
    if not secret_matches(password, user["password"]):
        _record_failure(user, now)
        raise AuthError(LOGIN_FAILED)
    user["failed_attempts"] = 0
    user["locked_until"] = None
    return user


def reset_password_with_code(
    users: dict,
    username: str,
    code: str,
    new_password: str,
    confirm: str,
    now: datetime,
) -> str:
    """Set a new password with the recovery code; return the next code (T29).

    The new password's rules are checked first, so a typo there is not a
    failed attempt. A wrong code counts toward the same lockout as login.
    """
    check_password_rules(new_password, confirm)
    user = find_user(users, username)
    if user is None:
        hash_secret(code, b"timing-equaliser", PBKDF2_ITERATIONS)
        raise AuthError(RECOVERY_FAILED)
    _check_not_locked(user, now)
    if not secret_matches(normalize_recovery_code(code), user["recovery"]):
        _record_failure(user, now)
        raise AuthError(RECOVERY_FAILED)
    user["password"] = make_secret_record(new_password)
    next_code = make_recovery_code()
    user["recovery"] = make_secret_record(normalize_recovery_code(next_code))
    user["failed_attempts"] = 0
    user["locked_until"] = None
    return next_code


def change_password(
    user: dict, current_password: str, new_password: str, confirm: str
) -> None:
    """Replace the logged-in user's password after checking the current one."""
    if not secret_matches(current_password, user["password"]):
        raise AuthError(WRONG_CURRENT_PASSWORD)
    check_password_rules(new_password, confirm)
    user["password"] = make_secret_record(new_password)


def regenerate_recovery_code(user: dict, password: str) -> str:
    """Replace the logged-in user's recovery code and return the new one."""
    if not secret_matches(password, user["password"]):
        raise AuthError(WRONG_CURRENT_PASSWORD)
    code = make_recovery_code()
    user["recovery"] = make_secret_record(normalize_recovery_code(code))
    return code


def delete_account(users: dict, user: dict, password: str) -> None:
    """Remove an account after checking its password."""
    if not secret_matches(password, user["password"]):
        raise AuthError(WRONG_CURRENT_PASSWORD)
    users["users"] = [u for u in users["users"] if u["user_id"] != user["user_id"]]
