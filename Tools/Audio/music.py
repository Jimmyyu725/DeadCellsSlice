"""Procedural music and ambience loops.

Each track is composed from a chord progression, a few instruments built in
dsp.py (plucked strings, music box, bells, formant choir, saw pads, synthetic
drums) and a seeded melody generator, rendered on a dry and a reverb bus and
folded so the reverb tail wraps onto the start: every file loops seamlessly.
"""

import numpy as np

import dsp

MSR = 32000  # music / ambience sample rate (keeps the repo small)


def S(d):
    return dsp.secs(d, MSR)


# ---------------------------------------------------------------- instruments

def pad(freqs, dur, bright=1200.0, attack=0.8, release=1.2, detune=0.006, harm=14, vib=0.0):
    n = S(dur + release)
    out = np.zeros(n)
    for f in freqs:
        for d in (-detune, 0.0, detune):
            ff = f * (1 + d)
            if vib:
                ff = ff * (1 + vib * dsp.sine(5.2, n, MSR))
            out += dsp.additive_saw(ff, n, MSR, max_h=harm)
    out = dsp.lowpass(out, bright, order=2, sr=MSR)
    return out * dsp.adsr(n, attack, 0.3, 0.8, release, MSR) / (len(freqs) * 2.2)


def strings(freqs, dur, bright=2200.0, attack=0.25, release=0.6):
    return pad(freqs, dur, bright=bright, attack=attack, release=release, detune=0.004, harm=24, vib=0.004)


VOWELS = {"a": [(800, 6, 1.0), (1150, 7, 0.5), (2900, 10, 0.25)],
          "o": [(450, 6, 1.0), (800, 7, 0.45), (2830, 10, 0.15)],
          "u": [(325, 6, 1.0), (700, 7, 0.3), (2530, 10, 0.1)]}


def choir(freqs, dur, vowel="a", attack=0.6, release=1.0):
    n = S(dur + release)
    out = np.zeros(n)
    rng = np.random.default_rng(int(sum(freqs)))
    for f in freqs:
        for k in range(3):
            vib = 1 + 0.006 * dsp.sine(4.5 + rng.uniform(-0.6, 0.6), n, MSR, phase0=rng.uniform(0, 6))
            out += dsp.additive_saw(f * vib * (1 + rng.uniform(-0.004, 0.004)), n, MSR, max_h=40)
    out = dsp.peaks(out, VOWELS[vowel], sr=MSR)
    return out * dsp.adsr(n, attack, 0.3, 0.85, release, MSR) / (len(freqs) * 6)


def pluck(f, dur, rng, bright=0.6, decay=0.996):
    x = dsp.karplus(f, dur, rng, decay=decay, bright=bright, sr=MSR)
    return dsp.highpass(x, 40, sr=MSR) * 0.7


def musicbox(f, dur=1.2):
    n = S(dur)
    t = dsp.tvec(n, MSR)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.5) + 0.35 * np.sin(2 * np.pi * f * 3.98 * t) * np.exp(-t / 0.12)
    x += 0.15 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t / 0.04)
    return x * 0.6


def bellv(f, dur, rng, bright=0.7, decay=0.8):
    return dsp.bell(f, dur, rng, bright=bright, decay=decay, sr=MSR) * 0.5


def bass(f, dur, bright=500.0, saw=0.5):
    n = S(dur + 0.08)
    x = dsp.sine(f, n, MSR) + saw * dsp.lowpass(dsp.additive_saw(f, n, MSR, max_h=20), bright, sr=MSR)
    return x * dsp.adsr(n, 0.005, 0.15, 0.6, 0.08, MSR) * 0.6


def lead(f, dur, rng, bright=2400.0):
    n = S(dur + 0.15)
    x = dsp.additive_saw(f * (1 + 0.004 * dsp.sine(5.5, n, MSR)), n, MSR, max_h=30)
    x = dsp.tv_filter(x, lambda t: bright * (0.4 + 0.6 * np.exp(-t / 0.25)), kind="lp", sr=MSR)
    return dsp.distort(x * dsp.adsr(n, 0.01, 0.2, 0.7, 0.15, MSR), 1.5) * 0.35


