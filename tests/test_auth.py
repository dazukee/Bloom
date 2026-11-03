"""Tests for tracker/auth.py. Hashing is made fast with monkeypatch."""

from datetime import date, datetime, timedelta

import pytest

from tracker import auth, storage

NOW = datetime(2026, 10, 31, 9, 0)
TODAY = NOW.date()


@pytest.fixture(autouse=True)
def fast_hashing(monkeypatch):
    monkeypatch.setattr(auth, "PBKDF2_ITERATIONS", 1_000)


@pytest.fixture
def users():
    accounts = storage.new_users()
    auth.register_user(accounts, "maria_c", "secret123", "secret123", TODAY)
    return accounts


def test_t21_register_returns_code():
    accounts = storage.new_users()
    user, code = auth.register_user(accounts, "ana_r", "secret123", "secret123", TODAY)
    groups = code.split("-")
    assert len(groups) == 3 and all(len(g) == 4 for g in groups)
    assert user in accounts["users"]


def test_t22_username_taken_ignoring_case(users):
    with pytest.raises(auth.AuthError, match="That username is taken."):
        auth.register_user(users, "Maria_C", "secret123", "secret123", TODAY)


def test_t23_username_length():
    with pytest.raises(ValueError, match="3 to 20 characters"):
        auth.check_username_rules("ab")


def test_t24_username_characters():
    with pytest.raises(ValueError, match="letters, numbers and _"):
        auth.check_username_rules("maria c")


def test_t25_short_password():
    with pytest.raises(ValueError, match="at least 8 characters"):
        auth.check_password_rules("short1", "short1")


def test_t26_password_needs_letter_and_number():
    with pytest.raises(ValueError, match="one letter and one number"):
        auth.check_password_rules("password", "password")


def test_passwords_must_match():
    with pytest.raises(ValueError, match="do not match"):
        auth.check_password_rules("secret123", "secret124")


def test_t27_same_message_for_unknown_user_and_wrong_password(users):
    with pytest.raises(auth.AuthError) as wrong_password:
        auth.check_login(users, "maria_c", "wrong1234", NOW)
    with pytest.raises(auth.AuthError) as unknown_user:
        auth.check_login(users, "nobody", "secret123", NOW)
    assert str(wrong_password.value) == str(unknown_user.value) == auth.LOGIN_FAILED


def test_t28_lockout_after_five_failures(users):
    for _ in range(5):
        with pytest.raises(auth.AuthError):
            auth.check_login(users, "maria_c", "wrong1234", NOW)
    with pytest.raises(
        auth.AuthError, match="Too many attempts. Try again in 30 seconds."
    ):
        auth.check_login(users, "maria_c", "secret123", NOW)
    later = NOW + timedelta(seconds=30)
    assert (
        auth.check_login(users, "maria_c", "secret123", later)["username"] == "maria_c"
    )


def test_t29_recovery_code_works_once():
    accounts = storage.new_users()
    _, code = auth.register_user(accounts, "ana_r", "secret123", "secret123", TODAY)
    next_code = auth.reset_password_with_code(
        accounts, "ana_r", code, "newpass99", "newpass99", NOW
    )
    assert auth.check_login(accounts, "ana_r", "newpass99", NOW)
    with pytest.raises(auth.AuthError, match="recovery code"):
        auth.reset_password_with_code(
            accounts, "ana_r", code, "other9999", "other9999", NOW
        )
    assert auth.reset_password_with_code(
        accounts, "ana_r", next_code, "other9999", "other9999", NOW
    )


def test_t30_code_normalized():
    accounts = storage.new_users()
    _, code = auth.register_user(accounts, "ana_r", "secret123", "secret123", TODAY)
    messy = " " + code.lower().replace("-", " ") + " "
    assert auth.reset_password_with_code(
        accounts, "ana_r", messy, "newpass99", "newpass99", NOW
    )


def test_same_password_different_hashes():
    accounts = storage.new_users()
    first, _ = auth.register_user(accounts, "ana_r", "secret123", "secret123", TODAY)
    second, _ = auth.register_user(accounts, "bea_s", "secret123", "secret123", TODAY)
    assert first["password"]["hash"] != second["password"]["hash"]


def test_change_password_and_delete(users):
    user = users["users"][0]
    with pytest.raises(auth.AuthError, match="current password"):
        auth.change_password(user, "nope12345", "newpass99", "newpass99")
    auth.change_password(user, "secret123", "newpass99", "newpass99")
    assert auth.check_login(users, "maria_c", "newpass99", NOW)
    new_code = auth.regenerate_recovery_code(user, "newpass99")
    assert len(new_code) == 14
    auth.delete_account(users, user, "newpass99")
    assert users["users"] == []


def test_created_on_is_today(users):
    assert users["users"][0]["created_on"] == date(2026, 10, 31)
