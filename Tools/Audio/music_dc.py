"""Music in the spirit of Dead Cells' soundtrack: Celtic folk melodies (fiddle,
tin whistle) over rock rhythm sections (driving drums, palm-muted and
distorted guitars, picked bass), with piano and string sections for the
calmer areas.  Everything is synthesised here; nothing is sampled.

Each track is built bar by bar from a section plan (intro / A / B / break /
A'), rendered on a dry and a reverb bus, glued with gentle saturation and
folded so the reverb tail wraps onto the start: every file loops seamlessly.
"""

import numpy as np

import dsp
from music import MSR, Song, S

# ---------------------------------------------------------------- drums


def kick(rng, punch=1.0, tone=50.0, length=0.42):
    n = S(length)
    t = dsp.tvec(n, MSR)
    f = tone + (170.0 * punch - tone) * np.exp(-t / 0.028)
    body = dsp.sine(f, n, MSR) * np.exp(-t / 0.15)
    click = dsp.highpass(dsp.noise(S(0.005), rng), 1800, sr=MSR) * 0.5
    body[:len(click)] += click
    return np.tanh(1.9 * body) * 0.6


def snare(rng, tone=190.0, crack=1.0):
    n = S(0.32)
    t = dsp.tvec(n, MSR)
    body = (dsp.sine(tone * (1 + 0.4 * np.exp(-t / 0.01)), n, MSR) + 0.5 * dsp.sine(tone * 1.72, n, MSR)) * np.exp(-t / 0.05)
    wires = dsp.bandpass(dsp.noise(n, rng), 4200, 0.6, sr=MSR) * np.exp(-t / 0.11) * crack
    snap = dsp.highpass(dsp.noise(S(0.008), rng), 3000, sr=MSR)
    x = body * 0.55 + wires
    x[:len(snap)] += snap * 0.6
    return np.tanh(1.6 * x) * 0.8


def clap(rng):
    n = S(0.3)
    x = np.zeros(n)
    for k, d in enumerate((0.0, 0.011, 0.022)):
        b = dsp.bandpass(dsp.noise(S(0.02), rng), 1400, 1.2, sr=MSR) * np.exp(-dsp.tvec(S(0.02), MSR) / 0.005)
        x = dsp.mix_at(x, b, S(d))
    tail = dsp.bandpass(dsp.noise(n, rng), 1200, 0.8, sr=MSR) * np.exp(-dsp.tvec(n, MSR) / 0.07) * 0.6
    return (x + tail) * 0.8


METAL = [2.0, 3.0, 4.16, 5.43, 6.79, 8.21]


def hat(rng, open_=False, tone=310.0):
    n = S(0.4 if open_ else 0.07)
    t = dsp.tvec(n, MSR)
    x = sum(np.sign(np.sin(2 * np.pi * tone * r * t + rng.uniform(0, 6))) for r in METAL)
    x = dsp.highpass(x / 6 + 0.4 * dsp.noise(n, rng), 7500, sr=MSR)
    return x * np.exp(-t / (0.12 if open_ else 0.018)) * 0.45


def crash(rng, dur=2.2):
    n = S(dur)
    t = dsp.tvec(n, MSR)
    x = sum(np.sign(np.sin(2 * np.pi * 420 * r * t + rng.uniform(0, 6))) for r in METAL) / 6
    x = dsp.highpass(x * 0.5 + dsp.noise(n, rng), 3500, sr=MSR)
    return x * np.exp(-t / 0.7) * (1 - np.exp(-t / 0.004)) * 0.5


def tamb(rng):
    n = S(0.16)
    t = dsp.tvec(n, MSR)
    jingle = dsp.modal([5800, 7200, 8900], [1, 0.7, 0.5], [0.04, 0.03, 0.02], 0.16, MSR, rng=rng, detune=0.02)
    return (jingle * 0.4 + dsp.highpass(dsp.noise(n, rng), 6000, sr=MSR) * np.exp(-t / 0.03) * 0.4) * 0.6


def tom(rng, f=110.0, decay=0.2):
    n = S(0.6)
    t = dsp.tvec(n, MSR)
    x = dsp.sine(f * (1 + 0.5 * np.exp(-t / 0.03)), n, MSR) * np.exp(-t / decay)
    x[:S(0.01)] += dsp.lowpass(dsp.noise(S(0.01), rng), 2500, sr=MSR) * 0.4
    return np.tanh(1.5 * x) * 0.8


def bodhran(rng, low=True):
    n = S(0.35)
    t = dsp.tvec(n, MSR)
    f = 85.0 if low else 160.0
    x = dsp.sine(f * (1 + 0.3 * np.exp(-t / 0.02)), n, MSR) * np.exp(-t / (0.12 if low else 0.06))
    x += dsp.lowpass(dsp.noise(n, rng), 900, sr=MSR) * np.exp(-t / 0.02) * 0.5
    return x * 0.8