def brass(freqs, dur):
    n = S(dur + 0.2)
    out = sum(dsp.additive_saw(f, n, MSR, max_h=25) for f in freqs)
    out = dsp.tv_filter(out, lambda t: 500 + 2200 * np.exp(-t / 0.18), kind="lp", sr=MSR)
    return dsp.distort(out * dsp.adsr(n, 0.02, 0.2, 0.55, 0.2, MSR) / len(freqs), 1.4) * 0.5


# drums

def kick(rng, punch=1.0):
    n = S(0.35)
    x = dsp.sine(dsp.sweep(140 * punch, 42, n), n, MSR) * dsp.exp_env(n, 0.09, MSR)
    c = dsp.lowpass(dsp.noise(S(0.006), rng), 5000, sr=MSR) * 0.4
    x[:len(c)] += c
    return x


def snare(rng, tone=190.0):
    n = S(0.25)
    body = dsp.sine(dsp.sweep(tone * 1.3, tone, n), n, MSR) * dsp.exp_env(n, 0.04, MSR) * 0.6
    sn = dsp.bandpass(dsp.noise(n, rng), 3200, 0.7, sr=MSR) * dsp.exp_env(n, 0.07, MSR)
    return body + sn


def hat(rng, open_=False):
    n = S(0.3 if open_ else 0.06)
    return dsp.highpass(dsp.noise(n, rng), 7000, sr=MSR) * dsp.exp_env(n, 0.09 if open_ else 0.012, MSR) * 0.5


def shaker(rng):
    n = S(0.08)
    return dsp.bandpass(dsp.noise(n, rng), 6000, 1.2, sr=MSR) * dsp.adsr(n, 0.02, 0.02, 0.4, 0.03, MSR) * 0.4


def tom(rng, f=110.0, decay=0.15):
    n = S(0.5)
    x = dsp.sine(dsp.sweep(f * 1.5, f, n), n, MSR) * dsp.exp_env(n, decay, MSR)
    x[:S(0.01)] += dsp.lowpass(dsp.noise(S(0.01), rng), 2500, sr=MSR) * 0.3
    return x


def taiko(rng):
    n = S(1.0)
    x = dsp.sine(dsp.sweep(95, 55, n), n, MSR) * dsp.exp_env(n, 0.3, MSR)
    x += dsp.lowpass(dsp.noise(n, rng, "brown"), 300, sr=MSR) * dsp.exp_env(n, 0.12, MSR) * 0.5
    return x


def tick(rng, f=3200.0):
    return dsp.modal([f, f * 2.13, f * 3.7], [1.0, 0.4, 0.2], [0.015, 0.008, 0.005], 0.05, MSR, rng=rng) * 0.5


def gong(rng, f=65.0):
    return dsp.bell(f, 4.0, rng, bright=0.8, decay=1.5, sr=MSR) * 0.6


# ---------------------------------------------------------------- song bus

class Song:
    def __init__(self, bpm, bars, seed, beats=4):
        self.spb = 60.0 / bpm
        self.beats = beats
        self.bars = bars
        self.length = bars * beats * self.spb
        self.rng = np.random.default_rng(seed)
        n = S(self.length + 8.0)
        self.dry = np.zeros((n, 2))
        self.wet = np.zeros((n, 2))

    def at(self, bar, beat=0.0):
        return (bar * self.beats + beat) * self.spb

    def add(self, x, t, pan=0.0, gain=1.0, send=0.3):
        st = dsp.to_stereo(x * gain, pan)
        i = S(t)
        end = min(len(self.dry), i + len(st))
        self.dry[i:end] += st[:end - i]
        self.wet[i:end] += st[:end - i] * send

    def render(self, verb=2.4, decay=2.2, target_db=-17.0):
        ir = dsp.reverb_ir(verb, self.rng, sr=MSR, decay=decay, stereo=True, predelay=0.02)
        mix = self.dry + dsp.convolve(self.wet, ir)[:len(self.dry)] * 1.6
        L = S(self.length)
        out = mix[:L].copy()
        tail = mix[L:]
        k = min(len(tail), L)
        out[:k] += tail[:k]  # wrap the tail: seamless loop
        return dsp.rms_normalize(out, target_db)


