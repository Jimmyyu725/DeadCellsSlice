"""Dead Cells-flavoured replacements for the core combat and pickup sounds.

The originals in sfx.py are clean but thin.  These are layered the way action
games build impact sounds: a low body (pitch-dropping sine, saturated), a
crunchy mid transient (filtered noise, a little bit-crush grit), a wet or
metallic top layer, and a short room.  OVERRIDES replaces recipes (and
variant counts) in sfx.REGISTRY while keeping each event's mix metadata.
"""

import numpy as np

import dsp
import sfx
from dsp import SR, secs
from sfx import burst, finish, metal, thump, whoosh


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def sat(x, drive=2.0):
    return np.tanh(x * drive) / np.tanh(drive)


def sub_drop(rng, f0, f1, dur, tau):
    n = secs(dur)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / (dur * 0.25))
    return dsp.sine(f, n) * env_exp(n, tau)


def crunch(rng, dur=0.07, fc=1400, grit=6):
    x = dsp.bandpass(dsp.noise(secs(dur), rng), fc, 0.9) * env_exp(secs(dur), dur * 0.25)
    return dsp.crush(x / (np.abs(x).max() + 1e-9), grit) * 0.8 + x * 0.6


def splat(rng, dur=0.16):
    n = secs(dur)
    x = dsp.noise(n, rng, "pink")
    x = dsp.tv_filter(x, lambda t: 1600 * np.exp(-t / 0.05) + 350, kind="lp", order=2)
    x = dsp.peaks(x, [(500, 2.0, 1.0), (1100, 3.0, 0.5)]) + 0.3 * x
    return x * env_exp(n, dur * 0.3)


def room(x, rng, mix=0.18, dur=0.5, low_cut=110.0):
    """A short room, after a gentle low cut: small speakers turn sub energy into mud."""
    if low_cut:
        x = dsp.highpass(x, low_cut, order=1)
    return dsp.reverb(x, rng, mix=mix, dur=dur, decay=0.45)


def nz(x):
    return x / (np.abs(x).max() + 1e-9)


def stack(*parts):
    """Mix layers by peak-normalised gain, so ratios mean what they say."""
    n = max(len(p) for p, _ in parts)
    out = np.zeros(n)
    for p, g in parts:
        out[:len(p)] += nz(p) * g
    return out


def thwack(rng, fc=700, tau=0.016):
    n = secs(0.06)
    return dsp.bandpass(dsp.noise(n, rng), fc, 1.4) * env_exp(n, tau)


# ---------------------------------------------------------------- swings

def swing_light(rng):
    w = whoosh(rng, rng.uniform(0.15, 0.19), rng.uniform(500, 700), rng.uniform(2600, 3400), q=1.6, peak=0.28, curve=0.7)
    shing = metal(rng, rng.uniform(2900, 3600), 0.18, decay=0.07, bright=0.6) * env_exp(secs(0.18), 0.05)
    air = whoosh(rng, 0.14, 180, 420, q=0.8, peak=0.35) * 0.5
    return finish(stack((w, 1.0), (shing, 0.16), (air, 0.6)), fout=0.03)


def swing_heavy(rng):
    w = whoosh(rng, rng.uniform(0.3, 0.36), 160, 900, q=1.1, peak=0.42, curve=0.9)
    rumble = dsp.lowpass(dsp.noise(secs(0.34), rng, "brown"), 220) * np.sin(np.linspace(0, np.pi, secs(0.34))) ** 2
    flap = whoosh(rng, 0.2, 700, 1600, q=1.4, peak=0.5) * 0.3
    return finish(stack((w, 1.0), (rumble, 0.9), (flap, 1.0)), fout=0.04)