def taiko(rng):
    n = S(1.1)
    t = dsp.tvec(n, MSR)
    x = dsp.sine(60 * (1 + 0.6 * np.exp(-t / 0.05)), n, MSR) * np.exp(-t / 0.35)
    x += dsp.lowpass(dsp.noise(n, rng, "brown"), 350, sr=MSR) * np.exp(-t / 0.12) * 0.6
    return np.tanh(1.4 * x)


def timpani(rng, f):
    n = S(2.0)
    t = dsp.tvec(n, MSR)
    x = dsp.modal([f, f * 1.5, f * 1.98, f * 2.44], [1, 0.5, 0.3, 0.15], [0.9, 0.5, 0.3, 0.2], 2.0, MSR, rng=rng)
    x[:S(0.015)] += dsp.lowpass(dsp.noise(S(0.015), rng), 1200, sr=MSR) * 0.5
    return x * 0.8


# ---------------------------------------------------------------- strings / winds


def guitar_string(f, dur, rng, bright=0.75, decay=0.9985, pick=0.18):
    return dsp.karplus(f, dur, rng, decay=decay, bright=bright, sr=MSR, pick=pick)


def eguitar(freqs, dur, rng, mute=0.0, drive=7.0, bright=0.85):
    """Distorted electric: power chord through a little amp and cabinet."""
    n = S(dur + 0.08)
    x = np.zeros(n)
    for f in freqs:
        s = guitar_string(f * (1 + rng.uniform(-0.002, 0.002)), dur + 0.08, rng, bright=bright, decay=0.9992)
        x[:len(s)] += s[:n]
    t = dsp.tvec(n, MSR)
    if mute > 0:
        x *= np.exp(-t / (0.05 + 0.4 * (1 - mute)))
    x = dsp.highpass(x, 100, sr=MSR)
    x = np.tanh(drive * x / max(1, len(freqs)))
    x = dsp.peaks(dsp.lowpass(x, 4300, order=3, sr=MSR), [(110, 1.0, 0.6), (1800, 1.5, 0.5), (750, 1.2, 0.4)], sr=MSR)
    return x * dsp.adsr(n, 0.002, 0.05, 0.9, 0.05, MSR) * 1.05


def strum(freqs, dur, rng, down=True, spread=0.014, bright=0.65, accent=1.0):
    """Acoustic strum: strings sounded a few ms apart, a wooden body bump."""
    order = freqs if down else list(reversed(freqs))
    n = S(dur + 0.3)
    x = np.zeros(n)
    for k, f in enumerate(order):
        s = guitar_string(f, dur + 0.3, rng, bright=bright, decay=0.9975, pick=0.22) * (0.9 ** k)
        x = dsp.mix_at(x, s, S(k * spread + rng.uniform(0, 0.002)))
    x = dsp.peaks(x, [(105, 2.0, 0.8), (230, 2.5, 0.6), (2600, 1.2, 0.35)], sr=MSR) + 0.4 * x
    x[:S(0.008)] += dsp.highpass(dsp.noise(S(0.008), rng), 2500, sr=MSR) * 0.15
    return x * accent * 0.32


def pick_bass(f, dur, rng, bright=0.45):
    n = S(dur + 0.05)
    t = dsp.tvec(n, MSR)
    s = guitar_string(f, dur + 0.05, rng, bright=bright, decay=0.9993, pick=0.3)[:n]
    sub = dsp.sine(f, n, MSR) * np.exp(-t / max(0.2, dur))
    x = dsp.lowpass(s * 0.8 + sub * 0.6, 1400, sr=MSR)
    return np.tanh(1.5 * x) * dsp.adsr(n, 0.003, 0.05, 0.9, 0.05, MSR) * 0.6


def fiddle(f, dur, rng, vib=0.007, attack=0.05, bright=1.0):
    """Bowed: a saw with delayed vibrato through violin body formants plus rosin noise."""
    n = S(dur + 0.12)
    t = dsp.tvec(n, MSR)
    onset = np.clip((t - 0.15) / 0.3, 0, 1)
    ff = f * (1 + vib * onset * np.sin(2 * np.pi * 5.8 * t + rng.uniform(0, 6)))
    x = dsp.additive_saw(ff, n, MSR, max_h=28)
    x = dsp.peaks(x, [(290, 3.0, 1.0), (1050, 2.5, 0.45), (2900, 3.0, 0.8 * bright), (4500, 4.0, 0.3 * bright)], sr=MSR)
    bow = dsp.bandpass(dsp.noise(n, rng), 3200, 1.0, sr=MSR) * 0.05
    return (x + bow) * dsp.adsr(n, attack, 0.08, 0.85, 0.1, MSR) * 0.6


