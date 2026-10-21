"""Generatore musicale: basi originali sintetizzate al volo, niente copyright.

Ogni preset è un genere con il suo tempo, i suoi strumenti e il suo groove.
Il seme cambia accordi e variazioni, così ogni Reel suona un po' diverso.
"""

import wave
from pathlib import Path

import numpy as np

SR = 44100


def midi(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


# ------------------------------------------------------------- strumenti

def _t(n):
    return np.arange(n) / SR


def epiano(f, n, vel=1.0):
    """Piano elettrico tipo Rhodes (sintesi FM)."""
    t = _t(n)
    idx = 1.6 * np.exp(-t * 6)
    tone = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    tine = 0.12 * np.sin(2 * np.pi * f * 14 * t) * np.exp(-t * 30)
    env = np.exp(-t * 1.8) * np.minimum(1, t / 0.004)
    return vel * (tone + tine) * env


def pluck(f, n, vel=1.0, bright=1.0):
    """Corda pizzicata: armoniche che si spengono prima le alte."""
    t = _t(n)
    out = np.zeros(n)
    for k in range(1, 14):
        out += np.sin(2 * np.pi * k * f * t) / k * np.exp(-t * (3 + k * 2.5 / bright))
    return vel * out * np.minimum(1, t / 0.002)


def bell(f, n, vel=1.0):
    """Carillon / campanella."""
    t = _t(n)
    out = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 4) + 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 9)
    return vel * out * np.exp(-t * 2.2) * np.minimum(1, t / 0.002)


def pad(freqs, n, attack=0.4, release=0.6, bright=4):
    """Tappeto di saw leggermente scordate."""
    t = _t(n)
    out = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.0, 0.11):
            ff = f * 2 ** (det / 12)
            for k in range(1, bright + 1):
                out += np.sin(2 * np.pi * k * ff * t + k) / k
    env = np.minimum(1, t / attack) * np.minimum(1, np.maximum(0, (n / SR - t)) / release)
    return out * env / (len(freqs) * 3)


def bass(f, n, vel=1.0, drive=1.5):
    t = _t(n)
    tone = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    env = np.minimum(1, t / 0.005) * np.minimum(1, np.maximum(0, n / SR - t) / 0.03)
    return vel * np.tanh(drive * tone) * env


def kick(n, punch=1.0):
    t = _t(n)
    freq = 48 + 120 * punch * np.exp(-t * 35)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 7) + 0.3 * np.exp(-t * 300)


def snare(n, rng, tone=180):
    t = _t(n)
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=0)
    return 0.6 * noise * np.exp(-t * 22) + 0.5 * np.sin(2 * np.pi * tone * t) * np.exp(-t * 30)


def clap(n, rng):
    t = _t(n)
    noise = np.diff(rng.standard_normal(n), prepend=0)
    env = sum(np.exp(-np.maximum(0, t - d) * 80) * (t >= d) for d in (0, 0.01, 0.02)) * np.exp(-t * 12)
    return noise * env * 0.6


def hat(n, rng, decay=60):
    t = _t(n)
    noise = np.diff(np.diff(rng.standard_normal(n + 2)))
    return noise * np.exp(-t * decay) * 0.5


# --------------------------------------------------------------- effetti

def lowpass(x, cutoff):
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    spec *= 1 / np.sqrt(1 + (freqs / cutoff) ** 4)
    return np.fft.irfft(spec, len(x))


def reverb(x, seconds=1.8, mix=0.25, seed=0):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * (6.9 / seconds))
    ir = lowpass(ir, 5000)
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    wet /= np.max(np.abs(wet)) + 1e-9
    return x * (1 - mix) + wet * mix * np.max(np.abs(x))


def vinyl(n, rng):
    crackle = (rng.random(n) > 0.9993) * rng.uniform(-1, 1, n)
    hiss = lowpass(rng.standard_normal(n), 6000) * 0.02
    return crackle * 0.12 + hiss * 0.5


class Track:
    def __init__(self, seconds, bpm, seed):
        self.bpm = bpm
        self.beat = 60 / bpm
        self.n = int(seconds * SR)
        self.rng = np.random.default_rng(seed)
        self.buses: dict[str, np.ndarray] = {}

    def add(self, bus, time_s, sound, gain=1.0):
        buf = self.buses.setdefault(bus, np.zeros(self.n + SR * 4))
        start = int(time_s * SR)
        if start >= self.n:
            return
        end = min(len(buf), start + len(sound))
        buf[start:end] += gain * sound[: end - start]

    def get(self, bus):
        return self.buses.get(bus, np.zeros(self.n + SR * 4))[: self.n]

    def steps(self, bars, per_beat=4):
        """Tutte le posizioni a sedicesimi: (battuta, step, tempo in secondi)."""
        step = self.beat / per_beat
        total = int(self.n / SR / step) + 1
        for i in range(total):
            yield i // (per_beat * 4), i % (per_beat * 4), i * step


