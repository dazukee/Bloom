"""Plays the sounds from tracker/sound.py, following the user's settings.

Sounds are written once to a temporary folder as WAV files. winsound plays them
on Windows and afplay on a Mac; any other system stays silent.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from tracker import sound

_folder = Path(tempfile.gettempdir()) / "bloom-sounds"
_settings = {
    "sound_on": True,
    "sound_volume": 60,
    "sound_pack": "chimes",
    "sound_clicks": True,
    "sound_alerts": True,
    "sound_celebrate": True,
}


def configure(settings: dict) -> None:
    """Copy the sound settings from the user's preferences."""
    for key in _settings:
        _settings[key] = settings[key]


def _path_for(event: str) -> Path:
    """Return the WAV file for an event, creating it the first time."""
    pack, volume = _settings["sound_pack"], _settings["sound_volume"]
    path = _folder / f"{pack}-{event}-{volume}.wav"
    if not path.exists():
        _folder.mkdir(exist_ok=True)
        path.write_bytes(sound.render(event, pack, volume))
    return path


def play(event: str) -> None:
    """Play an event's sound if its switches allow; a sound never crashes the app."""
    if not _settings["sound_on"] or not _settings[sound.CATEGORIES[event]]:
        return
    try:
        path = _path_for(event)
        if sys.platform == "win32":
            import winsound

            flags = winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT
            winsound.PlaySound(str(path), flags)
        elif sys.platform == "darwin":
            subprocess.Popen(["afplay", str(path)])
    except (OSError, RuntimeError):
        pass


def with_sound(command, event: str):
    """Return `command` wrapped so it plays a sound first; None stays None."""
    if command is None:
        return None

    def run(*args):
        play(event)
        return command(*args)

    return run