def swing_thrust(rng):
    n = secs(0.16)
    fft = dsp.highpass(dsp.noise(n, rng), 1800) * np.where(np.arange(n) < secs(0.02), np.arange(n) / secs(0.02), env_exp(n, 0.04))
    tone = dsp.sine(dsp.sweep(900, 1900, n), n) * np.sin(np.linspace(0, np.pi, n)) ** 3 * 0.08
    w = whoosh(rng, 0.13, 900, 3000, q=2.0, peak=0.2) * 0.8
    return finish(stack((fft, 0.8), (tone, 1.0), (w, 1.0)), fout=0.03)


def swing_flail(rng):
    dur = 0.42
    n = secs(dur)
    w = whoosh(rng, dur, 300, 1200, q=1.2, peak=0.5)
    am = 0.55 + 0.45 * np.sin(2 * np.pi * 9 * np.arange(len(w)) / SR) ** 2
    jingle = sum(metal(rng, rng.uniform(2200, 4200), 0.12, decay=0.03, bright=0.5) for _ in range(3))
    j = np.zeros(n)
    for k in range(4):
        j = dsp.mix_at(j, jingle * rng.uniform(0.3, 0.6), secs(0.06 + 0.08 * k))
    return finish(stack((w * am, 1.0), (j, 0.12)), fout=0.04)


# ---------------------------------------------------------------- impacts

def hit_flesh(rng):
    # Body high enough to carry on laptop speakers; the crunch and splat carry the "meat".
    body = sat(sub_drop(rng, rng.uniform(190, 220), 95, 0.1, 0.03), 3.0)
    cr = crunch(rng, 0.06, rng.uniform(1300, 1900), grit=5)
    wet = splat(rng, rng.uniform(0.12, 0.18))
    click = dsp.highpass(dsp.noise(secs(0.004), rng), 3000)
    x = stack((body, 0.5), (thwack(rng, rng.uniform(600, 850)), 0.7), (cr, 0.75), (wet, 0.6), (click, 0.35))
    return finish(room(sat(x, 1.6), rng, 0.12), fout=0.04, max_rms_db=-11.0)


def hit_crit(rng):
    base = hit_flesh(rng)
    ring = metal(rng, rng.uniform(1800, 2300), 0.6, decay=0.22, bright=0.8)
    shimmer = dsp.bell(rng.uniform(3200, 3800), 0.6, rng, bright=0.9, decay=0.25) * 0.5
    boom = sat(sub_drop(rng, 130, 50, 0.4, 0.13), 2.0)
    x = stack((base, 1.0), (ring, 0.35), (shimmer, 0.3), (boom, 0.45))
    return finish(room(sat(x, 1.4), rng, 0.2, 0.8), fout=0.08, max_rms_db=-11.0)


def hit_heavy(rng):
    body = sat(sub_drop(rng, 160, 70, 0.22, 0.06), 3.0)
    cr = crunch(rng, 0.1, 1000, grit=4)
    wet = splat(rng, 0.2)
    debris = sfx.scatter(rng, 0.35, 6, lambda: burst(rng, 0.02, fc=rng.uniform(2000, 5000), kind="bp", q=2.0, tau=0.006), 0.25,
                         start=0.03)
    x = stack((body, 0.6), (thwack(rng, 500, 0.025), 0.7), (cr, 0.8), (wet, 0.55), (debris, 0.3))
    return finish(room(sat(x, 1.5), rng, 0.16, 0.6), fout=0.06, max_rms_db=-10.5)


def enemy_death(rng):
    """Gore burst: a wet squelch, a bone crack, the body slumping."""
    squelch = splat(rng, 0.3) * 1.2
    gurgle = dsp.tv_filter(dsp.noise(secs(0.3), rng, "pink"), lambda t: 400 + 900 * abs(np.sin(t * 40)), kind="bp", q=4.0) * env_exp(secs(0.3), 0.1)
    crack = stack(*[(burst(rng, 0.015, fc=rng.uniform(2500, 4500), kind="bp", q=1.5, tau=0.003), 1.0)])
    fall = thump(rng, 110, 45, 0.25, click=0.1, decay=0.07)
    out = np.zeros(secs(0.6))
    out = dsp.mix_at(out, nz(squelch), 0, 1.0)
    out = dsp.mix_at(out, nz(gurgle), secs(0.02), 0.5)
    out = dsp.mix_at(out, nz(crack), secs(0.005), 0.7)
    out = dsp.mix_at(out, nz(sat(fall, 2.0)), secs(0.22), 0.45)
    return finish(room(out, rng, 0.15), fout=0.06)


