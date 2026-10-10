"""Small numpy DSP toolkit for the procedural sound effects and music.

Everything works on float64 numpy arrays in [-1, 1]; stereo signals are
(n, 2) arrays.  No scipy: static filters are applied in the frequency domain,
time-varying filters with a short-time FFT (overlap-add).
"""

import math
import wave

import numpy as np

SR = 44100


def secs(d, sr=SR):
    return max(1, int(round(d * sr)))


def tvec(n, sr=SR):
    return np.arange(n) / sr


def silence(d, sr=SR):
    return np.zeros(secs(d, sr))


# ---------------------------------------------------------------- envelopes

def exp_env(n, tau, sr=SR):
    """exp(-t / tau)."""
    return np.exp(-tvec(n, sr) / max(tau, 1e-4))


def adsr(n, a, d, s, r, sr=SR):
    """Attack/decay/sustain/release envelope filling n samples (release at the end)."""
    a_n, d_n, r_n = secs(a, sr), secs(d, sr), secs(r, sr)
    s_n = max(0, n - a_n - d_n - r_n)
    env = np.concatenate([
        np.linspace(0.0, 1.0, a_n, endpoint=False),
        np.linspace(1.0, s, d_n, endpoint=False),
        np.full(s_n, s),
        np.linspace(s, 0.0, r_n),
    ])
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)))
    return env[:n]


def ramp(n, a, b, curve=1.0):
    x = np.linspace(0.0, 1.0, n) ** curve
    return a + (b - a) * x


def fade(x, fin=0.002, fout=0.01, sr=SR):
    x = x.copy()
    i, o = min(len(x), secs(fin, sr)), min(len(x), secs(fout, sr))
    if i > 1:
        x[:i] *= np.linspace(0, 1, i)[:, None] if x.ndim == 2 else np.linspace(0, 1, i)
    if o > 1:
        x[-o:] *= np.linspace(1, 0, o)[:, None] if x.ndim == 2 else np.linspace(1, 0, o)
    return x


# ---------------------------------------------------------------- sources

def noise(n, rng, color="white"):
    w = rng.standard_normal(n)
    if color == "white":
        return w / 3.0
    spec = np.fft.rfft(w)
    f = np.fft.rfftfreq(n)
    f[0] = f[1] if n > 1 else 1.0
    if color == "pink":
        spec /= np.sqrt(f)
    elif color == "brown":
        spec /= f
    out = np.fft.irfft(spec, n)
    return out / (np.max(np.abs(out)) + 1e-9) * 0.8


def phase_of(freq, n, sr=SR):
    """Phase accumulator for a constant or per-sample frequency array."""
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    return 2 * np.pi * np.cumsum(f) / sr


def sine(freq, n, sr=SR, phase0=0.0):
    return np.sin(phase_of(freq, n, sr) + phase0)