def motif(rng, beats=8, density=0.55, span=(0, 7)):
    """[(beat, length, degree)] — a short phrase on a random walk."""
    rhythms = [[1, 1], [0.5, 0.5, 1], [1.5, 0.5], [0.5, 0.5, 0.5, 0.5], [2], [1, 0.5, 0.5]]
    notes, t, d = [], 0.0, int(rng.integers(span[0] + 2, span[1] - 1))
    while t < beats - 0.01:
        for length in rhythms[int(rng.integers(len(rhythms)))]:
            if t >= beats - 0.01:
                break
            if rng.random() < density or not notes:
                d = int(np.clip(d + rng.choice([-2, -1, -1, 1, 1, 2, 0, 3, -3]), span[0], span[1]))
                notes.append((t, min(length, beats - t), d))
            t += length
    return notes


def snap(d, chord_degs, scale_len):
    """Move degree d onto the nearest chord tone (strong beats)."""
    best = min(chord_degs, key=lambda c: min(abs((d - c) % scale_len), abs((c - d) % scale_len)))
    base = d - ((d - best) % scale_len)
    cand = [base, base + scale_len]
    return min(cand, key=lambda c: abs(c - d))


# ---------------------------------------------------------------- tracks

def track_menu():
    s = Song(72, 24, seed=11)
    root, sc = dsp.note("D", 3), "minor"
    prog = [0, 5, 2, 6, 0, 3, 5, 4]
    rng = s.rng
    mot = motif(rng, beats=8, density=0.5, span=(4, 11))
    for i in range(s.bars // 2):
        deg = prog[i % len(prog)]
        ch = dsp.chord(root, sc if deg != 4 else "harmonic", deg)
        t = s.at(2 * i)
        s.add(strings([dsp.midi_to_hz(m) for m in ch], 2 * s.beats * s.spb, bright=1500, attack=1.2, release=1.4), t, gain=0.5, send=0.5)
        s.add(bass(dsp.midi_to_hz(ch[0] - 12), 2 * s.beats * s.spb * 0.9, bright=300, saw=0.2), t, gain=0.45, send=0.1)
        if i >= 2:
            arp = ch + [ch[0] + 12, ch[1] + 12, ch[2] + 12]
            order = [0, 1, 2, 3, 4, 3, 2, 1] * 2
            for k, idx in enumerate(order):
                s.add(pluck(dsp.midi_to_hz(arp[idx] + 12), 1.4, rng, bright=0.45), t + k * s.spb / 2,
                      pan=-0.35 + 0.7 * (idx / 5), gain=0.32, send=0.45)
        if i >= 4 and i % 4 in (0, 1, 2):
            for b, ln, d in mot:
                dd = snap(d, [deg, deg + 2, deg + 4], 7) if b % 2 == 0 else d
                s.add(musicbox(dsp.midi_to_hz(dsp.degree(root + 24, sc, dd)), 1.6), t + b * s.spb, pan=0.2, gain=0.38, send=0.6)
        if i % 2 == 0:
            s.add(bellv(dsp.midi_to_hz(root + 12), 4.0, rng, bright=0.6), t, pan=-0.2, gain=0.35, send=0.7)
    return s.render(verb=3.0, decay=2.8)


def track_oubliette():
    s = Song(92, 32, seed=21)
    root, sc = dsp.note("A", 2), "phrygian"
    prog = [0, 0, 5, 1, 0, 0, 3, 4]
    rng = s.rng
    mot = motif(rng, beats=8, density=0.6, span=(5, 12))
    ost = [0, 0, 4, 1, 0, 7, 4, 3]
    for bar in range(s.bars):
        deg = prog[(bar // 2) % len(prog)]
        t = s.at(bar)
        ch = dsp.chord(root, sc, deg)
        if bar % 4 == 0:
            s.add(pad([dsp.midi_to_hz(ch[0]), dsp.midi_to_hz(ch[0] + 7)], 4 * s.beats * s.spb, bright=600, attack=1.5, release=2.0),
                  t, gain=0.55, send=0.5)
        for k, o in enumerate(ost):
            s.add(pluck(dsp.midi_to_hz(dsp.degree(root, sc, deg + o)), 0.5, rng, bright=0.7, decay=0.99), t + k * s.spb / 2,
                  pan=-0.15, gain=0.45, send=0.2)
        if bar >= 4:
            s.add(kick(rng, 0.8), t, gain=0.6, send=0.1)
            s.add(tom(rng, 90), t + 2.5 * s.spb, pan=0.2, gain=0.45, send=0.3)
            s.add(tom(rng, 120, 0.1), t + 3.5 * s.spb, pan=-0.2, gain=0.3, send=0.3)
            for k in range(8):
                s.add(shaker(rng), t + k * s.spb / 2, pan=0.4, gain=0.5 if k % 2 else 0.8, send=0.1)
        if 8 <= bar < 28 and bar % 2 == 0:
            for b, ln, d in mot:
                dd = snap(d, [deg, deg + 2, deg + 4], 7) if b % 2 == 0 else d
                f = dsp.midi_to_hz(dsp.degree(root + 24, sc, dd))
                s.add(strings([f], ln * s.spb, bright=2600, attack=0.08, release=0.4), t + b * s.spb, pan=0.25, gain=0.42, send=0.45)
        if bar % 8 == 7:
            s.add(dsp.modal([523, 1201, 1980], [1, 0.5, 0.3], [0.6, 0.4, 0.25], 1.0, MSR, rng=rng) * 0.3,
                  t + 3 * s.spb, pan=0.5, gain=0.6, send=0.8)
    return s.render(verb=2.6, decay=2.4)


def track_promenade():
    s = Song(100, 32, seed=31)
    root, sc = dsp.note("E", 3), "dorian"
    prog = [0, 3, 5, 4, 0, 3, 6, 4]
    rng = s.rng
    mot = motif(rng, beats=8, density=0.4, span=(5, 11))
    for bar in range(s.bars):
        deg = prog[(bar // 2) % len(prog)]
        t = s.at(bar)
        ch = dsp.chord(root, sc, deg, 4)
        if bar % 2 == 0:
            s.add(pad([dsp.midi_to_hz(m + 12) for m in ch[:3]], 2 * s.beats * s.spb, bright=2600, attack=0.9, release=1.5),
                  t, gain=0.4, send=0.6)
            s.add(bass(dsp.midi_to_hz(ch[0] - 12), 2 * s.beats * s.spb * 0.95, bright=250, saw=0.15), t, gain=0.4, send=0.1)
        arp = [ch[0] + 24, ch[1] + 24, ch[2] + 24, ch[3] + 24, ch[2] + 24, ch[1] + 24]
        for k in range(16):
            s.add(musicbox(dsp.midi_to_hz(arp[k % len(arp)]), 0.8), t + k * s.spb / 4, pan=-0.5 + (k % 6) / 6,
                  gain=0.16 + 0.06 * (k % 4 == 0), send=0.55)
        if bar >= 8:
            s.add(kick(rng, 0.7), t, gain=0.4, send=0.05)
            s.add(kick(rng, 0.7), t + 2.5 * s.spb, gain=0.3, send=0.05)
            for k in range(4):
                s.add(hat(rng), t + (k + 0.5) * s.spb, pan=0.3, gain=0.4, send=0.15)
            s.add(snare(rng, 220) * 0.5, t + 3 * s.spb, pan=-0.1, gain=0.35, send=0.4)
        if 12 <= bar < 30 and bar % 4 in (0, 2):
            for b, ln, d in mot:
                dd = snap(d, [deg, deg + 2, deg + 4], 7)
                s.add(choir([dsp.midi_to_hz(dsp.degree(root + 12, sc, dd))], ln * s.spb * 1.2, "u", attack=0.2, release=0.6),
                      t + b * s.spb, pan=0.1, gain=0.55, send=0.6)
    return s.render(verb=3.2, decay=3.0)


def track_ossuary():
    s = Song(78, 24, seed=41)
    root, sc = dsp.note("C", 3), "harmonic"
    prog = [0, 5, 3, 4, 0, 1, 5, 4]
    rng = s.rng
    mot = motif(rng, beats=8, density=0.45, span=(3, 9))
    for bar in range(s.bars):
        deg = prog[(bar // 2) % len(prog)]
        t = s.at(bar)
        ch = dsp.chord(root, sc, deg)
        if bar % 2 == 0:
            s.add(choir([dsp.midi_to_hz(m) for m in ch], 2 * s.beats * s.spb, "a", attack=1.0, release=1.5), t, gain=0.6, send=0.6)
        for k in range(4):
            s.add(strings([dsp.midi_to_hz(ch[0] - 12 + (7 if k == 2 else 0))], s.spb * 0.8, bright=900, attack=0.03, release=0.2),
                  t + k * s.spb, pan=-0.2, gain=0.4, send=0.25)
        if bar >= 4:
            s.add(taiko(rng), t, pan=-0.1, gain=0.7, send=0.4)
            s.add(taiko(rng) * 0.6, t + 2 * s.spb, pan=0.1, gain=0.6, send=0.4)
            if bar % 4 == 3:
                for k in range(4):
                    s.add(tom(rng, 140 - 15 * k), t + (2 + k * 0.5) * s.spb, pan=-0.3 + 0.2 * k, gain=0.4, send=0.3)
        if bar % 4 == 0:
            s.add(bellv(dsp.midi_to_hz(root), 5.0, rng, bright=0.65, decay=1.2), t, pan=0.3, gain=0.45, send=0.8)
        if 8 <= bar < 22 and bar % 2 == 0:
            for b, ln, d in mot:
                dd = snap(d, [deg, deg + 2, deg + 4], 7) if b % 2 == 0 else d
                s.add(strings([dsp.midi_to_hz(dsp.degree(root + 12, sc, dd))], ln * s.spb, bright=1800, attack=0.15, release=0.5),
                      t + b * s.spb, pan=0.2, gain=0.4, send=0.5)
    return s.render(verb=3.5, decay=3.2)


def track_stilt():
    s = Song(104, 32, seed=51)
    root, sc = dsp.note("D", 3), "pentatonic"
    rng = s.rng
    mot = motif(rng, beats=8, density=0.55, span=(5, 12))
    mot2 = motif(rng, beats=8, density=0.55, span=(5, 12))
    prog = [0, 0, 2, 3, 0, 0, 4, 3]
    for bar in range(s.bars):
        deg = prog[(bar // 2) % len(prog)]
        t = s.at(bar)
        ch = [dsp.degree(root, sc, deg + k) for k in (0, 2, 4)]
        if bar % 4 == 0:
            s.add(gong(rng, dsp.midi_to_hz(root - 12)), t, gain=0.5, send=0.6)
            s.add(pad([dsp.midi_to_hz(m) for m in ch], 4 * s.beats * s.spb, bright=900, attack=1.5, release=2.0), t, gain=0.35, send=0.6)
        patt = [0, 2, 1, 3, 2, 4, 3, 1]
        for k, o in enumerate(patt):
            s.add(pluck(dsp.midi_to_hz(dsp.degree(root + 12, sc, deg + o)), 0.6, rng, bright=0.85, decay=0.994),
                  t + k * s.spb / 2, pan=-0.3, gain=0.35, send=0.35)
        if bar >= 4:
            for k, (f, g) in enumerate(((110, 0.5), (0, 0), (150, 0.35), (110, 0.4), (0, 0), (150, 0.3), (180, 0.3), (0, 0))):
                if f:
                    s.add(tom(rng, f, 0.08), t + k * s.spb / 2, pan=0.2, gain=g, send=0.2)
        if 8 <= bar < 30:
            m = mot if (bar // 4) % 2 == 0 else mot2
            if bar % 2 == 0:
                for b, ln, d in m:
                    s.add(bellv(dsp.midi_to_hz(dsp.degree(root + 24, sc, d)), 1.8, rng, bright=0.55, decay=0.5),
                          t + b * s.spb, pan=0.25, gain=0.5, send=0.5)
    return s.render(verb=2.8, decay=2.6)


def track_lung():
    s = Song(116, 32, seed=61)
    root, sc = dsp.note("G", 2), "harmonic"
    prog = [0, 0, 5, 5, 3, 3, 4, 4]
    rng = s.rng
    mot = motif(rng, beats=8, density=0.6, span=(7, 14))
    for bar in range(s.bars):
        deg = prog[bar % len(prog)]
        t = s.at(bar)
        ch = dsp.chord(root, sc, deg)
        for k in range(8):
            s.add(tick(rng, 3400 if k % 2 == 0 else 2600), t + k * s.spb / 2, pan=0.45 if k % 2 else -0.45, gain=0.45, send=0.2)
        for k in range(8):
            s.add(bass(dsp.midi_to_hz(ch[0] + (12 if k % 4 == 3 else 0)), s.spb / 2 * 0.8, bright=700, saw=0.6),
                  t + k * s.spb / 2, gain=0.42, send=0.05)
        if bar % 2 == 0:
            s.add(strings([dsp.midi_to_hz(m + 12) for m in ch], 2 * s.beats * s.spb, bright=1800, attack=0.4, release=0.8),
                  t, gain=0.35, send=0.4)
        arp = [ch[0] + 24, ch[1] + 24, ch[2] + 24, ch[1] + 24]
        if bar >= 4:
            for k in range(16):
                s.add(pluck(dsp.midi_to_hz(arp[k % 4]), 0.35, rng, bright=0.8, decay=0.99), t + k * s.spb / 4,
                      pan=-0.2 + 0.4 * ((k % 4) / 3), gain=0.22, send=0.25)
            for k in range(4):
                s.add(kick(rng, 0.9), t + k * s.spb, gain=0.5, send=0.05)
            s.add(snare(rng), t + s.spb, gain=0.3, send=0.3)
            s.add(snare(rng), t + 3 * s.spb, gain=0.3, send=0.3)
        if 8 <= bar < 30 and bar % 2 == 0:
            for b, ln, d in mot:
                dd = snap(d, [deg, deg + 2, deg + 4], 7) if b % 1 == 0 else d
                s.add(musicbox(dsp.midi_to_hz(dsp.degree(root + 24, sc, dd)), 1.0), t + b * s.spb, pan=0.3, gain=0.3, send=0.5)
    return s.render(verb=2.2, decay=2.0)


def track_passage():
    s = Song(64, 16, seed=71)
    root, sc = dsp.note("F", 3), "lydian"
    prog = [0, 1, 5, 4]
    rng = s.rng
    for bar in range(s.bars):
        deg = prog[(bar // 2) % len(prog)]
        t = s.at(bar)
        ch = dsp.chord(root, sc, deg, 4)
        if bar % 2 == 0:
            s.add(pad([dsp.midi_to_hz(m) for m in ch], 2 * s.beats * s.spb, bright=1400, attack=1.4, release=2.0), t, gain=0.45, send=0.6)
        arp = ch + [ch[0] + 12]
        for k, idx in enumerate([0, 2, 4, 3, 1, 3, 2, 4]):
            s.add(pluck(dsp.midi_to_hz(arp[idx] + 12), 2.0, rng, bright=0.4, decay=0.998), t + k * s.spb / 2,
                  pan=-0.4 + 0.2 * idx, gain=0.3, send=0.6)
        if bar % 4 == 2:
            s.add(bellv(dsp.midi_to_hz(ch[2] + 24), 3.0, rng, bright=0.5, decay=0.8), t + s.spb, pan=0.4, gain=0.3, send=0.8)
    return s.render(verb=3.5, decay=3.4)


def track_boss():
    s = Song(140, 32, seed=81)
    root, sc = dsp.note("D", 2), "harmonic"
    prog = [0, 0, 5, 5, 3, 3, 4, 4]
    rng = s.rng
    mot = motif(rng, beats=8, density=0.7, span=(7, 14))
    ost = [0, 0, 7, 0, 5, 0, 7, 8]
    for bar in range(s.bars):
        deg = prog[bar % len(prog)]
        t = s.at(bar)
        ch = dsp.chord(root, sc, deg)
        for k, o in enumerate(ost):
            s.add(bass(dsp.midi_to_hz(ch[0] + (o if o < 8 else 12)), s.spb / 2 * 0.85, bright=900, saw=0.9),
                  t + k * s.spb / 2, gain=0.5, send=0.05)
        for k in range(16):
            s.add(pluck(dsp.midi_to_hz(ch[k % 3] + 24), 0.25, rng, bright=0.9, decay=0.985), t + k * s.spb / 4,
                  pan=0.35 if k % 2 else -0.35, gain=0.2, send=0.15)
        if bar % 2 == 0:
            s.add(brass([dsp.midi_to_hz(m + 12) for m in ch], s.spb * 1.5), t, gain=0.55, send=0.3)
            s.add(choir([dsp.midi_to_hz(m + 12) for m in ch], 2 * s.beats * s.spb, "a", attack=0.4, release=0.8), t, gain=0.35, send=0.5)
        if bar >= 2:
            for k in range(4):
                s.add(kick(rng, 1.1), t + k * s.spb, gain=0.65, send=0.05)
            s.add(kick(rng, 1.1), t + 2.5 * s.spb, gain=0.4, send=0.05)
            for k in (1, 3):
                s.add(snare(rng), t + k * s.spb, gain=0.5, send=0.3)
            for k in range(8):
                s.add(hat(rng, open_=(k == 7)), t + k * s.spb / 2, pan=0.25, gain=0.45, send=0.1)
        if bar % 8 == 7:
            for k in range(8):
                s.add(tom(rng, 180 - 12 * k, 0.12), t + (2 + k * 0.25) * s.spb, pan=-0.4 + 0.1 * k, gain=0.5, send=0.25)
        if bar % 4 == 0:
            s.add(taiko(rng), t, gain=0.7, send=0.3)
        if 8 <= bar < 32 and bar % 2 == 0:
            for b, ln, d in mot:
                dd = snap(d, [deg, deg + 2, deg + 4], 7) if b % 1 == 0 else d
                s.add(lead(dsp.midi_to_hz(dsp.degree(root + 24, sc, dd)), ln * s.spb, rng), t + b * s.spb, pan=0.1, gain=0.42, send=0.3)
    return s.render(verb=2.0, decay=1.8, target_db=-15.5)


def track_death():
    """Short one-shot sting (not looped)."""
    rng = np.random.default_rng(91)
    n = S(5.0)
    out = np.zeros((n, 2))
    for k, m in enumerate((dsp.note("D", 4), dsp.note("A", 3), dsp.note("F", 3), dsp.note("D", 3))):
        x = bellv(dsp.midi_to_hz(m), 3.5, rng, bright=0.6, decay=1.0)
        out = dsp.mix_at(out, dsp.to_stereo(x, -0.3 + 0.2 * k), S(0.45 * k))
    p = pad([dsp.midi_to_hz(m) for m in (dsp.note("D", 2), dsp.note("A", 2), dsp.note("F", 3))], 3.0, bright=700, attack=1.0, release=1.5)
    out = dsp.mix_at(out, dsp.to_stereo(p * 0.8), 0)
    wet = dsp.convolve(out, dsp.reverb_ir(3.0, rng, sr=MSR, decay=2.8))
    out = out + wet[:len(out)] * 0.5
    return dsp.fade(dsp.normalize(out, 0.7), 0.01, 0.8, MSR)


# ---------------------------------------------------------------- ambience

def loop_fold(x, cross):
    """Crossfade the last `cross` samples into the start so x loops."""
    c = S(cross)
    body, tail = x[:-c].copy(), x[-c:]
    w = np.linspace(0, 1, c)
    if body.ndim == 2:
        w = w[:, None]
    body[:c] = body[:c] * w + tail * (1 - w)
    return body


def drip(rng):
    n = S(0.25)
    f = dsp.sweep(rng.uniform(900, 1400), rng.uniform(2200, 3200), n)
    return dsp.sine(f, n, MSR) * dsp.exp_env(n, 0.025, MSR) * 0.5


def amb(seed, dur, layers):
    rng = np.random.default_rng(seed)
    n = S(dur + 2.0)
    out = np.zeros((n, 2))
    for fn in layers:
        out += fn(rng, n)
    wet = dsp.convolve(out, dsp.reverb_ir(2.5, rng, sr=MSR, decay=2.4))[:n]
    out = out + wet * 0.4
    return dsp.rms_normalize(loop_fold(out, 2.0), -24.0)


def lfo(n, rate, rng):
    return 0.5 + 0.5 * dsp.sine(rate, n, MSR, phase0=rng.uniform(0, 6))


def drone(rng, n, freqs=(55.0, 55.4), level=0.25):
    x = sum(dsp.sine(f, n, MSR) for f in freqs) / len(freqs)
    return dsp.to_stereo(x * level * (0.7 + 0.3 * lfo(n, 0.07, rng)))


def wind(rng, n, center=500.0, level=0.6):
    x = dsp.noise(n, rng, "pink")
    x = dsp.tv_filter(x, lambda t: center * (0.6 + 0.8 * (0.5 + 0.5 * np.sin(t * 0.37) * np.sin(t * 0.11 + 1))), kind="bp", q=1.2, sr=MSR)
    l, r = x * (0.6 + 0.4 * lfo(n, 0.05, rng)), np.roll(x, S(0.013)) * (0.6 + 0.4 * lfo(n, 0.06, rng))
    return np.stack([l, r], axis=1) * level


def events(rng, n, maker, every, pan_spread=0.8, gain=1.0):
    out = np.zeros((n, 2))
    t = rng.uniform(0, every)
    while S(t) < n - S(1.0):
        out = dsp.mix_at(out, dsp.to_stereo(maker(rng) * gain, rng.uniform(-pan_spread, pan_spread)), S(t))[:n]
        t += rng.uniform(every * 0.5, every * 1.5)
    return out


def waves(rng, n):
    x = dsp.lowpass(dsp.noise(n, rng, "pink"), 900, sr=MSR)
    t = dsp.tvec(n, MSR)
    swell = (0.35 + 0.65 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 6.5))) ** 2
    return dsp.to_stereo(x * swell * 0.8)


def rain(rng, n):
    x = dsp.highpass(dsp.noise(n, rng), 2500, sr=MSR) * 0.25
    return np.stack([x, np.roll(x, 777)], axis=1)


def ticking(rng, n):
    out = np.zeros((n, 2))
    k, t = 0, 0.0
    while S(t) < n - S(0.1):
        out = dsp.mix_at(out, dsp.to_stereo(tick(rng, 2400 if k % 2 else 1800) * 0.6, 0.3 if k % 2 else -0.3), S(t))[:n]
        t += 0.5
        k += 1
    return out


def hiss(rng):
    n = S(1.2)
    return dsp.highpass(dsp.noise(n, rng), 3000, sr=MSR) * dsp.adsr(n, 0.05, 0.2, 0.5, 0.8, MSR) * 0.5


def creak_soft(rng):
    n = S(0.8)
    f = dsp.sweep(rng.uniform(150, 220), rng.uniform(250, 330), n)
    x = dsp.bandpass(dsp.additive_saw(f / 6, n, MSR, max_h=30), 260, 2.0, sr=MSR)
    return x * dsp.adsr(n, 0.1, 0.2, 0.6, 0.3, MSR) * 0.4


def far_bell(rng):
    return bellv(rng.choice([196.0, 220.0, 261.6]), 4.0, rng, bright=0.5, decay=1.2) * 0.35


def chain(rng):
    out = np.zeros(S(0.5))
    for k in range(4):
        out = dsp.mix_at(out, dsp.modal([rng.uniform(1800, 3200)], [1.0], [0.04], 0.1, MSR, rng=rng) * 0.3, S(rng.uniform(0, 0.35)))
    return out


def trickle(rng, n):
    return events(rng, n, drip, 0.18, 0.4, 0.35) + dsp.to_stereo(dsp.bandpass(dsp.noise(n, rng), 1800, 0.8, sr=MSR) * 0.12)


AMBIENCE = {
    "amb.dungeon": lambda: amb(101, 20, [lambda r, n: drone(r, n, (55.0, 55.3), 0.3), lambda r, n: wind(r, n, 260, 0.25),
                                         lambda r, n: events(r, n, drip, 1.8), lambda r, n: events(r, n, chain, 7.0, gain=0.6)]),
    "amb.wind": lambda: amb(102, 20, [lambda r, n: wind(r, n, 650, 0.6), lambda r, n: events(r, n, far_bell, 9.0, gain=0.5)]),
    "amb.ossuary": lambda: amb(103, 20, [lambda r, n: drone(r, n, (41.2, 41.5, 61.7), 0.35), lambda r, n: wind(r, n, 300, 0.2),
                                         lambda r, n: events(r, n, creak_soft, 4.5)]),
    "amb.sea": lambda: amb(104, 20, [waves, rain, lambda r, n: events(r, n, far_bell, 8.0, gain=0.7)]),
    "amb.clock": lambda: amb(105, 20, [ticking, lambda r, n: drone(r, n, (49.0, 98.2), 0.2), lambda r, n: events(r, n, hiss, 3.5, gain=0.6)]),
    "amb.passage": lambda: amb(106, 20, [trickle, lambda r, n: drone(r, n, (65.4, 65.7), 0.18)]),
}

TRACKS = {
    "music.menu": track_menu,
    "music.oubliette": track_oubliette,
    "music.promenade": track_promenade,
    "music.ossuary": track_ossuary,
    "music.stilt": track_stilt,
    "music.lung": track_lung,
    "music.passage": track_passage,
    "music.boss": track_boss,
    "music.death": track_death,
}