def kill(rng):
    """The killing blow: a heavier hit plus a bright 'cha-ching' of released cells."""
    hit = hit_heavy(rng)
    ting = dsp.bell(rng.uniform(1500, 1700), 0.5, rng, bright=0.8, decay=0.3) * 0.5
    sparkle = sum(dsp.bell(f, 0.4, rng, bright=0.9, decay=0.15) * 0.3 for f in (2600, 3300))
    out = np.zeros(secs(0.7))
    out = dsp.mix_at(out, nz(hit), 0)
    out = dsp.mix_at(out, nz(ting), secs(0.04), 0.35)
    out = dsp.mix_at(out, nz(sparkle), secs(0.09), 0.25)
    return finish(out, fout=0.08, max_rms_db=-11.0)


# ---------------------------------------------------------------- shields

def shield_block(rng):
    clang = metal(rng, rng.uniform(380, 460), 0.5, ratios=(1.0, 1.6, 2.32, 2.97, 3.81, 4.9), decay=0.16, bright=0.85)
    thud = sat(sub_drop(rng, 170, 80, 0.14, 0.04), 2.0)
    scrape = burst(rng, 0.09, fc=2600, kind="bp", q=1.2, tau=0.025)
    x = stack((clang, 0.8), (thud, 0.5), (scrape, 0.35))
    return finish(room(sat(x, 1.3), rng, 0.18, 0.6), fout=0.06)


def shield_parry(rng):
    ting = metal(rng, rng.uniform(2100, 2400), 1.1, ratios=(1.0, 2.76, 5.4, 8.93), decay=0.55, bright=0.7)
    clang = metal(rng, 520, 0.4, decay=0.12, bright=0.8)
    boom = sat(sub_drop(rng, 140, 55, 0.5, 0.15), 2.0)
    swish = whoosh(rng, 0.25, 3000, 900, q=1.5, peak=0.15) * 0.5
    x = stack((ting, 0.7), (clang, 0.55), (boom, 0.45), (swish, 0.35))
    return finish(room(sat(x, 1.3), rng, 0.25, 1.0), fout=0.15, max_rms_db=-12.0)


# ---------------------------------------------------------------- player

def hurt(rng):
    body = sat(sub_drop(rng, 180, 75, 0.2, 0.06), 2.5)
    cr = crunch(rng, 0.08, 1100, grit=4)
    sting = dsp.sine(dsp.sweep(620, 380, secs(0.22)), secs(0.22)) + 0.6 * dsp.sine(dsp.sweep(655, 400, secs(0.22)), secs(0.22))
    sting *= env_exp(secs(0.22), 0.07) * 0.25
    x = stack((body, 0.5), (thwack(rng, 650), 0.6), (cr, 0.7), (sting, 0.45), (splat(rng, 0.12), 0.45))
    return finish(room(sat(x, 1.5), rng, 0.12), fout=0.05, max_rms_db=-11.5)


def jump(rng):
    cloth = whoosh(rng, 0.17, 700, 2000, q=1.0, peak=0.22, color="white") * 0.7
    scuff = burst(rng, 0.04, fc=rng.uniform(1300, 1900), kind="bp", q=1.0, tau=0.01)
    push = thump(rng, 120, 70, 0.06, click=0.0, decay=0.02) * 0.4
    return finish(stack((cloth, 1.0), (scuff, 0.6), (push, 1.0)))