def whistle(f, dur, rng, vib=0.009, cut=False):
    """Tin whistle: nearly pure tone, breath, delayed vibrato, optional grace 'cut'."""
    n = S(dur + 0.08)
    t = dsp.tvec(n, MSR)
    onset = np.clip((t - 0.12) / 0.2, 0, 1)
    ff = f * (1 + vib * onset * np.sin(2 * np.pi * 5.4 * t))
    if cut:
        ff = np.where(t < 0.025, f * 2 ** (3 / 12), ff)
    x = dsp.sine(ff, n, MSR) + 0.22 * dsp.sine(ff * 2, n, MSR) + 0.06 * dsp.sine(ff * 3, n, MSR)
    breath = dsp.bandpass(dsp.noise(n, rng), f * 2.5, 2.0, sr=MSR) * 0.07
    return (x + breath) * dsp.adsr(n, 0.02, 0.05, 0.85, 0.06, MSR) * 0.2


def piano(f, dur, rng, vel=0.8):
    n = S(dur + 1.2)
    t = dsp.tvec(n, MSR)
    B = 0.00035
    x = np.zeros(n)
    life = 2.6 * (220.0 / max(f, 60.0)) ** 0.5
    for k in range(1, 11):
        fk = f * k * np.sqrt(1 + B * k * k)
        if fk > MSR * 0.45:
            break
        x += np.sin(2 * np.pi * fk * t + rng.uniform(0, 6)) * (vel ** (0.6 * k)) / k ** 1.1 * np.exp(-t / (life / (1 + 0.45 * k)))
    x[:S(0.01)] += dsp.lowpass(dsp.noise(S(0.01), rng), 2000, sr=MSR) * 0.1 * vel
    rel = np.clip(1 - (t - dur) / 0.25, 0, 1)
    return x * rel * vel * 0.35


def spiccato(f, dur, rng):
    """Short bouncing bow strokes for string ostinatos (a small section)."""
    n = S(dur + 0.05)
    x = sum(dsp.additive_saw(f * (1 + d), n, MSR, max_h=20) for d in (-0.004, 0.0, 0.004)) / 3
    x = dsp.peaks(x, [(300, 2.5, 1.0), (2600, 2.5, 0.6)], sr=MSR)
    t = dsp.tvec(n, MSR)
    return x * (1 - np.exp(-t / 0.006)) * np.exp(-t / 0.09) * 0.4


def strings(freqs, dur, attack=0.35, release=0.7, bright=2200.0):
    n = S(dur + release)
    x = np.zeros(n)
    for f in freqs:
        for d in (-0.005, 0.0, 0.005):
            x += dsp.additive_saw(f * (1 + d) * (1 + 0.004 * dsp.sine(5.0, n, MSR, phase0=d * 400)), n, MSR, max_h=22)
    x = dsp.lowpass(x, bright, sr=MSR)
    return x * dsp.adsr(n, attack, 0.3, 0.85, release, MSR) / (len(freqs) * 3.5)


def choir(freqs, dur, vowel="a", attack=0.5, release=0.9):
    import music
    return music.choir(freqs, dur, vowel, attack, release)


# ---------------------------------------------------------------- composition helpers

def hz(m):
    return dsp.midi_to_hz(m)


def power(root_midi):
    return [hz(root_midi), hz(root_midi + 7), hz(root_midi + 12)]


def open_chord(root, scale, deg):
    """Guitar voicing of a scale chord: root, fifth, octave, third, fifth."""
    c = dsp.chord(root, scale, deg)
    return [hz(c[0]), hz(c[2]), hz(c[0] + 12), hz(c[1] + 12), hz(c[2] + 12)]


RHYTHMS = [[1, 1], [0.5, 0.5, 1], [1.5, 0.5], [0.5, 0.5, 0.5, 0.5], [0.75, 0.25, 1], [1, 0.5, 0.5], [0.5, 1, 0.5]]


def phrase(rng, beats=8, span=(4, 11), density=0.75, runs=0.3):
    """A folk-ish phrase: stepwise motion with leaps, 8th-note runs, a long last note."""
    notes, t = [], 0.0
    d = int(rng.integers(span[0] + 2, span[1] - 1))
    while t < beats - 1.01:
        pat = [0.5, 0.5, 0.5, 0.5] if rng.random() < runs else RHYTHMS[int(rng.integers(len(RHYTHMS)))]
        for ln in pat:
            if t >= beats - 1.01:
                break
            if rng.random() < density or not notes:
                d = int(np.clip(d + rng.choice([-1, -1, 1, 1, 2, -2, 0, 3, -3, 4]), span[0], span[1]))
                notes.append([t, ln, d])
            t += ln
    notes.append([beats - 1.0, 1.0, int(np.clip(d + rng.choice([-1, 0, 1]), span[0], span[1]))])
    return notes


