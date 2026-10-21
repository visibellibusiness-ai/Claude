"""Base musicale generata al volo: niente problemi di copyright."""

import wave
from pathlib import Path

import numpy as np

RATE = 44100
NOTES = {"A": 220.00, "C": 261.63, "D": 293.66, "E": 329.63, "F": 349.23, "G": 392.00, "B": 246.94}
PROGRESSIONS = [
    [("A", "C", "E"), ("F", "A", "C"), ("C", "E", "G"), ("G", "B", "D")],
    [("C", "E", "G"), ("A", "C", "E"), ("F", "A", "C"), ("G", "B", "D")],
    [("F", "A", "C"), ("G", "B", "D"), ("A", "C", "E"), ("E", "G", "B")],
]


def _pad(freqs, n):
    t = np.arange(n) / RATE
    tone = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) for f in freqs)
    env = np.minimum(1, t / 0.15) * np.minimum(1, (n / RATE - t) / 0.3)
    return tone * env / len(freqs)


def _kick(n):
    t = np.arange(n) / RATE
    freq = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(freq) / RATE) * np.exp(-t * 9)


def _hat(n, rng):
    t = np.arange(n) / RATE
    noise = np.diff(rng.standard_normal(n + 1))  # rumore "chiaro"
    return noise * np.exp(-t * 60)


def make_track(path: Path, seconds: float, seed: int = 0, bpm: int = 88) -> Path:
    rng = np.random.default_rng(seed)
    beat = int(RATE * 60 / bpm)
    bar = beat * 4
    total = int(seconds * RATE) + bar
    out = np.zeros(total)
    prog = PROGRESSIONS[seed % len(PROGRESSIONS)]
    i = 0
    for start in range(0, total, bar):
        n = min(bar, total - start)
        out[start:start + n] += 0.32 * _pad([NOTES[x] for x in prog[i % len(prog)]], n)
        for b in range(4):
            s = start + b * beat
            if s >= total:
                break
            m = min(beat, total - s)
            if b in (0, 2):
                out[s:s + m] += 0.55 * _kick(m)
            h = s + beat // 2
            if h < total:
                k = min(beat // 2, total - h)
                out[h:h + k] += 0.05 * _hat(k, rng)
        i += 1
    out = out[: int(seconds * RATE)]
    fade = int(RATE * 1.5)
    out[-fade:] *= np.linspace(1, 0, fade)
    out[: RATE // 2] *= np.linspace(0, 1, RATE // 2)
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.8
    pcm = (out * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    return path