def land(rng):
    thud = sat(thump(rng, 110, 55, 0.12, click=0.15, decay=0.035), 1.8)
    grit = sfx.scatter(rng, 0.14, 5, lambda: burst(rng, 0.012, fc=rng.uniform(2500, 5000), kind="bp", q=1.5, tau=0.003), 0.06)
    dust = whoosh(rng, 0.12, 900, 400, q=0.8, peak=0.1) * 0.3
    return finish(stack((thud, 1.0), (grit, 0.25), (dust, 1.0)))


def roll(rng):
    a = whoosh(rng, 0.3, 400, 1400, q=1.0, peak=0.3, color="white")
    b = whoosh(rng, 0.22, 600, 1800, q=1.2, peak=0.4, color="white")
    out = np.zeros(secs(0.42))
    out = dsp.mix_at(out, a, 0, 0.8)
    out = dsp.mix_at(out, b, secs(0.15), 0.5)
    out = dsp.mix_at(out, land(rng) * 0.4, secs(0.3))
    return finish(out, fout=0.04)


# ---------------------------------------------------------------- enemies

def enemy_alert(rng):
    """The attack tell: a bright, slightly rising double 'shing'."""
    n = secs(0.32)
    f = dsp.sweep(1750, 2050, n)
    x = dsp.sine(f, n) + 0.5 * dsp.sine(f * 1.5, n) + 0.25 * dsp.sine(f * 2.76, n)
    x *= env_exp(n, 0.09) * (1 - np.exp(-np.arange(n) / (0.002 * SR)))
    x2 = np.zeros(n)
    x2[secs(0.06):] = x[:n - secs(0.06)] * 0.55
    return finish(room(stack((x, 1.0), (x2, 1.0)), rng, 0.25, 0.7), fout=0.06)


def enemy_attack(rng):
    w = whoosh(rng, 0.22, 250, 1100, q=1.1, peak=0.35)
    grunt = dsp.peaks(dsp.additive_saw(dsp.sweep(140, 95, secs(0.18)), secs(0.18), max_h=30), [(500, 3, 1.0), (900, 4, 0.5)])
    grunt *= dsp.adsr(secs(0.18), 0.01, 0.05, 0.6, 0.08) * 0.15
    return finish(stack((w, 1.0), (grunt, 1.0)), fout=0.04)


# ---------------------------------------------------------------- pickups

def coin(rng):
    out = np.zeros(secs(0.45))
    for k in range(int(rng.integers(3, 5))):
        tink = dsp.modal([rng.uniform(3600, 4400) * r for r in (1.0, 1.47, 2.09)], [1, 0.5, 0.3], [0.08, 0.05, 0.03], 0.15, rng=rng)
        out = dsp.mix_at(out, tink, secs(0.035 * k + rng.uniform(0, 0.01)), 0.8 - 0.12 * k)
    pling = dsp.bell(rng.choice([1975.5, 2093.0]), 0.35, rng, bright=0.8, decay=0.2) * 0.35
    out = dsp.mix_at(out, pling, 0)
    return finish(out, fout=0.06)


def cell(rng):
    """A soft glassy blip rising into a two-note chime."""
    out = np.zeros(secs(0.55))
    blip = dsp.sine(dsp.sweep(500, 1300, secs(0.06)), secs(0.06)) * np.sin(np.linspace(0, np.pi, secs(0.06))) * 0.4
    out = dsp.mix_at(out, blip, 0)
    for k, f in enumerate((1318.5, 1975.5)):
        out = dsp.mix_at(out, dsp.bell(f, 0.4, rng, bright=0.6, decay=0.25) * (0.45 - 0.1 * k), secs(0.04 + 0.06 * k))
    return finish(room(out, rng, 0.2, 0.7), fout=0.08)