def snap(d, chord_degs, n=7):
    best = min(chord_degs, key=lambda c: min(abs((d - c) % n), abs((c - d) % n)))
    base = d - ((d - best) % n)
    return min([base, base + n], key=lambda c: abs(c - d))


def melody(s, play, root, scale, prog_at, bar0, bars, phrase_a, phrase_b, beats_per_bar=4, pan=0.15, gain=1.0, send=0.35,
           octave=24, ends=True):
    """Lay an AABA'-style melody over `bars` bars (2-bar phrases), snapping strong beats to the chord."""
    for p in range(bars // 2):
        ph = phrase_b if p % 4 == 2 else phrase_a
        for b, ln, d in ph:
            bar = bar0 + 2 * p + int(b // beats_per_bar)
            deg = prog_at(bar)
            dd = snap(d, [deg, deg + 2, deg + 4]) if (b % 1 == 0 and b % 2 == 0) or (ends and b >= 2 * beats_per_bar - 1) else d
            if p % 4 == 3 and b >= 2 * beats_per_bar - 1:
                dd = snap(dd, [deg])
            t = s.at(bar0 + 2 * p) + b * s.spb
            s.add(play(hz(dsp.degree(root + octave, scale, dd)), ln * s.spb * 0.95), t, pan=pan, gain=gain, send=send)


def glue(x, drive=1.25):
    """Bus saturation: a touch of tape-style compression before normalising."""
    return np.tanh(x * drive) / drive


class DCSong(Song):
    def render(self, verb=1.8, decay=1.8, target_db=-15.5):
        ir = dsp.reverb_ir(verb, self.rng, sr=MSR, decay=decay, stereo=True, predelay=0.018)
        mix = self.dry + dsp.convolve(self.wet, ir)[:len(self.dry)] * 1.3
        L = S(self.length)
        out = mix[:L].copy()
        tail = mix[L:]
        k = min(len(tail), L)
        out[:k] += tail[:k]
        out = glue(out / (np.max(np.abs(out)) + 1e-9) * 1.6)
        return dsp.rms_normalize(out, target_db)


def drums_rock(s, rng, bar, t, fill=False, double=False, crash_on=False, open_hats=False, half=False):
    spb = s.spb
    if crash_on:
        s.add(crash(rng), t, pan=0.35, gain=0.55, send=0.25)
    kicks = [0, 2.5] if not double else [0, 0.5, 1.5, 2, 2.5, 3.5]
    if half:
        kicks = [0, 1.75]
    for b in kicks:
        s.add(kick(rng), t + b * spb, gain=0.95, send=0.03)
    for b in ([2] if half else [1, 3]):
        s.add(snare(rng), t + b * spb, pan=-0.05, gain=0.75, send=0.2)
    for k in range(8):
        is_open = open_hats and k % 2 == 1
        s.add(hat(rng, is_open), t + k * spb / 2, pan=0.3, gain=0.5 if k % 2 else 0.7, send=0.05)
    if fill:
        for k, f in enumerate((180, 150, 120, 95)):
            s.add(tom(rng, f), t + (3 + k * 0.25) * spb, pan=0.4 - 0.25 * k, gain=0.7, send=0.2)


# ---------------------------------------------------------------- tracks

def track_menu():
    """Melancholic title theme: piano arpeggios, strings, a lone fiddle."""
    s = DCSong(74, 24, seed=111)
    rng = s.rng
    root, sc = dsp.note("D", 3), "minor"
    prog = [0, 5, 2, 6, 0, 3, 4, 4]
    pa = lambda bar: prog[(bar // 2) % len(prog)]
    a = phrase(rng, 8, (5, 11), 0.6, 0.15)
    b = phrase(rng, 8, (6, 12), 0.6, 0.2)
    for bar in range(s.bars):
        deg = pa(bar)
        ch = dsp.chord(root, sc, deg)
        t = s.at(bar)
        for k, m in enumerate([ch[0], ch[2], ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 12, ch[0] + 12, ch[2]]):
            s.add(piano(hz(m + 12), 0.6, rng, 0.55 + 0.15 * (k == 0)), t + k * s.spb / 2, pan=-0.2 + 0.05 * k, gain=0.6, send=0.45)
        if bar % 2 == 0:
            s.add(piano(hz(ch[0] - 12), 2 * s.beats * s.spb, rng, 0.7), t, gain=0.55, send=0.4)
            if bar >= 4:
                s.add(strings([hz(m) for m in ch], 2 * s.beats * s.spb, attack=1.0, release=1.2, bright=1600), t, gain=0.55, send=0.5)
        if bar in (7, 15, 23):
            s.add(timpani(rng, hz(root - 12)), t + 3 * s.spb, gain=0.6, send=0.4)
    melody(s, lambda f, d: fiddle(f, d, rng, vib=0.009, attack=0.12), root, sc, pa, 8, 16, a, b, pan=0.2, gain=0.85, send=0.5, octave=12)
    return s.render(verb=2.6, decay=2.4)


def track_oubliette():
    """The prison: muted-guitar ostinato that grows into a folk-rock beat with a fiddle lead."""
    s = DCSong(104, 40, seed=121)
    rng = s.rng
    root, sc = dsp.note("A", 2), "minor"
    prog = [0, 0, 5, 5, 2, 2, 6, 6]
    pa = lambda bar: prog[bar % len(prog)]
    a = phrase(rng, 8, (5, 12), 0.8, 0.35)
    b = phrase(rng, 8, (7, 13), 0.8, 0.45)
    w = phrase(rng, 8, (9, 15), 0.7, 0.3)
    for bar in range(s.bars):
        deg = pa(bar)
        ch = dsp.chord(root, sc, deg)
        t = s.at(bar)
        breakdown = 24 <= bar < 32
        # Palm-muted chugs (8ths), opening up on the last 8th.
        if not breakdown:
            for k in range(8):
                m = 0.85 if k < 7 else 0.2
                s.add(eguitar(power(ch[0] + 12), s.spb / 2 * (0.9 if k < 7 else 1.8), rng, mute=m, drive=6 if bar >= 8 else 3.5),
                      t + k * s.spb / 2, pan=-0.45, gain=0.5, send=0.06)
        # Picked bass.
        if bar >= 4 and not breakdown:
            for k, b8 in enumerate([0, 1.5, 2, 3, 3.5]):
                s.add(pick_bass(hz(ch[0] - 12 + (7 if k == 3 else 0)), s.spb * 0.45, rng), t + b8 * s.spb, gain=0.8, send=0.03)
        if bar >= 8 and not breakdown:
            drums_rock(s, rng, bar, t, fill=bar % 8 == 7, crash_on=bar in (8, 16, 32), open_hats=bar >= 16)
        elif bar >= 4 and not breakdown:
            for k in range(8):
                s.add(hat(rng), t + k * s.spb / 2, pan=0.3, gain=0.45, send=0.05)
            s.add(kick(rng), t, gain=0.8, send=0.03)
        if breakdown:
            if bar % 2 == 0:
                s.add(strings([hz(m + 12) for m in ch], 2 * s.beats * s.spb, attack=0.6, release=1.0), t, gain=0.6, send=0.5)
            for k in range(8):
                s.add(piano(hz(dsp.degree(root + 24, sc, deg + [0, 2, 4, 7, 4, 2, 0, 2][k])), 0.4, rng, 0.6), t + k * s.spb / 2,
                      pan=0.25, gain=0.55, send=0.4)
            s.add(tom(rng, 95, 0.3), t, gain=0.6, send=0.3)
            s.add(tom(rng, 95, 0.3), t + 2.5 * s.spb, gain=0.5, send=0.3)
        # Sustained distorted chords under the B section.
        if 16 <= bar < 24 and bar % 2 == 0:
            s.add(eguitar(power(ch[0] + 12), 2 * s.beats * s.spb * 0.98, rng, drive=8), t, pan=0.45, gain=0.32, send=0.15)
    melody(s, lambda f, d: fiddle(f, d, rng), root, sc, pa, 8, 16, a, b, pan=0.15, gain=0.95, send=0.3)
    melody(s, lambda f, d: fiddle(f, d, rng, attack=0.15), root, sc, pa, 24, 8, b, a, pan=0.1, gain=0.8, send=0.5, octave=12)
    melody(s, lambda f, d: whistle(f, d, rng, cut=rng.random() < 0.3), root, sc, pa, 32, 8, w, a, pan=-0.15, gain=0.85, send=0.35, octave=24)
    return s.render(verb=1.8, decay=1.9)


def track_promenade():
    """Promenade of the Condemned: bright folk-rock, acoustic strums, tin whistle lead."""
    s = DCSong(126, 32, seed=131)
    rng = s.rng
    root, sc = dsp.note("E", 3), "dorian"
    prog = [0, 6, 3, 0, 0, 6, 4, 4]
    pa = lambda bar: prog[bar % len(prog)]
    a = phrase(rng, 8, (7, 14), 0.85, 0.45)
    b = phrase(rng, 8, (9, 15), 0.8, 0.5)
    for bar in range(s.bars):
        deg = pa(bar)
        ch = dsp.chord(root, sc, deg)
        t = s.at(bar)
        voicing = open_chord(root - 12, sc, deg)
        for k, (b8, down, acc) in enumerate([(0, True, 1.0), (1, True, 0.6), (1.5, False, 0.7), (2.5, False, 0.7), (3, True, 0.8), (3.5, False, 0.6)]):
            s.add(strum(voicing, s.spb * 0.9, rng, down=down, accent=acc), t + b8 * s.spb, pan=-0.35, gain=0.9, send=0.15)
        if bar >= 2:
            for b8, off in ((0, 0), (1, 7), (2, 12), (3, 7)):
                s.add(pick_bass(hz(ch[0] - 12 + off), s.spb * 0.8, rng), t + b8 * s.spb, gain=0.75, send=0.03)
        if bar >= 4:
            drums_rock(s, rng, bar, t, fill=bar % 8 == 7, crash_on=bar in (4, 12, 20, 28), open_hats=bar >= 20)
            for k in range(4):
                s.add(tamb(rng), t + (k + 0.5) * s.spb, pan=0.45, gain=0.55, send=0.1)
        if 12 <= bar < 20 and bar % 2 == 0:
            s.add(strings([hz(m + 12) for m in ch], 2 * s.beats * s.spb, attack=0.5, release=0.8, bright=2800), t, gain=0.45, send=0.4)
    melody(s, lambda f, d: whistle(f, d, rng, cut=rng.random() < 0.35), root, sc, pa, 4, 16, a, b, pan=0.15, gain=1.0, send=0.35)
    melody(s, lambda f, d: fiddle(f, d, rng), root, sc, pa, 20, 12, b, a, pan=0.2, gain=0.9, send=0.35, octave=12)
    return s.render(verb=1.6, decay=1.7)


def track_ossuary():
    """Ossuary: choir and low piano, half-time taiko and toms, a lamenting fiddle, heavy guitars in B."""
    s = DCSong(90, 32, seed=141)
    rng = s.rng
    root, sc = dsp.note("C", 3), "harmonic"
    prog = [0, 5, 3, 4, 0, 5, 1, 4]
    pa = lambda bar: prog[(bar // 2) % len(prog)]
    a = phrase(rng, 8, (4, 10), 0.55, 0.15)
    b = phrase(rng, 8, (6, 12), 0.6, 0.25)
    for bar in range(s.bars):
        deg = pa(bar)
        ch = dsp.chord(root, sc, deg)
        t = s.at(bar)
        if bar % 2 == 0:
            s.add(choir([hz(m) for m in ch], 2 * s.beats * s.spb, "o", attack=0.8, release=1.2), t, gain=0.75, send=0.55)
        for k, o in enumerate([0, 4, 7, 4, 0, 4, 7, 9]):
            s.add(piano(hz(dsp.degree(root - 12, sc, deg) + o % 12), 0.45, rng, 0.65), t + k * s.spb / 2, pan=-0.2, gain=0.5, send=0.25)
        if bar >= 4:
            s.add(taiko(rng), t, gain=0.9, send=0.3)
            s.add(snare(rng, 170, 0.8), t + 2 * s.spb, gain=0.7, send=0.35)
            s.add(tom(rng, 80, 0.3), t + 3.5 * s.spb, gain=0.55, send=0.3)
            for k in range(4):
                s.add(hat(rng, k == 3), t + k * s.spb, pan=0.3, gain=0.4, send=0.1)
        if 16 <= bar < 28:
            if bar % 2 == 0:
                s.add(eguitar(power(ch[0] + 12), 2 * s.beats * s.spb * 0.98, rng, drive=9), t, pan=-0.4, gain=0.35, send=0.2)
                s.add(eguitar(power(ch[0] + 12), 2 * s.beats * s.spb * 0.98, rng, drive=9), t + 0.012, pan=0.4, gain=0.35, send=0.2)
            if bar % 4 == 0:
                s.add(crash(rng), t, pan=0.3, gain=0.45, send=0.3)
    melody(s, lambda f, d: fiddle(f, d, rng, vib=0.01, attack=0.12), root, sc, pa, 8, 24, a, b, pan=0.15, gain=0.95, send=0.45, octave=12)
    return s.render(verb=2.8, decay=2.6)


def track_stilt():
    """Stilt village: a swampy jig in 6/8 - bodhran, acoustic guitar, fiddle and whistle."""
    s = DCSong(264, 32, seed=151, beats=6)   # eighth notes, six to a bar
    rng = s.rng
    root, sc = dsp.note("D", 3), "dorian"
    prog = [0, 0, 6, 6, 3, 3, 4, 4]
    pa = lambda bar: prog[bar % len(prog)]
    a = phrase(rng, 12, (7, 13), 0.95, 0.7)
    b = phrase(rng, 12, (8, 14), 0.9, 0.6)
    for bar in range(s.bars):
        deg = pa(bar)
        ch = dsp.chord(root, sc, deg)
        t = s.at(bar)
        voicing = open_chord(root - 12, sc, deg)
        for e, acc, down in ((0, 1.0, True), (2, 0.6, False), (3, 0.9, True), (5, 0.6, False)):
            s.add(strum(voicing, s.spb * 1.6, rng, down=down, accent=acc), t + e * s.spb, pan=-0.35, gain=0.85, send=0.15)
        if bar >= 2:
            s.add(pick_bass(hz(ch[0] - 12), s.spb * 2.5, rng), t, gain=0.75, send=0.03)
            s.add(pick_bass(hz(ch[0] - 5), s.spb * 2.5, rng), t + 3 * s.spb, gain=0.65, send=0.03)
            for e in range(6):
                s.add(bodhran(rng, e in (0, 3)), t + e * s.spb, pan=0.15, gain=0.7 if e in (0, 3) else 0.4, send=0.1)
        if bar >= 8:
            s.add(kick(rng, 0.9), t, gain=0.7, send=0.03)
            s.add(snare(rng, 200, 0.7), t + 3 * s.spb, gain=0.5, send=0.2)
    melody(s, lambda f, d: fiddle(f, d, rng, vib=0.006, attack=0.03), root, sc, pa, 4, 16, a, b, beats_per_bar=6, pan=0.15, gain=0.95,
           send=0.3)
    melody(s, lambda f, d: whistle(f, d, rng, cut=True), root, sc, pa, 20, 12, b, a, beats_per_bar=6, pan=-0.15, gain=0.85, send=0.3,
           octave=36)
    return s.render(verb=1.7, decay=1.7)


def track_lung():
    """The Clockmaker's Lung: a clockwork piano ostinato over industrial drums and guitar riffs."""
    s = DCSong(112, 32, seed=161)
    rng = s.rng
    root, sc = dsp.note("B", 2), "minor"
    prog = [0, 0, 5, 3, 0, 0, 6, 4]
    pa = lambda bar: prog[bar % len(prog)]
    a = phrase(rng, 8, (6, 12), 0.7, 0.3)
    b = phrase(rng, 8, (8, 14), 0.75, 0.4)
    ost = [0, 7, 9, 7, 0, 7, 10, 7, 0, 7, 9, 7, 3, 2, 0, 2]
    for bar in range(s.bars):
        deg = pa(bar)
        ch = dsp.chord(root, sc, deg)
        t = s.at(bar)
        for k in range(16):
            s.add(piano(hz(ch[0] + 24 + ost[k]), 0.2, rng, 0.5 + 0.2 * (k % 4 == 0)), t + k * s.spb / 4, pan=0.2, gain=0.45, send=0.3)
        for k in range(4):
            s.add(dsp.modal([3100, 6600, 11500], [1, 0.4, 0.2], [0.012, 0.006, 0.004], 0.05, MSR, rng=rng) * 0.4, t + (k + 0.5) * s.spb,
                  pan=-0.5, gain=0.6, send=0.2)
        if bar >= 4:
            for k in range(4):
                s.add(kick(rng, 1.1, 46), t + k * s.spb, gain=0.85, send=0.03)
            s.add(clap(rng), t + 1 * s.spb, pan=-0.1, gain=0.6, send=0.3)
            s.add(clap(rng), t + 3 * s.spb, pan=-0.1, gain=0.6, send=0.3)
            for k in range(8):
                s.add(hat(rng, k % 4 == 2), t + k * s.spb / 2, pan=0.35, gain=0.45, send=0.05)
            for b8, ln in ((0, 0.75), (0.75, 0.75), (1.5, 0.5), (2.5, 0.5), (3, 1.0)):
                s.add(eguitar(power(ch[0] + 12), ln * s.spb * 0.9, rng, mute=0.4, drive=8), t + b8 * s.spb, pan=-0.4, gain=0.4, send=0.08)
        if 16 <= bar < 24 and bar % 2 == 0:
            s.add(choir([hz(m) for m in ch], 2 * s.beats * s.spb, "a"), t, gain=0.6, send=0.5)
            s.add(crash(rng), t, pan=0.3, gain=0.4, send=0.3)
    melody(s, lambda f, d: fiddle(f, d, rng, bright=1.2), root, sc, pa, 8, 24, a, b, pan=0.15, gain=0.9, send=0.35, octave=24)
    return s.render(verb=2.0, decay=2.0)


def track_passage():
    """The sluice passage: a breather - fingerpicked guitar, soft whistle, pad."""
    s = DCSong(84, 16, seed=171)
    rng = s.rng
    root, sc = dsp.note("G", 2), "major"
    prog = [0, 4, 5, 3, 0, 4, 3, 4]
    pa = lambda bar: prog[bar % len(prog)]
    a = phrase(rng, 8, (7, 13), 0.55, 0.15)
    b = phrase(rng, 8, (8, 14), 0.55, 0.2)
    for bar in range(s.bars):
        deg = pa(bar)
        ch = dsp.chord(root, sc, deg)
        t = s.at(bar)
        pattern = [ch[0], ch[2] + 12, ch[1] + 12, ch[2] + 12, ch[0] + 12, ch[2] + 12, ch[1] + 12, ch[2] + 12]
        for k, m in enumerate(pattern):
            s.add(guitar_string(hz(m), 1.2, rng, bright=0.55, decay=0.9978) * 0.35, t + k * s.spb / 2, pan=-0.3 + 0.08 * k, gain=0.8,
                  send=0.35)
        if bar % 2 == 0:
            s.add(strings([hz(m + 12) for m in ch], 2 * s.beats * s.spb, attack=1.2, release=1.4, bright=1400), t, gain=0.35, send=0.6)
    melody(s, lambda f, d: whistle(f, d, rng, vib=0.012), root, sc, pa, 4, 12, a, b, pan=0.2, gain=0.6, send=0.55, octave=24)
    return s.render(verb=2.4, decay=2.4, target_db=-18.0)


def track_boss():
    """Boss fights: double-kick rock, distorted riff, spiccato strings, choir stabs and a soaring fiddle."""
    s = DCSong(152, 32, seed=181)
    rng = s.rng
    root, sc = dsp.note("D", 2), "minor"
    riff = [(0, 0, 0.5), (0.5, 0, 0.5), (1, 3, 0.5), (1.5, 0, 0.5), (2, 5, 0.5), (2.5, 0, 0.5), (3, 6, 0.5), (3.5, 5, 0.5)]
    prog = [0, 0, 5, 6, 0, 0, 3, 4]
    pa = lambda bar: prog[bar % len(prog)]
    a = phrase(rng, 8, (8, 15), 0.85, 0.5)
    b = phrase(rng, 8, (10, 16), 0.85, 0.55)
    for bar in range(s.bars):
        deg = pa(bar)
        ch = dsp.chord(root, sc, deg)
        t = s.at(bar)
        for b8, step, ln in riff:
            m = dsp.degree(root + 12, sc, deg + step) if step else ch[0] + 12
            s.add(eguitar(power(m), ln * s.spb * 0.92, rng, mute=0.5 if step == 0 else 0.1, drive=9), t + b8 * s.spb, pan=-0.45, gain=0.42,
                  send=0.06)
            s.add(eguitar(power(m), ln * s.spb * 0.92, rng, mute=0.5 if step == 0 else 0.1, drive=9), t + b8 * s.spb + 0.01, pan=0.45,
                  gain=0.42, send=0.06)
        for k in range(8):
            s.add(pick_bass(hz(ch[0] - 12), s.spb * 0.45, rng), t + k * s.spb / 2, gain=0.7, send=0.02)
        drums_rock(s, rng, bar, t, fill=bar % 4 == 3, double=bar >= 8, crash_on=bar % 4 == 0, open_hats=False)
        if bar >= 8:
            for k in range(16):
                s.add(spiccato(hz(dsp.degree(root + 24, sc, deg + [0, 2, 4, 2][k % 4])), s.spb / 4, rng), t + k * s.spb / 4, pan=0.25,
                      gain=0.45, send=0.2)
        if bar % 2 == 0 and bar >= 4:
            s.add(choir([hz(m + 12) for m in ch], s.spb * 1.5, "a", attack=0.05, release=0.4), t, gain=0.55, send=0.4)
    melody(s, lambda f, d: fiddle(f, d, rng, bright=1.3), root, sc, pa, 16, 16, a, b, pan=0.1, gain=1.0, send=0.3, octave=24)
    return s.render(verb=1.6, decay=1.6, target_db=-15.0)


def track_death():
    """Short sting: a falling piano line over a string swell (not looped)."""
    rng = np.random.default_rng(191)
    n = S(6.0)
    out = np.zeros((n, 2))
    root = dsp.note("D", 3)
    for k, m in enumerate([12, 10, 8, 7, 5, 3, 2, 0]):
        x = piano(hz(root + m + 12), 0.5, rng, 0.7)
        st = dsp.to_stereo(x, -0.2 + 0.05 * k)
        i = S(0.22 * k)
        out[i:i + len(st)] += st[:n - i]
    sw = strings([hz(root), hz(root + 3), hz(root + 7)], 3.0, attack=1.5, release=2.0)
    st = dsp.to_stereo(sw, 0.0)
    out[S(0.8):S(0.8) + len(st)] += st[:n - S(0.8)] * 0.8
    ir = dsp.reverb_ir(3.0, rng, sr=MSR, decay=2.6, stereo=True)
    out = out + dsp.convolve(out * 0.5, ir)[:n]
    fade = np.clip((n - np.arange(n)) / S(1.5), 0, 1)[:, None]
    return dsp.rms_normalize(out * fade, -16.0)


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
