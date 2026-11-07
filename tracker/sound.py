"""Sound effects made from math: no audio files, just sine and square waves.

Pure logic: no customtkinter, no file access. A sound is a list of notes
(frequency in Hz, length in ms). Each note is turned into samples that fade out,
and render() packs them into WAV bytes that ui/sfx.py can play.
"""

import io
import math
import struct
import wave

SAMPLE_RATE = 22050
PEAK = 32767  # the largest value in 16-bit audio

# event: the notes it plays
SOUNDS = {
    "click": [(880, 35)],
    "toggle": [(660, 30), (990, 40)],
    "nav": [(587, 60)],
    "success": [(659, 80), (988, 130)],
    "warning": [(330, 110), (262, 170)],
    "celebrate": [(523, 90), (659, 90), (784, 90), (1047, 260)],
    "login": [(392, 90), (587, 90), (784, 200)],
    "logout": [(587, 90), (392, 170)],
    "breath": [(294, 340)],
}
# pack: (name, wave shape, frequency multiplier, loudness)
PACKS = {
    "chimes": ("Soft Chimes", "sine", 1.0, 0.8),
    "marimba": ("Marimba", "triangle", 0.75, 0.9),
    "retro": ("Retro 8-bit", "square", 1.0, 0.3),
}
# Which switch in Settings controls each event.
CATEGORIES = {
    "click": "sound_clicks",
    "toggle": "sound_clicks",
    "nav": "sound_clicks",
    "success": "sound_alerts",
    "warning": "sound_alerts",
    "login": "sound_alerts",
    "logout": "sound_alerts",
    "celebrate": "sound_celebrate",
    "breath": "sound_celebrate",
}


def wave_value(shape: str, phase: float) -> float:
    """Return a wave's height (-1 to 1) at a phase measured in whole cycles."""
    part = phase % 1.0
    if shape == "square":
        return 1.0 if part < 0.5 else -1.0
    if shape == "triangle":
        return 4 * abs(part - 0.5) - 1
    return math.sin(2 * math.pi * part)


def note_samples(
    frequency: float, length_ms: int, shape: str, volume: float
) -> list[int]:
    """Return one note's 16-bit samples: a quick attack, then a smooth fade."""
    count = SAMPLE_RATE * length_ms // 1000
    samples = []
    for index in range(count):
        attack = min(1.0, index / (SAMPLE_RATE * 0.004))
        fade = (1 - index / count) ** 2
        height = wave_value(shape, frequency * index / SAMPLE_RATE)
        samples.append(round(PEAK * volume * attack * fade * height))
    return samples


def render(event: str, pack: str, volume_percent: int) -> bytes:
    """Return a complete WAV file, as bytes, for an event in a sound pack."""
    _, shape, pitch, loudness = PACKS[pack]
    volume = max(0, min(volume_percent, 100)) / 100 * loudness
    samples = []
    for frequency, length_ms in SOUNDS[event]:
        samples += note_samples(frequency * pitch, length_ms, shape, volume)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(SAMPLE_RATE)
        file.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buffer.getvalue()
