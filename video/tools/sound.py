"""Tonspur für den Motion-Film (LokanonMotion, 74 s), komplett per Code erzeugt – keine Fremdaufnahmen, keine Lizenzfragen.

    python tools\\sound.py            -> public/ma/audio/lokanon-motion.wav (48 kHz, Stereo)

Aufbau: ein ruhiges Ambient-Bett (vier Akkorde, weiche Teiltöne, langsames Atmen), darüber kurze Klänge auf die
Schlüsselmomente der Zeitleiste aus public/ma/index.html (gleiche Sekundenangaben). Zurückhaltung nach MOTION-SPEC:
ein Klang je Bewegung, nichts Lautes, nichts Dauerhaftes außer dem Bett.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

SR = 48000
DUR = 74.0
OUT = Path(__file__).resolve().parents[1] / "public" / "ma" / "audio" / "lokanon-motion.wav"
rng = np.random.default_rng(7)

N = int(DUR * SR)
mix = np.zeros((N, 2), dtype=np.float64)


def note(name: str) -> float:
    """Frequenz aus Notennamen, z. B. 'D3', 'Bb3'."""
    names = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
    key, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[key] + 12 * (octave + 1) - 69) / 12)


def env(n: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    """ADSR in Sekunden, Länge n Samples."""
    t = np.arange(n) / SR
    total = n / SR
    e = np.ones(n)
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    if a_n:
        e[:a_n] = np.linspace(0, 1, a_n)
    if d_n:
        e[a_n:a_n + d_n] = np.linspace(1, s, min(d_n, max(0, n - a_n)))
    e[a_n + d_n:] = s
    if r_n and r_n < n:
        e[-r_n:] *= np.linspace(1, 0, r_n)
    return e * (t <= total)


def add(sig: np.ndarray, at: float, gain: float = 1.0, pan: float = 0.0) -> None:
    """Mono-Signal an Zeitpunkt `at` (s) einmischen; pan -1..1."""
    i = int(at * SR)
    if i >= N:
        return
    seg = sig[: N - i]
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    mix[i:i + len(seg), 0] += seg * gain * l
    mix[i:i + len(seg), 1] += seg * gain * r


def reverb(x: np.ndarray, tail: float = 1.2, wet: float = 0.35) -> np.ndarray:
    ir = rng.standard_normal(int(tail * SR)) * np.exp(-np.arange(int(tail * SR)) / SR * 4.0)
    ir[0] = 0
    y = np.fft.irfft(np.fft.rfft(x, len(x) + len(ir)) * np.fft.rfft(ir, len(x) + len(ir)))[: len(x) + len(ir)]
    y /= max(1e-9, np.max(np.abs(y))) / max(1e-9, np.max(np.abs(x)))
    out = np.zeros(len(y))
    out[: len(x)] += x * (1 - wet)
    out += y * wet
    return out


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    """Einfacher Einpol-Tiefpass."""
    a = math.exp(-2 * math.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    b = 1 - a
    for i in range(len(x)):  # kurze Signale, Schleife ist fein
        acc = b * x[i] + a * acc
        y[i] = acc
    return y


def bandnoise(dur: float, f0: float, f1: float) -> np.ndarray:
    """Rauschen, dessen Bandmitte von f0 nach f1 gleitet (Wusch)."""
    n = int(dur * SR)
    x = rng.standard_normal(n)
    chunk = int(0.01 * SR)
    out = np.zeros(n)
    win = np.hanning(chunk * 2)
    for s in range(0, n - chunk, chunk):
        p = s / n
        fc = f0 * (f1 / f0) ** p
        seg = x[s:s + chunk * 2] * win[: len(x[s:s + chunk * 2])]
        spec = np.fft.rfft(seg, chunk * 4)
        freqs = np.fft.rfftfreq(chunk * 4, 1 / SR)
        spec *= np.exp(-((np.log(freqs + 1) - math.log(fc)) ** 2) / (2 * 0.35 ** 2))
        y = np.fft.irfft(spec)[: len(seg)]
        out[s:s + len(y)] += y
    return out / max(1e-9, np.max(np.abs(out)))


# ---------------------------------------------------------------- Klangbausteine
def pluck(freq: float, dur: float = 0.9, bright: float = 1.0) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.35 * bright * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 9) + 0.12 * np.sin(2 * np.pi * freq * 3 * t) * np.exp(-t * 14)
    x *= np.exp(-t * 5.5) * env(n, 0.003, 0, 1, 0.05)
    return reverb(x, 0.9, 0.3)


def tick(freq: float = 2400.0, dur: float = 0.06) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) * np.exp(-t * 90) + 0.4 * rng.standard_normal(n) * np.exp(-t * 160)
    return x * env(n, 0.001, 0, 1, 0.01)


def pop(freq: float = 520.0) -> np.ndarray:
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 0.6 * np.exp(-t * 60))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 28)
    return reverb(x * env(n, 0.002, 0, 1, 0.02), 0.5, 0.2)


def whoosh(dur: float = 1.0, f0: float = 300, f1: float = 2200, shape: float = 0.5) -> np.ndarray:
    x = bandnoise(dur, f0, f1)
    n = len(x)
    t = np.linspace(0, 1, n)
    e = np.exp(-((t - shape) ** 2) / (2 * 0.22 ** 2))
    return reverb(x * e, 0.8, 0.25) * 0.8


def swell(dur: float = 1.4) -> np.ndarray:
    x = bandnoise(dur, 120, 900)
    n = len(x)
    t = np.linspace(0, 1, n)
    return x * np.sin(np.pi * t) ** 2 * 0.5


def chord_hit(freqs: list[float], dur: float = 2.6) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        x += np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 3)
    x *= env(n, 0.02, 0.6, 0.5, 1.4) * np.exp(-t * 1.2)
    return reverb(x / len(freqs), 1.6, 0.45)


# ---------------------------------------------------------------- Ambient-Bett
def pad(chords: list[tuple[float, list[str]]], end: float) -> np.ndarray:
    out = np.zeros(N)
    t_all = np.arange(N) / SR
    for i, (start, names) in enumerate(chords):
        stop = chords[i + 1][0] if i + 1 < len(chords) else end
        n0, n1 = int(start * SR), int(stop * SR)
        seg_n = n1 - n0 + int(2.5 * SR)
        seg_n = min(seg_n, N - n0)
        t = np.arange(seg_n) / SR
        seg = np.zeros(seg_n)
        for name in names:
            f = note(name)
            for k, (det, w) in enumerate([(0, 1.0), (1.003, 0.55), (0.997, 0.55)]):
                ph = rng.uniform(0, 2 * np.pi)
                seg += w * (np.sin(2 * np.pi * f * det * t + ph) + 0.22 * np.sin(2 * np.pi * f * det * 2 * t + ph) + 0.08 * np.sin(2 * np.pi * f * det * 3 * t))
        lfo = 1 + 0.06 * np.sin(2 * np.pi * 0.11 * (t + start))
        e = env(seg_n, 2.4, 0, 1, 2.4)
        out[n0:n0 + seg_n] += seg * e * lfo / (len(names) * 3)
    # leichte Höhenrücknahme, damit es weich bleibt
    out = lowpass(out, 1400) if len(out) < 2 else out
    return out * np.sin(np.pi * np.clip(t_all / 2.5, 0, 1) / 2) ** 2  # sanfter Einstieg


# Akkorde (D-Moll-Welt, ruhig): Startzeit und Töne
CHORDS = [
    (0.0, ["D3", "A3", "F4", "A4"]),      # Intro
    (6.0, ["Bb2", "F3", "D4", "F4"]),     # Der Name
    (13.0, ["F3", "C4", "A4", "C5"]),     # Erkennen (heller)
    (23.0, ["C3", "G3", "E4", "G4"]),     # Prüfen
    (31.0, ["D3", "A3", "F4", "C5"]),     # KI
    (37.4, ["Bb2", "F3", "D4", "A4"]),    # Rückübersetzung (warm)
    (43.0, ["F3", "C4", "A4", "E5"]),     # Kennzahlen
    (51.0, ["C3", "G3", "E4", "B4"]),     # Bildschirme
    (60.0, ["D3", "A3", "F4", "A4"]),     # Grenzen (ruhig)
    (66.0, ["Bb2", "F3", "D4", "F4", "A4"]),  # Abspann
]
bed = pad(CHORDS, DUR)
bed /= np.max(np.abs(bed)) + 1e-9
fade_out = np.ones(N)
fade_out[-int(3.0 * SR):] = np.linspace(1, 0, int(3.0 * SR))
mix[:, 0] += bed * 0.16 * fade_out
mix[:, 1] += bed * 0.16 * fade_out

# leiser Sub-Bass auf dem Grundton je Akkord
for i, (start, names) in enumerate(CHORDS):
    stop = CHORDS[i + 1][0] if i + 1 < len(CHORDS) else DUR
    n = int((stop - start) * SR)
    t = np.arange(n) / SR
    f = note(names[0]) / 2
    sub = np.sin(2 * np.pi * f * t) * env(n, 1.5, 0, 1, 1.5)
    add(sub, start, 0.07)

# ---------------------------------------------------------------- Klänge auf die Schlüsselmomente
# Cover
add(whoosh(1.5, 200, 1800, 0.55), 0.15, 0.35)                    # Schild zeichnet sich
for i, f in enumerate([note("D5"), note("F5"), note("A5"), note("D6"), note("A5"), note("F5"), note("D5")]):
    add(pluck(f, 0.7, 0.6), 0.95 + i * 0.05, 0.11, -0.3 + i * 0.1)  # Wortmarke-Buchstaben
add(chord_hit([note("D4"), note("A4"), note("F5")]), 1.45, 0.16)  # Haken sitzt
add(swell(1.2), 5.5, 0.5)                                         # Übergang
# Der Name
for i in range(2):
    add(tick(1800, 0.05), 8.0 + i * 0.2, 0.3, 0.45)              # Markierung
add(whoosh(1.1, 600, 2600, 0.5), 8.6, 0.22, -0.2)                # roter Faden
for i, f in enumerate([note("D4"), note("F4"), note("A4")]):
    add(pop(f), 9.6 + i * 0.14, 0.4, -0.5 + i * 0.3)             # Gesetze
add(swell(1.2), 12.5, 0.45)
# Erkennen
for i in range(6):
    add(tick(2000 + i * 120, 0.05), 14.0 + i * 0.5, 0.26, -0.5 + i * 0.2)   # Markierungen
for i, f in enumerate([note("A4"), note("C5"), note("D5"), note("F5"), note("A5")]):
    add(pluck(f, 0.6, 0.8), 18.0 + i * 0.28, 0.14, -0.5 + i * 0.25)         # Morph zu Platzhaltern
for i in range(4):
    add(tick(3000, 0.04), 14.2 + i * 0.5 + 0.9, 0.12, 0.6)                   # Zähler
add(swell(1.2), 22.5, 0.45)
# Prüfen
add(pop(380), 25.6, 0.45, 0.5)                                    # Schalter
add(pop(640), 27.4, 0.35, 0.5)                                    # benennen
for i in range(3):
    add(whoosh(0.35, 900, 3000, 0.4), 28.2 + i * 0.15, 0.2, -0.4 + i * 0.4)  # Klappen
add(swell(1.2), 30.5, 0.45)
# KI
add(whoosh(1.8, 250, 2400, 0.55), 31.7, 0.4, -0.6)               # Dokument fliegt
add(pop(560), 33.3, 0.35, 0.5)                                    # Nachricht
for i in range(5):
    add(tick(1500, 0.04), 33.9 + i * 0.3, 0.1, -0.3)             # Tippen
add(pop(480), 35.4, 0.35, -0.3)                                   # Antwort
add(swell(1.0), 37.2, 0.35)
for i, f in enumerate([note("F4"), note("A4"), note("D5")]):
    add(pluck(f, 1.4, 0.7), 38.6 + i * 0.5, 0.2, -0.3 + i * 0.3)  # Rückübersetzung
add(chord_hit([note("D4"), note("F4"), note("A4"), note("D5")], 3.0), 40.1, 0.2)
add(swell(1.3), 42.5, 0.5)
# Kennzahlen
for i in range(4):
    add(tick(2600 + i * 200, 0.05), 43.9 + i * 0.2, 0.22, -0.6 + i * 0.4)
for i in range(8):
    add(pluck(note(["D5", "F5", "A5", "D6", "C5", "F5", "A5", "C6"][i]), 0.5, 0.5), 46.0 + i * 0.08, 0.09, -0.6 + i * 0.17)
add(swell(1.3), 50.5, 0.5)
# Bildschirme
for i in range(3):
    add(whoosh(0.9, 200, 1600, 0.45), 51.2 + i * 0.14, 0.3, -0.5 + i * 0.5)
add(whoosh(0.9, 300, 1200, 0.5), 53.4, 0.25)
add(swell(1.2), 59.5, 0.45)
# Grenzen: nur das Bett, ein leiser Ton je Satz
add(pluck(note("D4"), 2.0, 0.3), 60.6, 0.12)
add(pluck(note("F4"), 2.0, 0.3), 63.3, 0.12)
add(swell(1.4), 65.4, 0.5)
# Abspann
add(chord_hit([note("Bb3"), note("D4"), note("F4"), note("A4"), note("D5")], 4.0), 66.6, 0.26)
add(pop(600), 68.2, 0.35)
add(pluck(note("D6"), 1.6, 0.5), 68.25, 0.1, 0.2)

# ---------------------------------------------------------------- Ausgabe
mix *= fade_out[:, None]
peak = np.max(np.abs(mix))
mix = mix / peak * 0.85  # Headroom
OUT.parent.mkdir(parents=True, exist_ok=True)
pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
import wave

with wave.open(str(OUT), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
rms = 20 * math.log10(np.sqrt(np.mean(mix ** 2)) + 1e-9)
print(f"{OUT.name}: {DUR:.0f} s, Spitze {20 * math.log10(0.85):.1f} dBFS, RMS {rms:.1f} dBFS, {OUT.stat().st_size / 2**20:.1f} MB")