# ---------------------------------------------------------------- preset
# Accordi in semitoni MIDI (voicing già pronto)

PROGS = {
    "minor_soul": [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 65]],  # Am7 Fmaj7 Cmaj7 G7
    "dreamy": [[50, 53, 57, 60], [55, 59, 62, 65], [48, 52, 55, 59], [45, 48, 52, 55]],  # Dm7 G7 Cmaj7 Am7
    "pop": [[48, 52, 55], [55, 59, 62], [57, 60, 64], [53, 57, 60]],  # C G Am F
    "epic": [[45, 48, 52], [41, 45, 48], [48, 52, 55], [43, 47, 50]],  # Am F C G
    "mystery": [[45, 48, 52], [45, 48, 53], [44, 48, 52], [45, 48, 52]],  # Am Am(b6) E+ Am
}

# Variazioni del brano "mystery": stessa atmosfera, accordi e melodie diverse
MYSTERY_VARIANTS = [
    (PROGS["mystery"], [0, 2, 1, 2, 0, 2, 1, 3]),
    ([[50, 53, 57], [50, 53, 58], [49, 53, 57], [50, 53, 57]], [0, 1, 2, 1, 3, 2, 1, 2]),  # Dm Dm(b6) C#+ Dm
    ([[45, 48, 52], [41, 45, 48], [43, 46, 50], [40, 44, 47]], [0, 2, 1, 3, 0, 2, 1, 2]),  # Am F Gm E
    ([[52, 55, 59], [48, 52, 55], [53, 57, 60], [51, 55, 59]], [2, 1, 0, 1, 2, 3, 1, 0]),  # Em C F B+
]


def lofi(tr: Track, seed):
    prog = PROGS["minor_soul" if seed % 2 == 0 else "dreamy"]
    swing = tr.beat / 4 * 0.33
    for bar, s, t in tr.steps(None):
        chord = prog[bar % len(prog)]
        tt = t + (swing if s % 2 == 1 else 0)
        if s == 0:
            for i, note in enumerate(chord):
                tr.add("keys", tt + i * 0.012, epiano(midi(note), int(SR * tr.beat * 3.8), 0.5))
            tr.add("bass", tt, bass(midi(chord[0] - 12), int(SR * tr.beat * 1.6), 0.9, 1.2))
        if s == 10:
            tr.add("bass", tt, bass(midi(chord[0] - 12 + 7), int(SR * tr.beat * 0.9), 0.7, 1.2))
        if s in (0, 7, 10) and not (s == 7 and bar % 2):
            tr.add("drums", tt, kick(int(SR * 0.5), 0.8), 0.9)
        if s in (4, 12):
            tr.add("drums", tt, snare(int(SR * 0.4), tr.rng, 200), 0.45)
        if s % 2 == 0:
            tr.add("drums", tt, hat(int(SR * 0.08), tr.rng, 70), 0.18 if s % 4 else 0.28)
    keys = reverb(lowpass(tr.get("keys"), 3200), 2.2, 0.3)
    drums = lowpass(tr.get("drums"), 7000)
    mix = keys * 0.55 + tr.get("bass") * 0.4 + drums * 0.6 + vinyl(tr.n, tr.rng)
    return mix