def bow_shoot(rng):
    twang = dsp.karplus(rng.uniform(95, 115), 0.35, rng, decay=0.993, bright=0.7) * 0.6
    w = whoosh(rng, 0.18, 2500, 700, q=1.5, peak=0.1) * 0.7
    creak = burst(rng, 0.05, fc=800, kind="bp", q=3.0, tau=0.015) * 0.3
    return finish(stack((twang, 1.0), (w, 1.0), (creak, 1.0)), fout=0.05)


def explode_fire(rng):
    boom = sat(sub_drop(rng, 130, 50, 0.7, 0.2), 2.5)
    blast = dsp.lowpass(dsp.noise(secs(0.9), rng, "pink"), 3000) * env_exp(secs(0.9), 0.18)
    crackle = sfx.scatter(rng, 0.9, 24, lambda: burst(rng, 0.008, fc=rng.uniform(1500, 6000), kind="bp", q=1.0, tau=0.002), 0.7, start=0.05)
    x = stack((boom, 0.6), (blast, 1.0), (crackle, 0.5))
    return finish(room(sat(x, 1.4), rng, 0.25, 1.2, low_cut=60.0), fout=0.2, max_rms_db=-11.0)


# ---------------------------------------------------------------- 0.6 systems

def secret_break(rng):
    """Masonry giving way: a crack, a deep thud, rubble trickling down."""
    crack = stack((burst(rng, 0.03, fc=2200, kind="bp", q=1.2, tau=0.006), 1.0), (burst(rng, 0.05, fc=900, kind="bp", q=1.0, tau=0.012), 0.8))
    thud = sat(sub_drop(rng, 140, 55, 0.35, 0.1), 2.5)
    rubble = sfx.scatter(rng, 0.9, 22, lambda: burst(rng, rng.uniform(0.015, 0.04), fc=rng.uniform(700, 3500), kind="bp", q=1.4,
                                                      tau=0.008), 0.7, start=0.05)
    out = np.zeros(secs(1.0))
    out = dsp.mix_at(out, nz(crack), 0, 0.9)
    out = dsp.mix_at(out, nz(thud), secs(0.01), 0.7)
    out = dsp.mix_at(out, nz(rubble), secs(0.05), 0.5)
    return finish(room(out, rng, 0.25, 0.9), fout=0.1)


def rune_pickup(rng):
    """An old, resonant chord swelling out of stone."""
    n = secs(2.2)
    x = sum(dsp.bell(f, 2.2, rng, bright=0.6, decay=1.2) * g for f, g in ((220.0, 1.0), (329.6, 0.7), (440.0, 0.6), (659.3, 0.4)))
    pad = sum(dsp.additive_saw(f, n, max_h=12) for f in (110.0, 164.8)) * dsp.adsr(n, 0.6, 0.3, 0.6, 0.8) * 0.15
    rise = whoosh(rng, 1.0, 300, 2400, q=1.2, peak=0.8) * 0.4
    return finish(room(stack((x, 1.0), (pad, 0.5), (rise, 0.4)), rng, 0.4, 2.0, low_cut=0), fout=0.4)


def curse(rng):
    """A cursed chest's seal breaking: a dissonant low chord and a breath."""
    n = secs(1.6)
    chord = sum(dsp.additive_saw(f * (1 + 0.006 * dsp.sine(rng.uniform(4, 7), n)), n, max_h=18) for f in (98.0, 103.8, 146.8))
    chord = dsp.lowpass(chord, 900) * dsp.adsr(n, 0.05, 0.3, 0.6, 0.8)
    breath = whoosh(rng, 1.2, 1200, 300, q=0.8, peak=0.2) * 0.6
    chains = sfx.scatter(rng, 0.6, 6, lambda: metal(rng, rng.uniform(1600, 2600), 0.12, decay=0.04, bright=0.6), 0.4)
    return finish(room(stack((chord, 1.0), (breath, 0.5), (chains, 0.35)), rng, 0.35, 1.6, low_cut=0), fout=0.3)


