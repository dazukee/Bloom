"""Reading aloud: the app's stand-in for a screen reader.

Tkinter windows cannot talk to screen readers such as Narrator, so Bloom speaks
for itself. On Windows one PowerShell helper stays open and speaks each line it is
sent, using the voice built into Windows; a Mac uses `say`. Text goes through the
helper's standard input, never onto a command line, so nothing typed can run as a
command. If speech is not available, these functions quietly do nothing.
"""

import subprocess
import sys

# Reads one line at a time. Each new line interrupts the one being spoken.
WINDOWS_SCRIPT = (
    "Add-Type -AssemblyName System.Speech;"
    "$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
    "[Console]::InputEncoding = [System.Text.Encoding]::UTF8;"
    "while (($line = [Console]::In.ReadLine()) -ne $null) {"
    "$voice.SpeakAsyncCancelAll();"
    "if ($line) { [void]$voice.SpeakAsync($line) }"
    "}"
)
_helper: subprocess.Popen | None = None


def _start_helper() -> subprocess.Popen | None:
    """Start the Windows speech helper once; return None if it cannot start."""
    global _helper
    if _helper is not None and _helper.poll() is None:
        return _helper
    try:
        _helper = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", WINDOWS_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except OSError:
        _helper = None
    return _helper


def available() -> bool:
    """Return True on the systems Bloom can speak on."""
    return sys.platform in ("win32", "darwin")


def speak(text: str) -> None:
    """Say `text`, interrupting anything being said now."""
    clean = " ".join(text.split())
    if not clean:
        return
    if sys.platform == "win32":
        helper = _start_helper()
        if helper is None:
            return
        try:
            helper.stdin.write((clean + "\n").encode("utf-8"))
            helper.stdin.flush()
        except OSError:
            pass
    elif sys.platform == "darwin":
        try:
            subprocess.Popen(["say", clean])
        except OSError:
            pass


def stop() -> None:
    """Stop speaking now."""
    if sys.platform == "win32" and _helper is not None and _helper.poll() is None:
        try:
            _helper.stdin.write(b"\n")
            _helper.stdin.flush()
        except OSError:
            pass


def shut_down() -> None:
    """Close the helper when the program exits."""
    global _helper
    if _helper is not None:
        try:
            _helper.stdin.close()
            _helper.terminate()
        except OSError:
            pass
        _helper = None