def curious_pop(tr: Track, seed):
    prog = PROGS["pop"]
    arp = [0, 1, 2, 1, 2, 0, 1, 2]
    for bar, s, t in tr.steps(None):
        chord = prog[bar % len(prog)]
        if s % 2 == 0:
            note = chord[arp[(s // 2) % len(arp)]] + 12
            tr.add("pluck", t, pluck(midi(note), int(SR * 0.6), 0.55, 1.4))
        if s == 0:
            tr.add("pad", t, pad([midi(n) for n in chord], int(SR * tr.beat * 4), 0.2, 0.3, 3))
        if s in (0, 6, 8, 14):
            tr.add("bass", t, bass(midi(chord[0] - 12), int(SR * tr.beat * 0.45), 0.8, 2.0))
        if s in (0, 8):
            tr.add("drums", t, kick(int(SR * 0.4), 1.0))
        if s in (4, 12):
            tr.add("drums", t, clap(int(SR * 0.3), tr.rng), 0.7)
        if s % 2 == 1:
            tr.add("drums", t, hat(int(SR * 0.05), tr.rng, 90), 0.2)
    plk = reverb(tr.get("pluck"), 1.2, 0.2)
    return plk * 0.45 + lowpass(tr.get("pad"), 2500) * 0.25 + tr.get("bass") * 0.35 + tr.get("drums") * 0.55


def documentary(tr: Track, seed):
    prog = PROGS["epic"]
    for bar, s, t in tr.steps(None):
        chord = prog[(bar // 2) % len(prog)]
        if s == 0 and bar % 2 == 0:
            tr.add("pad", t, pad([midi(n) for n in chord] + [midi(chord[0] + 12)], int(SR * tr.beat * 8.2), 1.2, 1.0, 5))
        # pulsazione di basso a ottavi, tipica dei documentari
        if s % 2 == 0:
            tr.add("bass", t, bass(midi(chord[0] - 12), int(SR * tr.beat * 0.4), 0.5 + 0.2 * (s % 8 == 0), 2.5))
        if s == 0 and bar % 2 == 0:
            tr.add("hits", t, kick(int(SR * 1.2), 0.5), 1.0)
        if s % 4 == 2 and bar % 4 >= 2:
            tr.add("hits", t, hat(int(SR * 0.06), tr.rng, 80), 0.15)
        if s in (0, 6, 12) and bar % 2 == 1:
            tr.add("bells", t, bell(midi(chord[2] + 24 - (s == 6) * 3), int(SR * 2), 0.25))
    pads = reverb(lowpass(tr.get("pad"), 1800), 3.0, 0.35)
    return pads * 0.5 + lowpass(tr.get("bass"), 900) * 0.45 + tr.get("hits") * 0.6 + reverb(tr.get("bells"), 2.5, 0.4) * 0.5


def chill_house(tr: Track, seed):
    prog = PROGS["dreamy"]
    kick_env = np.ones(tr.n + SR * 4)
    for bar, s, t in tr.steps(None):
        chord = prog[bar % len(prog)]
        if s % 4 == 0:
            tr.add("drums", t, kick(int(SR * 0.35), 1.1))
            i = int(t * SR)
            k = int(SR * tr.beat * 0.6)
            kick_env[i:i + k] = np.minimum(kick_env[i:i + k], np.linspace(0.25, 1, k) ** 0.6)
        if s % 4 == 2:
            tr.add("drums", t, hat(int(SR * 0.12), tr.rng, 30), 0.3)
            tr.add("stab", t, sum(epiano(midi(n + 12), int(SR * 0.35), 0.4) for n in chord))
        if s in (4, 12):
            tr.add("drums", t, clap(int(SR * 0.3), tr.rng), 0.4)
        if s in (2, 6, 10, 14):
            tr.add("bass", t, bass(midi(chord[0] - 12), int(SR * tr.beat * 0.4), 0.8, 1.8))
        if s == 0:
            tr.add("pad", t, pad([midi(n) for n in chord], int(SR * tr.beat * 4), 0.6, 0.6, 3))
    duck = kick_env[: tr.n]
    stab = reverb(tr.get("stab"), 1.5, 0.3)
    return (stab * 0.4 + lowpass(tr.get("pad"), 1500) * 0.3 + tr.get("bass") * 0.35) * duck + tr.get("drums") * 0.5


def mystery(tr: Track, seed):
    prog, pattern = MYSTERY_VARIANTS[seed % len(MYSTERY_VARIANTS)]
    for bar, s, t in tr.steps(None):
        chord = prog[bar % len(prog)]
        if s % 2 == 0:
            idx = pattern[(s // 2) % len(pattern)]
            note = chord[min(idx, len(chord) - 1)] + 24 + (12 if idx == 3 else 0)
            tr.add("bells", t, bell(midi(note), int(SR * 1.5), 0.35))
        if s == 0:
            tr.add("pad", t, pad([midi(chord[0] - 12), midi(chord[0])], int(SR * tr.beat * 4.2), 1.0, 0.8, 4))
        if s in (0, 10):
            tr.add("drums", t, kick(int(SR * 0.6), 0.6), 0.7)
        if s == 8:
            tr.add("drums", t, snare(int(SR * 0.5), tr.rng, 160), 0.25)
    bells = reverb(tr.get("bells"), 2.8, 0.45)
    return bells * 0.45 + reverb(lowpass(tr.get("pad"), 900), 3, 0.3) * 0.45 + lowpass(tr.get("drums"), 4000) * 0.5


PRESETS = {
    "lofi": (lofi, 82),
    "curious_pop": (curious_pop, 112),
    "documentary": (documentary, 96),
    "chill_house": (chill_house, 120),
    "mystery": (mystery, 76),
}


def make_track(path: Path, seconds: float, seed: int = 0, preset: str = "lofi") -> Path:
    fn, bpm = PRESETS.get(preset, PRESETS["lofi"])
    tr = Track(seconds, bpm + (seed % 3 - 1) * 4, seed)
    out = fn(tr, seed)[: tr.n]
    # dissolvenze, compressione morbida e normalizzazione
    fade_in, fade_out = int(SR * 0.3), int(SR * 1.5)
    out[:fade_in] *= np.linspace(0, 1, fade_in)
    out[-fade_out:] *= np.linspace(1, 0, fade_out)
    out = np.tanh(out / (np.percentile(np.abs(out), 99.5) + 1e-9) * 0.9)
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.89
    pcm = (out * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path