def additive_saw(freq, n, sr=SR, max_h=60, rolloff=1.0, phase_jitter=None):
    """Band-limited sawtooth by additive synthesis (freq constant or array)."""
    ph = phase_of(freq, n, sr)
    f0 = float(np.max(freq)) if np.ndim(freq) else float(freq)
    out = np.zeros(n)
    hmax = int(min(max_h, (sr * 0.45) // max(f0, 1.0)))
    for k in range(1, hmax + 1):
        off = phase_jitter[k % len(phase_jitter)] if phase_jitter is not None else 0.0
        out += np.sin(k * ph + off) / (k ** rolloff)
    return out * 0.55


def additive_square(freq, n, sr=SR, max_h=40):
    ph = phase_of(freq, n, sr)
    f0 = float(np.max(freq)) if np.ndim(freq) else float(freq)
    out = np.zeros(n)
    hmax = int(min(max_h, (sr * 0.45) // max(f0, 1.0)))
    for k in range(1, hmax + 1, 2):
        out += np.sin(k * ph) / k
    return out * 0.8


def sweep(f0, f1, n, curve="exp"):
    if curve == "exp":
        return f0 * (f1 / f0) ** np.linspace(0, 1, n)
    return np.linspace(f0, f1, n)


def karplus(freq, dur, rng, decay=0.996, bright=0.5, sr=SR, pick=0.5):
    """Plucked string (Karplus-Strong), vectorised one period at a time."""
    n = secs(dur, sr)
    period = max(2, int(round(sr / freq)))
    burst = rng.uniform(-1, 1, period)
    # Brightness: blend the burst with a smoothed copy; pick position comb.
    sm = np.convolve(burst, np.ones(3) / 3, mode="same")
    burst = bright * burst + (1 - bright) * sm
    k = int(period * pick)
    if 0 < k < period:
        burst = burst - np.roll(burst, k) * 0.5
    out = np.zeros(n + period + 1)
    out[:period] = burst
    pos = period
    while pos < n:
        end = min(pos + period, n)
        seg = out[pos - period:end - period]
        nxt = out[pos - period + 1:end - period + 1]
        out[pos:end] = decay * 0.5 * (seg + nxt)
        pos = end
    return out[:n]


def modal(freqs, amps, decays, dur, sr=SR, rng=None, detune=0.0):
    """Sum of exponentially decaying sines (bells, metal, glass)."""
    n = secs(dur, sr)
    t = tvec(n, sr)
    out = np.zeros(n)
    for f, a, d in zip(freqs, amps, decays):
        if f >= sr * 0.48:
            continue
        ff = f * (1 + (rng.uniform(-detune, detune) if rng is not None and detune else 0.0))
        out += a * np.sin(2 * np.pi * ff * t + (rng.uniform(0, 6.28) if rng is not None else 0.0)) * np.exp(-t / d)
    return out


BELL_RATIOS = [0.5, 1.0, 1.183, 1.506, 2.0, 2.514, 2.662, 3.011, 4.166, 5.433]
BELL_AMPS = [0.35, 1.0, 0.55, 0.4, 0.6, 0.25, 0.22, 0.18, 0.12, 0.07]


def bell(freq, dur, rng, bright=1.0, decay=1.0, sr=SR):
    d = [2.6, 1.8, 1.2, 1.0, 0.9, 0.55, 0.5, 0.4, 0.3, 0.2]
    amps = [a * (bright ** i) for i, a in enumerate(BELL_AMPS)]
    x = modal([freq * r for r in BELL_RATIOS], amps, [v * decay for v in d], dur, sr, rng, detune=0.002)
    n = len(x)
    strike = noise(min(n, secs(0.01, sr)), rng) * 0.3
    x[:len(strike)] += strike
    return x


# ---------------------------------------------------------------- filters

def _spectral(x, gain_fn, sr=SR):
    n = len(x)
    spec = np.fft.rfft(x, n)
    f = np.fft.rfftfreq(n, 1.0 / sr)
    return np.fft.irfft(spec * gain_fn(f), n)


def lowpass(x, fc, order=2, sr=SR):
    return _spectral(x, lambda f: 1.0 / np.sqrt(1.0 + (f / max(fc, 1.0)) ** (2 * order)), sr)


def highpass(x, fc, order=2, sr=SR):
    def g(f):
        r = np.where(f > 0, (max(fc, 1.0) / np.maximum(f, 1e-6)) ** (2 * order), 1e12)
        return 1.0 / np.sqrt(1.0 + r)
    return _spectral(x, g, sr)


def bandpass(x, f0, q=1.0, sr=SR):
    def g(f):
        ff = np.maximum(f, 1e-6)
        return 1.0 / np.sqrt(1.0 + q * q * (ff / f0 - f0 / ff) ** 2)
    return _spectral(x, g, sr)


def peaks(x, bands, sr=SR):
    """Sum of resonant band-passes (formants): bands = [(f0, q, gain), ...]."""
    def g(f):
        ff = np.maximum(f, 1e-6)
        out = np.zeros_like(f)
        for f0, q, gain in bands:
            out += gain / np.sqrt(1.0 + q * q * (ff / f0 - f0 / ff) ** 2)
        return out
    return _spectral(x, g, sr)


def tv_filter(x, cutoff_fn, kind="lp", order=2, q=2.0, frame=1024, hop=256, sr=SR):
    """Time-varying filter by STFT overlap-add.  cutoff_fn(t_seconds) -> Hz."""
    n = len(x)
    win = np.hanning(frame)
    pad = np.concatenate([np.zeros(frame), x, np.zeros(frame)])
    out = np.zeros_like(pad)
    norm = np.zeros_like(pad)
    f = np.fft.rfftfreq(frame, 1.0 / sr)
    ff = np.maximum(f, 1e-6)
    for start in range(0, len(pad) - frame, hop):
        t = (start + frame / 2 - frame) / sr
        fc = max(20.0, float(cutoff_fn(max(0.0, t))))
        seg = pad[start:start + frame] * win
        spec = np.fft.rfft(seg)
        if kind == "lp":
            gain = 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))
        elif kind == "hp":
            gain = 1.0 / np.sqrt(1.0 + (fc / ff) ** (2 * order))
        else:
            gain = 1.0 / np.sqrt(1.0 + q * q * (ff / fc - fc / ff) ** 2)
        out[start:start + frame] += np.fft.irfft(spec * gain, frame) * win
        norm[start:start + frame] += win * win
    out = out / np.maximum(norm, 1e-6)
    return out[frame:frame + n]


# ---------------------------------------------------------------- effects

def distort(x, drive=2.0):
    return np.tanh(x * drive) / np.tanh(drive)


def crush(x, bits=6):
    q = 2 ** bits
    return np.round(x * q) / q


def to_stereo(x, pan=0.0):
    """Equal-power pan, pan in [-1, 1]."""
    if x.ndim == 2:
        return x
    a = (pan + 1) * math.pi / 4
    return np.stack([x * math.cos(a), x * math.sin(a)], axis=1)


def reverb_ir(dur, rng, sr=SR, decay=1.4, damp_start=9000.0, damp_end=1800.0, stereo=True, predelay=0.012,
              early=8):
    n = secs(dur, sr)
    t = tvec(n, sr)
    chans = []
    for c in range(2 if stereo else 1):
        tail = rng.standard_normal(n) * np.exp(-t * 6.9 / decay)
        tail = tv_filter(tail, lambda s: damp_start * (damp_end / damp_start) ** min(1.0, s / decay), sr=sr)
        er = np.zeros(n)
        for k in range(early):
            idx = int(sr * (predelay + rng.uniform(0.003, 0.06)))
            if idx < n:
                er[idx] += rng.uniform(0.3, 0.8) * (1 if rng.random() < 0.5 else -1)
        pd = secs(predelay, sr)
        tail = np.concatenate([np.zeros(pd), tail])[:n]
        chans.append(er * 0.5 + tail * 0.35)
    ir = np.stack(chans, axis=1) if stereo else chans[0]
    return ir / (np.sqrt(np.sum(ir ** 2)) + 1e-9)


def convolve(x, ir):
    """FFT convolution; x mono or stereo, ir mono or stereo.  Output stereo if either is."""
    if x.ndim == 1 and ir.ndim == 2:
        x = np.stack([x, x], axis=1)
    if x.ndim == 2 and ir.ndim == 1:
        ir = np.stack([ir, ir], axis=1)
    n = len(x) + len(ir) - 1
    size = 1 << (n - 1).bit_length()
    if x.ndim == 1:
        return np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:n]
    out = np.zeros((n, 2))
    for c in range(2):
        out[:, c] = np.fft.irfft(np.fft.rfft(x[:, c], size) * np.fft.rfft(ir[:, c], size), size)[:n]
    return out


def reverb(x, rng, mix=0.25, dur=1.6, decay=1.4, sr=SR, stereo=False, keep_length=False, **kw):
    ir = reverb_ir(dur, rng, sr=sr, decay=decay, stereo=stereo, **kw)
    wet = convolve(x, ir)
    dry = x
    if dry.ndim == 1 and wet.ndim == 2:
        dry = np.stack([dry, dry], axis=1)
    pad = len(wet) - len(dry)
    dry = np.pad(dry, ((0, pad), (0, 0)) if dry.ndim == 2 else (0, pad))
    out = dry * (1 - mix) + wet * mix * 2.2
    return out[:len(x)] if keep_length else out


def mix_at(dst, src, at, gain=1.0):
    """Add src into dst starting at sample `at` (grows dst if needed)."""
    end = at + len(src)
    if end > len(dst):
        shape = (end - len(dst),) + dst.shape[1:]
        dst = np.concatenate([dst, np.zeros(shape)])
    dst[at:end] += src * gain
    return dst


def normalize(x, peak=0.89):
    m = np.max(np.abs(x))
    return x if m < 1e-9 else x * (peak / m)


def rms_normalize(x, target_db=-16.0, peak=0.95):
    r = np.sqrt(np.mean(x ** 2)) + 1e-12
    x = x * (10 ** (target_db / 20) / r)
    m = np.max(np.abs(x))
    if m > peak:
        x = np.tanh(x / m * 1.2) / np.tanh(1.2) * peak if m > peak * 1.4 else x * (peak / m)
    return x


def trim(x, threshold=1e-4, sr=SR, tail=0.02):
    mag = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)
    idx = np.nonzero(mag > threshold)[0]
    if len(idx) == 0:
        return x[:secs(0.05, sr)]
    end = min(len(x), idx[-1] + secs(tail, sr))
    return x[:end]


def write_wav(path, x, sr=SR):
    x = np.clip(x, -1.0, 1.0)
    data = (x * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1 if x.ndim == 1 else 2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


# ---------------------------------------------------------------- music helpers

NOTE_NAMES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7,
              "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def midi_to_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def note(name, octave):
    return 12 * (octave + 1) + NOTE_NAMES[name]


SCALES = {
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic": [0, 2, 3, 5, 7, 8, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "pentatonic": [0, 3, 5, 7, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
}


def degree(root, scale, d):
    """MIDI note of scale degree d (0-based, may be negative or > len)."""
    s = SCALES[scale]
    octv, idx = divmod(d, len(s))
    return root + 12 * octv + s[idx]


def chord(root, scale, d, size=3):
    return [degree(root, scale, d + 2 * k) for k in range(size)]