def timed_open(rng):
    """The timed vault: a clock chime and heavy bolts sliding back."""
    out = np.zeros(secs(1.8))
    for k, f in enumerate((1318.5, 987.8, 1174.7, 784.0)):
        out = dsp.mix_at(out, nz(dsp.bell(f, 1.0, rng, bright=0.7, decay=0.5)) * 0.4, secs(0.12 * k))
    bolts = stack((metal(rng, 380, 0.3, decay=0.1), 1.0), (burst(rng, 0.2, fc=900, kind="bp", q=1.0, tau=0.06), 0.6))
    out = dsp.mix_at(out, nz(bolts) * 0.6, secs(0.55))
    out = dsp.mix_at(out, nz(sat(sub_drop(rng, 120, 50, 0.4, 0.12), 2.0)) * 0.6, secs(0.6))
    return finish(room(out, rng, 0.3, 1.4), fout=0.3)


def mutation(rng):
    """Taking a mutation: a wet organic squelch melting into a chime."""
    squ = splat(rng, 0.35)
    wob = dsp.sine(dsp.sweep(180, 90, secs(0.4)), secs(0.4)) * (1 + 0.5 * dsp.sine(14, secs(0.4))) * env_exp(secs(0.4), 0.15)
    chime = sum(dsp.bell(f, 0.8, rng, bright=0.7, decay=0.4) for f in (880.0, 1318.5))
    out = np.zeros(secs(1.2))
    out = dsp.mix_at(out, nz(squ) * 0.7, 0)
    out = dsp.mix_at(out, nz(wob) * 0.5, secs(0.02))
    out = dsp.mix_at(out, nz(chime) * 0.5, secs(0.25))
    return finish(room(out, rng, 0.3, 1.0), fout=0.2)


def vine_grow(rng):
    """Rustling leaves and creaking wood climbing upward."""
    n = secs(1.4)
    rustle = dsp.tv_filter(dsp.noise(n, rng, "pink"), lambda t: 800 + 2400 * t / 1.4, kind="bp", q=1.0)
    rustle *= (0.5 + 0.5 * np.abs(dsp.sine(9, n))) * dsp.adsr(n, 0.1, 0.2, 0.8, 0.4)
    creaks = sfx.scatter(rng, 1.4, 5, lambda: sfx.creak(rng, rng.uniform(0.1, 0.2), rng.uniform(250, 400), rng.uniform(420, 600)), 1.1)
    return finish(room(stack((rustle, 1.0), (creaks, 0.6)), rng, 0.2, 0.8), fout=0.2)


def status_fire(rng):
    """Catching fire: a soft whoomp with crackles."""
    w = whoosh(rng, 0.45, 200, 1400, q=0.9, peak=0.25) * 1.0
    body = sat(sub_drop(rng, 120, 60, 0.3, 0.1), 2.0)
    crackle = sfx.scatter(rng, 0.5, 10, lambda: burst(rng, 0.006, fc=rng.uniform(2000, 6000), kind="bp", q=1.0, tau=0.0015), 0.4, start=0.05)
    return finish(stack((w, 1.0), (body, 0.5), (crackle, 0.45)), fout=0.1)


def status_ice(rng):
    """Freezing: crystalline crackling and a glassy ring."""
    crackle = sfx.scatter(rng, 0.5, 16, lambda: metal(rng, rng.uniform(3000, 6500), 0.05, decay=0.012, bright=0.5), 0.35)
    ring = dsp.bell(2637.0, 0.6, rng, bright=0.9, decay=0.3)
    hiss = burst(rng, 0.4, fc=5000, kind="hp", tau=0.1)
    return finish(room(stack((crackle, 1.0), (ring, 0.35), (hiss, 0.3)), rng, 0.25, 0.7, low_cut=200), fout=0.1)


def status_poison(rng):
    """Poison taking hold: a few thick bubbles."""
    out = np.zeros(secs(0.5))
    for k in range(4):
        n = secs(0.06)
        b = dsp.sine(dsp.sweep(rng.uniform(300, 500), rng.uniform(700, 1100), n), n) * np.sin(np.linspace(0, np.pi, n))
        out = dsp.mix_at(out, b, secs(0.07 * k + rng.uniform(0, 0.03)), 0.7 - 0.1 * k)
    return finish(stack((out, 1.0), (splat(rng, 0.2), 0.3)), fout=0.05)


def status_bleed(rng):
    """Bleeding: a quick wet slice."""
    slice_ = whoosh(rng, 0.09, 2500, 5000, q=2.0, peak=0.15)
    wet = splat(rng, 0.14)
    return finish(stack((slice_, 0.7), (wet, 0.8)), fout=0.05)


def malaise(rng):
    """Malaise grows: a sick, detuned swell."""
    n = secs(1.2)
    x = sum(dsp.additive_saw(f * (1 + 0.01 * dsp.sine(rng.uniform(2, 5), n)), n, max_h=14) for f in (138.6, 146.8, 207.7))
    x = dsp.lowpass(x, 1200) * dsp.adsr(n, 0.3, 0.2, 0.7, 0.6)
    return finish(room(x, rng, 0.35, 1.2, low_cut=0), fout=0.3)


NEW = {
    "secret.break": (secret_break, 2, sfx.M(0.9, (0.95, 1.05), 0.1, 2)),
    "rune.pickup": (rune_pickup, 1, sfx.M(0.85, (1.0, 1.0), voices=1, spatial=False)),
    "curse": (curse, 1, sfx.M(0.85, (1.0, 1.0), voices=1, spatial=False)),
    "timed.open": (timed_open, 1, sfx.M(0.85, (1.0, 1.0), voices=1)),
    "mutation": (mutation, 1, sfx.M(0.75, (1.0, 1.0), voices=1, spatial=False)),
    "vine.grow": (vine_grow, 1, sfx.M(0.75, voices=1)),
    "status.fire": (status_fire, 2, sfx.M(0.5, (0.9, 1.1), 0.12, 3)),
    "status.ice": (status_ice, 2, sfx.M(0.5, (0.95, 1.08), 0.12, 3)),
    "status.poison": (status_poison, 2, sfx.M(0.45, (0.9, 1.15), 0.12, 3)),
    "status.bleed": (status_bleed, 2, sfx.M(0.45, (0.9, 1.1), 0.12, 3)),
    "malaise.up": (malaise, 1, sfx.M(0.6, (1.0, 1.0), voices=1, spatial=False)),
}


# id -> (recipe, variants); metadata stays as in sfx.REGISTRY
OVERRIDES = {
    "swing.light": (swing_light, 4),
    "swing.heavy": (swing_heavy, 3),
    "swing.thrust": (swing_thrust, 3),
    "swing.flail": (swing_flail, 2),
    "hit.flesh": (hit_flesh, 5),
    "hit.crit": (hit_crit, 3),
    "hit.heavy": (hit_heavy, 3),
    "enemy.death": (enemy_death, 3),
    "enemy.kill": (kill, 3),
    "shield.block": (shield_block, 3),
    "shield.parry": (shield_parry, 2),
    "player.hurt": (hurt, 3),
    "player.jump": (jump, 3),
    "player.land": (land, 3),
    "player.roll": (roll, 2),
    "enemy.alert": (enemy_alert, 2),
    "enemy.attack": (enemy_attack, 3),
    "pickup.gold": (coin, 4),
    "pickup.cell": (cell, 3),
    "bow.shoot": (bow_shoot, 3),
    "explode.fire": (explode_fire, 2),
}


def apply():
    for sid, (fn, variants) in OVERRIDES.items():
        _, _, meta = sfx.REGISTRY[sid]
        sfx.REGISTRY[sid] = (fn, variants, meta)
    sfx.REGISTRY.update(NEW)
