"""Procedural sound effects.  Each recipe(rng) returns a mono float array at
dsp.SR; REGISTRY maps event id -> (recipe, variants, metadata) where the
metadata ends up in the Unity sound bank (volume, pitch range, cooldown,
max voices, spatial)."""

import numpy as np

import dsp
from dsp import SR, secs

# ---------------------------------------------------------------- building blocks


def whoosh(rng, dur, f0, f1, q=1.4, peak=0.4, color="pink", curve=1.0):
    n = secs(dur)
    x = dsp.noise(n, rng, color)
    x = dsp.tv_filter(x, lambda t: f0 * (f1 / f0) ** min(1.0, (t / dur) ** curve), kind="bp", q=q)
    t = np.linspace(0, 1, n)
    env = np.where(t < peak, (t / peak) ** 1.6, ((1 - t) / (1 - peak)) ** 1.8)
    return dsp.normalize(x * env)


def thump(rng, f0, f1, dur, click=0.25, decay=None):
    n = secs(dur)
    x = dsp.sine(dsp.sweep(f0, f1, n), n) * dsp.exp_env(n, decay or dur * 0.35)
    c = dsp.lowpass(dsp.noise(secs(0.012), rng), 3000) * click
    x[:len(c)] += c
    return x


def burst(rng, dur, fc=2500, kind="lp", q=1.0, tau=None):
    n = secs(dur)
    x = dsp.noise(n, rng)
    x = dsp.lowpass(x, fc) if kind == "lp" else dsp.highpass(x, fc) if kind == "hp" else dsp.bandpass(x, fc, q)
    return x * dsp.exp_env(n, tau or dur * 0.3)


def metal(rng, base, dur, ratios=(1.0, 1.52, 2.33, 3.17, 4.08, 5.21), decay=0.25, bright=0.8):
    amps = [bright ** i for i in range(len(ratios))]
    decs = [decay / (1 + 0.35 * i) for i in range(len(ratios))]
    return dsp.modal([base * r for r in ratios], amps, decs, dur, rng=rng, detune=0.004)


def chirp(rng, f0, f1, dur, harm=0.2):
    n = secs(dur)
    f = dsp.sweep(f0, f1, n)
    x = dsp.sine(f, n) + harm * dsp.sine(f * 2, n)
    return x * dsp.adsr(n, 0.003, dur * 0.4, 0.4, dur * 0.4)


def scatter(rng, out_len, count, maker, spread, start=0.0):
    out = np.zeros(secs(out_len))
    for _ in range(count):
        at = secs(start + rng.uniform(0, spread))
        out = dsp.mix_at(out, maker(), at)
    return out


def layer(*parts):
    n = max(len(p) for p, _ in parts)
    out = np.zeros(n)
    for p, g in parts:
        out[:len(p)] += p * g
    return out


def room(rng, x, mix=0.18, dur=0.8, decay=0.6):
    return dsp.trim(dsp.reverb(x, rng, mix=mix, dur=dur, decay=decay), threshold=2e-4)


def finish(x, fin=0.001, fout=0.02, max_rms_db=-13.0):
    """Trim, de-click, remove DC/rumble, peak-normalise, then cap loudness so
    dense sounds (hits, buzzes) do not dwarf sparse ones."""
    x = dsp.highpass(dsp.trim(x), 28, order=2)
    x = dsp.normalize(dsp.fade(x, fin, fout))
    rms = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
    if rms > max_rms_db:
        x *= 10 ** ((max_rms_db - rms) / 20)
    return x


# ---------------------------------------------------------------- player


def step(rng):
    tap = burst(rng, 0.06, fc=rng.uniform(900, 1500), kind="bp", q=1.2, tau=0.012)
    low = thump(rng, 140, 80, 0.06, click=0.0, decay=0.015) * 0.6
    grit = burst(rng, 0.05, fc=3000, kind="bp", q=1.0, tau=0.006) * 0.15
    return finish(dsp.lowpass(layer((tap, 1.0), (low, 1.0), (grit, 1.0)), 4000))


def jump(rng):
    w = whoosh(rng, 0.2, 500, 1500, q=1.2, peak=0.25)
    scuff = burst(rng, 0.05, fc=1800, kind="bp", q=0.8, tau=0.012)
    return finish(layer((w, 0.8), (scuff, 0.6)))


def double_jump(rng):
    w = whoosh(rng, 0.32, 700, 3200, q=1.6, peak=0.3, curve=0.7)
    n = secs(0.45)
    f = dsp.sweep(520, 1560, n)
    glide = (dsp.sine(f, n) * 0.6 + dsp.sine(f * 2.01, n) * 0.25 + dsp.sine(f * 3.02, n) * 0.1) * dsp.adsr(n, 0.01, 0.1, 0.5, 0.3)
    sparkle = scatter(rng, 0.45, 6, lambda: metal(rng, rng.uniform(3500, 6000), 0.12, decay=0.05) * 0.25, 0.3, 0.05)
    return finish(room(rng, layer((w, 0.9), (glide, 0.35), (sparkle, 0.6)), mix=0.25))


def land(rng):
    t = thump(rng, 120, 45, 0.16, click=0.3)
    gravel = burst(rng, 0.12, fc=1600, tau=0.03)
    return finish(layer((t, 1.0), (gravel, 0.5)))


def roll(rng):
    w = whoosh(rng, 0.34, 1400, 600, q=0.9, peak=0.2, color="white")
    cloth = burst(rng, 0.3, fc=900, kind="bp", q=0.7, tau=0.1)
    tap = thump(rng, 100, 60, 0.08, click=0.1)
    return finish(layer((w, 0.8), (cloth, 0.4), (tap, 0.4)))


def mantle(rng):
    scrape = whoosh(rng, 0.2, 2200, 1200, q=1.0, peak=0.3, color="white")
    grip = thump(rng, 160, 90, 0.07, click=0.2)
    return finish(layer((scrape, 0.6), (grip, 0.8)))


def hurt(rng):
    t = thump(rng, 180, 50, 0.22, click=0.5)
    crunch = dsp.distort(burst(rng, 0.12, fc=2200, tau=0.03), 3.0)
    whomp = dsp.lowpass(dsp.noise(secs(0.25), rng, "brown"), 300) * dsp.exp_env(secs(0.25), 0.08)
    return finish(layer((t, 1.0), (crunch, 0.6), (whomp, 0.7)))


def player_death(rng):
    t = thump(rng, 140, 30, 0.9, click=0.6, decay=0.3)
    boom = dsp.lowpass(dsp.noise(secs(1.2), rng, "brown"), 220) * dsp.exp_env(secs(1.2), 0.35)
    n = secs(1.4)
    toll = dsp.bell(196.0, 1.4, rng, bright=0.8, decay=0.8) * 0.5
    x = layer((t, 1.0), (boom, 0.8), (toll, 0.6))
    return finish(room(rng, x, mix=0.35, dur=2.0, decay=1.6), fout=0.2)


def pound_start(rng):
    return finish(whoosh(rng, 0.3, 1800, 500, q=1.3, peak=0.5))


def pound_land(rng):
    t = thump(rng, 95, 28, 0.6, click=0.8, decay=0.18)
    boom = dsp.lowpass(dsp.noise(secs(0.7), rng, "brown"), 300) * dsp.exp_env(secs(0.7), 0.2)
    debris = scatter(rng, 0.6, 9, lambda: burst(rng, 0.03, fc=rng.uniform(1500, 3500), kind="bp", q=2, tau=0.008), 0.4, 0.04)
    return finish(room(rng, layer((t, 1.0), (boom, 0.9), (debris, 0.4)), mix=0.2, dur=1.0, decay=0.8))


def drink(rng):
    clink = metal(rng, 2100, 0.2, ratios=(1.0, 2.7, 4.1), decay=0.08) * 0.3
    out = dsp.mix_at(np.zeros(secs(0.55)), clink, 0)
    for k in range(3):
        b = chirp(rng, rng.uniform(260, 340), rng.uniform(600, 800), 0.06, harm=0.1)
        b = dsp.lowpass(b, 1800) * 0.8
        out = dsp.mix_at(out, b, secs(0.08 + 0.11 * k + rng.uniform(0, 0.02)))
    gulp = thump(rng, 180, 90, 0.12, click=0.0) * 0.6
    out = dsp.mix_at(out, gulp, secs(0.42))
    return finish(out)


def flask_empty(rng):
    return finish(metal(rng, 1700, 0.25, ratios=(1.0, 1.71, 2.9), decay=0.06, bright=0.6))


# ---------------------------------------------------------------- weapons


def swing_light(rng):
    w = whoosh(rng, 0.22, rng.uniform(800, 1000), rng.uniform(2400, 3000), q=1.5, peak=0.4)
    ring = metal(rng, rng.uniform(3000, 3600), 0.25, decay=0.08, bright=0.5) * 0.08
    return finish(layer((w, 1.0), (ring, 1.0)))


def swing_heavy(rng):
    w = whoosh(rng, 0.42, rng.uniform(250, 320), rng.uniform(800, 1000), q=1.2, peak=0.5)
    n = secs(0.42)
    vw = dsp.sine(dsp.sweep(95, 60, n), n) * dsp.adsr(n, 0.12, 0.1, 0.6, 0.2)
    return finish(layer((w, 1.0), (vw, 0.25)))


def swing_thrust(rng):
    return finish(whoosh(rng, 0.16, rng.uniform(1400, 1700), rng.uniform(3300, 3900), q=1.8, peak=0.25))


def swing_flail(rng):
    w = whoosh(rng, 0.36, 450, 1400, q=1.3, peak=0.45)
    links = scatter(rng, 0.36, 7, lambda: metal(rng, rng.uniform(2500, 4200), 0.06, decay=0.02) * 0.4, 0.25)
    return finish(layer((w, 1.0), (links, 0.7)))


def hit_flesh(rng):
    t = thump(rng, rng.uniform(150, 190), 55, 0.14, click=0.4)
    smack = burst(rng, 0.09, fc=rng.uniform(2200, 3000), tau=0.02)
    squish = dsp.tv_filter(dsp.noise(secs(0.16), rng), lambda s: 900 - 3000 * s, kind="bp", q=2.0) * dsp.exp_env(secs(0.16), 0.05)
    return finish(dsp.distort(layer((t, 1.0), (smack, 0.7), (squish, 0.5)), 1.5))


def hit_crit(rng):
    base = hit_flesh(rng)
    ring = metal(rng, rng.uniform(2000, 2400), 0.5, decay=0.22, bright=0.75)
    crack = burst(rng, 0.04, fc=5000, kind="hp", tau=0.01)
    return finish(room(rng, layer((base, 1.0), (ring, 0.45), (crack, 0.5)), mix=0.15))


def hit_heavy(rng):
    t = thump(rng, 120, 35, 0.3, click=0.6, decay=0.1)
    bones = scatter(rng, 0.25, 5, lambda: burst(rng, 0.025, fc=rng.uniform(1800, 3200), kind="bp", q=3, tau=0.006), 0.08)
    smack = burst(rng, 0.12, fc=1800, tau=0.03)
    return finish(dsp.distort(layer((t, 1.0), (bones, 0.5), (smack, 0.7)), 2.0))


def hit_bell(rng):
    t = thump(rng, 130, 45, 0.2, click=0.4)
    b = dsp.bell(rng.uniform(330, 370), 1.6, rng, bright=0.85, decay=0.7)
    return finish(room(rng, layer((t, 0.8), (b, 0.55)), mix=0.2, dur=1.2, decay=1.0))


def kill(rng):
    t = thump(rng, 160, 40, 0.25, click=0.5)
    sq = dsp.tv_filter(dsp.noise(secs(0.35), rng), lambda s: 1500 * (0.25 ** (s / 0.35)), kind="bp", q=1.5)
    sq *= dsp.exp_env(len(sq), 0.12)
    splat = scatter(rng, 0.35, 5, lambda: burst(rng, 0.04, fc=rng.uniform(600, 1400), kind="bp", q=1.5, tau=0.012), 0.2, 0.03)
    return finish(dsp.distort(layer((t, 1.0), (sq, 0.6), (splat, 0.6)), 1.6))


def bow_shoot(rng):
    tw = dsp.karplus(rng.uniform(105, 120), 0.35, rng, decay=0.994, bright=0.35)
    tw = dsp.lowpass(dsp.highpass(tw, 90), 2500)
    w = whoosh(rng, 0.18, 1000, 2400, q=1.5, peak=0.2)
    return finish(layer((tw, 1.0), (w, 0.45)))


def crossbow_shoot(rng):
    click = metal(rng, 2400, 0.06, ratios=(1.0, 1.8, 2.9), decay=0.015) * 0.5
    tw = dsp.lowpass(dsp.highpass(dsp.karplus(78, 0.4, rng, decay=0.993, bright=0.4), 60), 2200)
    thunk = thump(rng, 200, 90, 0.1, click=0.5)
    w = whoosh(rng, 0.2, 900, 2200, q=1.6, peak=0.2)
    return finish(layer((click, 1.0), (tw, 1.0), (thunk, 0.8), (w, 0.4)))


def arrow_hit(rng):
    knock = dsp.modal([620, 1340, 2150], [1.0, 0.5, 0.25], [0.05, 0.03, 0.02], 0.12, rng=rng)
    return finish(layer((knock, 0.8), (burst(rng, 0.05, fc=2500, tau=0.01), 0.6)))


def grenade_throw(rng):
    clink = metal(rng, 2300, 0.15, ratios=(1.0, 2.6, 4.3), decay=0.05) * 0.4
    return finish(layer((whoosh(rng, 0.2, 700, 1800, q=1.3, peak=0.3), 1.0), (clink, 1.0)))


def explode_fire(rng):
    n = secs(1.1)
    boom = dsp.lowpass(dsp.noise(n, rng, "brown"), 500) * dsp.exp_env(n, 0.3)
    low = thump(rng, 75, 30, 0.8, click=0.8, decay=0.25)
    crackle = scatter(rng, 1.0, 40, lambda: burst(rng, 0.01, fc=rng.uniform(2000, 6000), kind="bp", q=4, tau=0.003), 0.8, 0.05)
    crackle *= dsp.ramp(len(crackle), 1.0, 0.0, 0.7)
    roar = dsp.tv_filter(dsp.noise(n, rng, "pink"), lambda s: 1800 * (0.3 ** s), kind="lp") * dsp.adsr(n, 0.01, 0.2, 0.4, 0.6)
    return finish(room(rng, dsp.distort(layer((boom, 1.0), (low, 1.0), (crackle, 0.35), (roar, 0.5)), 1.4), mix=0.2, dur=1.2, decay=1.0))


def explode_ice(rng):
    shards = scatter(rng, 0.8, 26, lambda: metal(rng, rng.uniform(2500, 7500), 0.25, ratios=(1.0, 1.37, 2.11), decay=0.06, bright=0.6) * rng.uniform(0.2, 0.6), 0.45)
    thud = thump(rng, 110, 45, 0.3, click=0.6)
    w = whoosh(rng, 0.5, 4000, 1500, q=0.9, peak=0.1, color="white")
    return finish(room(rng, layer((shards, 1.0), (thud, 0.8), (w, 0.5)), mix=0.25, dur=1.0, decay=0.9))


def harpoon_throw(rng):
    w = whoosh(rng, 0.25, 900, 2600, q=1.5, peak=0.25)
    n = secs(0.3)
    buzz = dsp.additive_saw(120, n, max_h=30) * (0.6 + 0.4 * dsp.sine(30, n)) * dsp.exp_env(n, 0.12)
    return finish(layer((w, 0.9), (dsp.highpass(buzz, 300), 0.35)))


def zap(rng):
    n = secs(0.4)
    gate = (rng.random(n // 220 + 1) < 0.55).repeat(220)[:n].astype(float)
    crack = dsp.highpass(dsp.noise(n, rng), 1500) * gate * dsp.exp_env(n, 0.12)
    saw = dsp.distort(dsp.additive_saw(dsp.sweep(900, 180, n), n, max_h=25), 2.5) * dsp.exp_env(n, 0.1)
    return finish(dsp.lowpass(layer((crack, 1.0), (saw, 0.5)), 7000))


def shield_raise(rng):
    return finish(layer((thump(rng, 220, 140, 0.07, click=0.4), 0.8), (burst(rng, 0.1, fc=1200, kind="bp", q=0.8, tau=0.03), 0.5)))


def shield_block(rng):
    wood = thump(rng, 200, 110, 0.12, click=0.6)
    clank = metal(rng, rng.uniform(900, 1100), 0.3, decay=0.08, bright=0.7)
    return finish(layer((wood, 1.0), (clank, 0.5)))


def shield_parry(rng):
    clang = metal(rng, rng.uniform(1300, 1500), 1.0, ratios=(1.0, 1.59, 2.71, 3.82, 5.13), decay=0.45, bright=0.8)
    w = whoosh(rng, 0.2, 2500, 5000, q=1.3, peak=0.1, color="white")
    t = thump(rng, 220, 90, 0.1, click=0.8)
    return finish(room(rng, layer((clang, 1.0), (w, 0.4), (t, 0.5)), mix=0.25, dur=1.2, decay=1.0))


def equip(rng):
    scrape = dsp.tv_filter(dsp.noise(secs(0.25), rng), lambda s: 2500 + 9000 * s, kind="bp", q=3.0) * dsp.adsr(secs(0.25), 0.03, 0.1, 0.6, 0.1)
    ting = metal(rng, 2600, 0.5, decay=0.18, bright=0.7)
    out = dsp.mix_at(scrape * 0.6, ting * 0.6, secs(0.18))
    return finish(out)


# ---------------------------------------------------------------- enemies


def enemy_alert(rng):
    a = metal(rng, 2650, 0.35, ratios=(1.0, 1.5, 2.0, 3.0), decay=0.12, bright=0.55)
    b = metal(rng, 3970, 0.3, ratios=(1.0, 2.0), decay=0.08, bright=0.5)
    x = dsp.mix_at(a, b * 0.7, secs(0.045))
    return finish(room(rng, x, mix=0.12, dur=0.5, decay=0.4))


def enemy_notice(rng):
    return finish(chirp(rng, 480, 720, 0.12, harm=0.15) * 0.8)


def enemy_attack(rng):
    w = whoosh(rng, 0.32, rng.uniform(380, 450), rng.uniform(1100, 1400), q=1.3, peak=0.45)
    grunt = dsp.lowpass(dsp.additive_saw(dsp.sweep(110, 80, secs(0.2)), secs(0.2), max_h=20), 600) * dsp.adsr(secs(0.2), 0.02, 0.05, 0.6, 0.1)
    return finish(layer((w, 1.0), (grunt, 0.3)))


def enemy_death(rng):
    k = kill(rng)
    collapse = scatter(rng, 0.7, 6, lambda: burst(rng, 0.04, fc=rng.uniform(500, 1500), kind="bp", q=2, tau=0.012), 0.35, 0.25)
    thud = dsp.mix_at(np.zeros(secs(0.7)), thump(rng, 120, 50, 0.15, click=0.3), secs(0.4))
    return finish(layer((k, 1.0), (collapse, 0.5), (thud, 0.6)))


def cast(rng):
    n = secs(0.7)
    f = dsp.sweep(300, 900, n)
    x = sum(dsp.sine(f * d, n) for d in (1.0, 1.007, 2.003)) / 3
    x *= (0.7 + 0.3 * dsp.sine(14, n)) * dsp.adsr(n, 0.3, 0.1, 0.8, 0.25)
    shimmer = dsp.highpass(dsp.noise(n, rng), 5000) * dsp.adsr(n, 0.4, 0.1, 0.6, 0.2) * 0.3
    return finish(room(rng, layer((x, 1.0), (shimmer, 1.0)), mix=0.3))


def orb_fire(rng):
    n = secs(0.3)
    x = dsp.sine(dsp.sweep(500, 220, n), n) * dsp.exp_env(n, 0.1)
    return finish(layer((x, 1.0), (whoosh(rng, 0.25, 800, 400, q=1.0, peak=0.15), 0.6)))


def leap(rng):
    return finish(layer((whoosh(rng, 0.3, 400, 1600, q=1.2, peak=0.3), 1.0), (thump(rng, 150, 80, 0.08, click=0.4), 0.6)))


def fuse(rng):
    n = secs(0.75)
    hiss = dsp.highpass(dsp.noise(n, rng), 3500) * dsp.ramp(n, 0.1, 1.0, 1.5)
    bub = scatter(rng, 0.75, 10, lambda: chirp(rng, rng.uniform(300, 500), rng.uniform(700, 1100), 0.03) * 0.4, 0.7)
    return finish(dsp.lowpass(layer((hiss, 0.5), (bub, 0.8)), 7000), fout=0.005)


def vermin_explode(rng):
    wet = dsp.lowpass(dsp.noise(secs(0.5), rng), 1200) * dsp.exp_env(secs(0.5), 0.12)
    splash = scatter(rng, 0.5, 8, lambda: burst(rng, 0.05, fc=rng.uniform(700, 1800), kind="bp", q=1.5, tau=0.015), 0.25)
    return finish(dsp.distort(layer((wet, 1.0), (splash, 0.7), (thump(rng, 130, 40, 0.3, click=0.6), 0.9)), 1.6))


def flyer_dive(rng):
    n = secs(0.45)
    f = dsp.sweep(1900, 900, n)
    squeal = dsp.sine(f + 60 * dsp.sine(37, n), n) * dsp.adsr(n, 0.02, 0.1, 0.5, 0.2) * 0.4
    return finish(layer((whoosh(rng, 0.45, 2200, 800, q=1.4, peak=0.3), 1.0), (squeal, 0.5)))


def turret_fire(rng):
    n = secs(0.6)
    vib = 1 + 0.01 * dsp.sine(7, n)
    x = (dsp.sine(660 * vib, n) + 0.6 * dsp.sine(990 * vib, n) + 0.3 * dsp.sine(1320 * vib, n)) * dsp.adsr(n, 0.01, 0.1, 0.6, 0.35)
    return finish(room(rng, x, mix=0.3, dur=1.0, decay=0.9))


def turret_charge(rng):
    n = secs(0.5)
    x = dsp.sine(dsp.sweep(200, 660, n), n) * dsp.ramp(n, 0.0, 1.0, 1.2)
    return finish(x * (0.8 + 0.2 * dsp.sine(20, n)), fout=0.005)


def reflect(rng):
    ding = metal(rng, 1900, 0.5, ratios=(1.0, 2.0, 3.0, 4.2), decay=0.2, bright=0.6)
    return finish(layer((ding, 1.0), (whoosh(rng, 0.2, 3000, 1200, q=1.2, peak=0.2), 0.4)))


# ---------------------------------------------------------------- bosses


def boss_slam(rng):
    t = thump(rng, 80, 24, 1.0, click=1.0, decay=0.3)
    boom = dsp.lowpass(dsp.noise(secs(1.3), rng, "brown"), 250) * dsp.exp_env(secs(1.3), 0.4)
    debris = scatter(rng, 1.2, 18, lambda: burst(rng, 0.03, fc=rng.uniform(1200, 3500), kind="bp", q=2, tau=0.008), 0.9, 0.05)
    return finish(room(rng, dsp.distort(layer((t, 1.0), (boom, 1.0), (debris, 0.35)), 1.3), mix=0.25, dur=1.5, decay=1.2))


def boss_sweep(rng):
    w = whoosh(rng, 0.65, 180, 700, q=1.0, peak=0.55)
    n = secs(0.65)
    vw = dsp.sine(dsp.sweep(70, 45, n), n) * dsp.adsr(n, 0.25, 0.1, 0.6, 0.2)
    return finish(layer((w, 1.0), (vw, 0.4)))


def boss_shockwave(rng):
    n = secs(0.9)
    r = dsp.lowpass(dsp.noise(n, rng, "brown"), 350) * dsp.adsr(n, 0.05, 0.2, 0.7, 0.5)
    grind = dsp.bandpass(dsp.noise(n, rng), 700, 1.5) * dsp.adsr(n, 0.05, 0.2, 0.5, 0.5) * 0.4
    return finish(layer((r, 1.0), (grind, 1.0)))


def boss_death(rng):
    t = thump(rng, 70, 20, 1.6, click=1.0, decay=0.5)
    boom = dsp.lowpass(dsp.noise(secs(2.4), rng, "brown"), 300) * dsp.exp_env(secs(2.4), 0.7)
    toll = dsp.bell(130.8, 3.0, rng, bright=0.85, decay=1.4)
    x = layer((t, 1.0), (boom, 0.9), (toll, 0.7))
    return finish(room(rng, x, mix=0.35, dur=3.0, decay=2.5), fout=0.4)


def boss_intro(rng):
    n = secs(1.8)
    cluster = sum(dsp.additive_saw(f, n, max_h=25) for f in (55.0, 82.4, 110.0, 116.5))
    cluster = dsp.tv_filter(cluster, lambda s: 200 + 1400 * min(1.0, s / 1.5), kind="lp") * dsp.adsr(n, 1.2, 0.1, 0.9, 0.45)
    hit = dsp.mix_at(np.zeros(n), thump(rng, 70, 25, 0.8, click=1.0, decay=0.25), secs(1.35))
    return finish(room(rng, layer((cluster, 0.6), (hit, 1.0)), mix=0.3, dur=2.0, decay=1.8), fout=0.3)


def rewind(rng):
    chord = sum(dsp.bell(f, 1.3, rng, bright=0.7, decay=0.6) for f in (523.3, 659.3, 784.0)) / 3
    ticks = scatter(rng, 1.3, 10, lambda: metal(rng, 3200, 0.04, ratios=(1.0, 2.2), decay=0.01), 1.1)
    w = whoosh(rng, 1.3, 400, 3000, q=1.0, peak=0.9)
    x = layer((chord, 0.8), (ticks, 0.6), (w, 0.6))[::-1]
    return finish(room(rng, x, mix=0.3), fin=0.05)


def star(rng):
    out = np.zeros(secs(0.35))
    for k, f in enumerate((1568.0, 2093.0, 2637.0)):
        out = dsp.mix_at(out, dsp.sine(f, secs(0.15)) * dsp.exp_env(secs(0.15), 0.04), secs(0.04 * k))
    return finish(room(rng, out, mix=0.25))


def pillar(rng):
    n = secs(0.9)
    rise = dsp.tv_filter(dsp.noise(n, rng), lambda s: 300 * (10 ** min(1.0, s / 0.8)), kind="bp", q=2.0) * dsp.adsr(n, 0.4, 0.1, 0.8, 0.3)
    tone = dsp.sine(dsp.sweep(220, 880, n), n) * dsp.adsr(n, 0.5, 0.1, 0.7, 0.3) * 0.4
    return finish(room(rng, layer((rise, 1.0), (tone, 1.0)), mix=0.25))


def summon(rng):
    n = secs(0.7)
    buzz = sum(dsp.additive_saw(f * (1 + 0.03 * dsp.sine(rng.uniform(15, 25), n)), n, max_h=15) for f in (180, 230, 290))
    return finish(dsp.bandpass(buzz, 900, 1.2) * dsp.adsr(n, 0.15, 0.1, 0.7, 0.3))


# ---------------------------------------------------------------- world


def coin(rng):
    base = rng.uniform(2600, 3300)
    a = metal(rng, base, 0.25, ratios=(1.0, 2.31, 3.92), decay=0.07, bright=0.5)
    b = metal(rng, base * 1.33, 0.25, ratios=(1.0, 2.31, 3.92), decay=0.09, bright=0.5)
    return finish(dsp.mix_at(a, b * 0.8, secs(0.05)))


def cell(rng):
    n = secs(0.45)
    f = dsp.sweep(880, 1320, n)
    x = (dsp.sine(f, n) + 0.3 * dsp.sine(f * 2, n)) * dsp.adsr(n, 0.005, 0.08, 0.4, 0.3)
    sh = dsp.highpass(dsp.noise(n, rng), 6000) * dsp.exp_env(n, 0.06) * 0.2
    return finish(room(rng, layer((x, 0.7), (sh, 1.0)), mix=0.3))


def pickup_item(rng):
    return finish(layer((equip(rng), 1.0), (thump(rng, 160, 80, 0.12, click=0.3), 0.5)))


def fanfare(rng, notes=(523.3, 659.3, 784.0, 1046.5), gap=0.08, tail=1.2):
    out = np.zeros(secs(tail + gap * len(notes)))
    for k, f in enumerate(notes):
        out = dsp.mix_at(out, dsp.bell(f, tail, rng, bright=0.6, decay=0.5) * (0.8 + 0.1 * k), secs(gap * k))
    return out


def scroll(rng):
    sh = dsp.highpass(dsp.noise(secs(1.0), rng), 5000) * dsp.adsr(secs(1.0), 0.2, 0.2, 0.3, 0.5) * 0.25
    return finish(room(rng, layer((fanfare(rng), 1.0), (sh, 1.0)), mix=0.3, dur=1.5, decay=1.2))


def paper(rng):
    return scatter(rng, 0.35, 6, lambda: burst(rng, 0.04, fc=rng.uniform(2500, 5000), kind="bp", q=1.0, tau=0.012), 0.25)


def blueprint(rng):
    chime = fanfare(rng, notes=(784.0, 1174.7), gap=0.1, tail=0.9)
    return finish(room(rng, layer((paper(rng), 0.8), (chime, 0.7)), mix=0.25))


def creak(rng, dur=0.5, f0=320, f1=480):
    n = secs(dur)
    f = dsp.sweep(f0, f1, n, curve="lin") * (1 + 0.04 * rng.standard_normal(n).cumsum() / np.sqrt(n))
    pulses = dsp.additive_saw(f / 8, n, max_h=40)
    return dsp.bandpass(pulses, (f0 + f1) / 2, 2.0) * dsp.adsr(n, 0.05, 0.1, 0.8, 0.15)


def chest_open(rng):
    out = creak(rng, 0.45, 300, 520) * 0.6
    out = dsp.mix_at(out, thump(rng, 140, 70, 0.15, click=0.6), secs(0.42))
    coins = scatter(rng, 0.6, 7, lambda: coin(rng) * 0.25, 0.4)
    out = dsp.mix_at(out, coins, secs(0.45))
    return finish(out)


def door_open(rng):
    out = creak(rng, 0.9, 160, 240) * 0.6
    rumble = dsp.lowpass(dsp.noise(secs(1.1), rng, "brown"), 200) * dsp.adsr(secs(1.1), 0.2, 0.2, 0.6, 0.4)
    out = layer((out, 1.0), (rumble, 0.6))
    out = dsp.mix_at(out, thump(rng, 100, 45, 0.3, click=0.8), secs(0.95))
    return finish(room(rng, out, mix=0.25, dur=1.2, decay=1.0))


def warp(rng):
    n = secs(1.1)
    w = whoosh(rng, 1.1, 300, 4000, q=1.0, peak=0.7, curve=1.5)
    f = dsp.sweep(220, 1760, n)
    swirl = (dsp.sine(f, n) + 0.5 * dsp.sine(f * 1.5, n)) * dsp.adsr(n, 0.6, 0.1, 0.6, 0.35) * (0.7 + 0.3 * dsp.sine(9, n))
    return finish(room(rng, layer((w, 1.0), (swirl, 0.35)), mix=0.35, dur=1.5, decay=1.2), fout=0.15)


def activate(rng):
    chord = sum(dsp.bell(f, 1.6, rng, bright=0.7, decay=0.8) for f in (392.0, 587.3, 784.0)) / 3
    n = secs(1.6)
    hum = (dsp.sine(98, n) + 0.5 * dsp.sine(196, n)) * dsp.adsr(n, 0.3, 0.2, 0.5, 0.8) * 0.4
    return finish(room(rng, layer((chord, 1.0), (hum, 1.0)), mix=0.35, dur=1.8, decay=1.5), fout=0.2)


def fountain(rng):
    splash = dsp.bandpass(dsp.noise(secs(0.8), rng), 1800, 0.8) * dsp.adsr(secs(0.8), 0.02, 0.2, 0.4, 0.4)
    glugs = scatter(rng, 0.8, 6, lambda: chirp(rng, rng.uniform(300, 450), rng.uniform(700, 900), 0.05) * 0.5, 0.5, 0.1)
    chime = dsp.mix_at(np.zeros(secs(1.4)), fanfare(rng, notes=(659.3, 987.8), gap=0.1, tail=0.9) * 0.5, secs(0.4))
    return finish(room(rng, layer((splash, 0.6), (glugs, 0.7), (chime, 1.0)), mix=0.3))


def lore(rng):
    chime = dsp.bell(587.3, 1.4, rng, bright=0.6, decay=0.7)
    return finish(room(rng, layer((paper(rng), 0.9), (chime, 0.5)), mix=0.3, dur=1.4, decay=1.2))


def buy(rng):
    coins = scatter(rng, 0.6, 9, lambda: coin(rng) * rng.uniform(0.3, 0.7), 0.35)
    return finish(layer((coins, 1.0), (thump(rng, 180, 100, 0.1, click=0.3), 0.4)))


def npc_talk(rng):
    out = np.zeros(secs(0.45))
    for k in range(5):
        f = rng.uniform(260, 420)
        n = secs(0.06)
        blip = dsp.peaks(dsp.additive_saw(f, n, max_h=30), [(700, 3, 1.0), (1200, 4, 0.6)]) * dsp.adsr(n, 0.005, 0.02, 0.6, 0.02)
        out = dsp.mix_at(out, blip, secs(0.075 * k))
    return finish(out)


def spikes(rng):
    stab = metal(rng, 1800, 0.2, decay=0.05, bright=0.6)
    return finish(layer((stab, 0.7), (hit_flesh(rng), 0.8)))


def vent(rng):
    n = secs(0.9)
    roar = dsp.bandpass(dsp.noise(n, rng, "pink"), 600, 0.7) * dsp.adsr(n, 0.08, 0.2, 0.7, 0.4)
    crackle = scatter(rng, 0.9, 20, lambda: burst(rng, 0.008, fc=rng.uniform(2500, 6000), kind="bp", q=4, tau=0.002), 0.8)
    return finish(layer((roar, 1.0), (crackle, 0.3)))


def sorrow(rng):
    n = secs(1.0)
    x = sum(dsp.sine(f * (1 + 0.01 * dsp.sine(rng.uniform(3, 6), n)), n) for f in (220, 261.6, 311.1)) / 3
    return finish(room(rng, x * dsp.adsr(n, 0.3, 0.2, 0.6, 0.4), mix=0.4, dur=1.5, decay=1.3))


def area_enter(rng):
    n = secs(2.4)
    pad = sum(dsp.additive_saw(f, n, max_h=20) for f in (73.4, 110.0, 146.8, 174.6))
    pad = dsp.lowpass(pad, 900) * dsp.adsr(n, 0.8, 0.3, 0.6, 1.1)
    b = dsp.mix_at(np.zeros(n), dsp.bell(293.7, 2.0, rng, bright=0.6, decay=0.8), secs(0.15))
    return finish(room(rng, layer((pad, 0.35), (b, 0.6)), mix=0.35, dur=2.0, decay=1.8), fout=0.4)


def gate(rng):
    t = thump(rng, 70, 28, 0.8, click=1.0, decay=0.25)
    clank = metal(rng, 520, 0.8, decay=0.2, bright=0.6)
    rumble = dsp.lowpass(dsp.noise(secs(1.2), rng, "brown"), 200) * dsp.exp_env(secs(1.2), 0.4)
    return finish(room(rng, layer((t, 1.0), (clank, 0.5), (rumble, 0.8)), mix=0.3, dur=1.6, decay=1.4))


def achievement(rng):
    return finish(room(rng, fanfare(rng, notes=(783.99, 987.77, 1174.66, 1567.98), gap=0.09, tail=1.0), mix=0.3, dur=1.4, decay=1.2))


# ---------------------------------------------------------------- UI


def ui_move(rng):
    n = secs(0.035)
    return finish(layer((dsp.sine(1250, n) * dsp.exp_env(n, 0.008), 1.0), (burst(rng, 0.01, fc=4000, kind="hp", tau=0.002), 0.3)))


def two_notes(rng, f0, f1, wave="sine"):
    out = np.zeros(secs(0.2))
    for k, f in enumerate((f0, f1)):
        n = secs(0.09)
        x = dsp.sine(f, n) + 0.25 * dsp.sine(2 * f, n)
        out = dsp.mix_at(out, x * dsp.adsr(n, 0.003, 0.03, 0.5, 0.05), secs(0.065 * k))
    return finish(out)


def ui_confirm(rng):
    return two_notes(rng, 660, 990)


def ui_back(rng):
    return two_notes(rng, 660, 440)


def ui_error(rng):
    n = secs(0.16)
    return finish(dsp.lowpass(dsp.additive_square(140, n), 900) * dsp.adsr(n, 0.005, 0.03, 0.8, 0.05), max_rms_db=-16.0)


def ui_open(rng):
    return finish(dsp.lowpass(layer((whoosh(rng, 0.18, 1000, 2400, q=1.0, peak=0.6, color="white"), 0.6), (ui_move(rng), 0.7)), 5000))


def ui_close(rng):
    return finish(dsp.lowpass(whoosh(rng, 0.16, 2400, 1000, q=1.0, peak=0.3, color="white"), 4500))


# ---------------------------------------------------------------- registry

def M(volume=1.0, pitch=(0.95, 1.05), cooldown=0.03, voices=4, spatial=True):
    return dict(volume=volume, pitch=list(pitch), cooldown=cooldown, voices=voices, spatial=spatial)


REGISTRY = {
    "player.step": (step, 5, M(0.28, (0.9, 1.1), 0.08, 2)),
    "player.jump": (jump, 2, M(0.45, cooldown=0.05, voices=2)),
    "player.double_jump": (double_jump, 2, M(0.6, cooldown=0.05, voices=2)),
    "player.land": (land, 2, M(0.5, (0.9, 1.05), 0.08, 2)),
    "player.roll": (roll, 2, M(0.55, voices=2)),
    "player.mantle": (mantle, 2, M(0.45, voices=2)),
    "player.hurt": (hurt, 3, M(0.8, voices=2)),
    "player.death": (player_death, 1, M(0.9, (1.0, 1.0), voices=1, spatial=False)),
    "player.pound_start": (pound_start, 1, M(0.55, voices=1)),
    "player.pound_land": (pound_land, 2, M(0.85, voices=1)),
    "player.drink": (drink, 2, M(0.7, voices=1)),
    "player.flask_empty": (flask_empty, 1, M(0.5, voices=1)),
    "swing.light": (swing_light, 3, M(0.55, (0.92, 1.08), 0.02, 3)),
    "swing.heavy": (swing_heavy, 2, M(0.65, (0.92, 1.05), 0.02, 3)),
    "swing.thrust": (swing_thrust, 3, M(0.5, (0.92, 1.1), 0.02, 3)),
    "swing.flail": (swing_flail, 2, M(0.6, (0.92, 1.06), 0.02, 3)),
    "hit.flesh": (hit_flesh, 4, M(0.75, (0.9, 1.1), 0.025, 5)),
    "hit.crit": (hit_crit, 2, M(0.9, (0.95, 1.05), 0.03, 3)),
    "hit.heavy": (hit_heavy, 2, M(0.9, (0.92, 1.05), 0.03, 3)),
    "hit.bell": (hit_bell, 2, M(0.8, (0.94, 1.06), 0.05, 3)),
    "enemy.kill": (kill, 3, M(0.75, (0.9, 1.1), 0.03, 4)),
    "bow.shoot": (bow_shoot, 2, M(0.6)),
    "crossbow.shoot": (crossbow_shoot, 2, M(0.75)),
    "arrow.hit": (arrow_hit, 2, M(0.55)),
    "grenade.throw": (grenade_throw, 1, M(0.55)),
    "explode.fire": (explode_fire, 2, M(0.95, (0.92, 1.05), 0.05, 3)),
    "explode.ice": (explode_ice, 2, M(0.85, (0.95, 1.05), 0.05, 3)),
    "harpoon.throw": (harpoon_throw, 1, M(0.65)),
    "lightning.zap": (zap, 3, M(0.6, (0.9, 1.1), 0.04, 3)),
    "shield.raise": (shield_raise, 1, M(0.45, voices=1)),
    "shield.block": (shield_block, 2, M(0.75, voices=2)),
    "shield.parry": (shield_parry, 2, M(0.9, voices=2)),
    "weapon.equip": (equip, 1, M(0.6, voices=1, spatial=False)),
    "enemy.alert": (enemy_alert, 1, M(0.55, (0.98, 1.04), 0.06, 3)),
    "enemy.notice": (enemy_notice, 1, M(0.35, (0.95, 1.1), 0.1, 2)),
    "enemy.attack": (enemy_attack, 2, M(0.55, (0.9, 1.08), 0.04, 4)),
    "enemy.death": (enemy_death, 2, M(0.7, (0.9, 1.1), 0.04, 4)),
    "enemy.cast": (cast, 1, M(0.5, voices=3)),
    "enemy.orb": (orb_fire, 1, M(0.5, voices=3)),
    "enemy.leap": (leap, 1, M(0.55, voices=3)),
    "vermin.fuse": (fuse, 1, M(0.5, voices=3)),
    "vermin.explode": (vermin_explode, 2, M(0.85, voices=3)),
    "flyer.dive": (flyer_dive, 2, M(0.55, voices=3)),
    "turret.charge": (turret_charge, 1, M(0.4, voices=3)),
    "turret.fire": (turret_fire, 1, M(0.5, voices=3)),
    "projectile.reflect": (reflect, 1, M(0.7, voices=2)),
    "boss.slam": (boss_slam, 2, M(1.0, (0.95, 1.03), 0.1, 2)),
    "boss.sweep": (boss_sweep, 2, M(0.85, voices=2)),
    "boss.shockwave": (boss_shockwave, 1, M(0.75, voices=2)),
    "boss.death": (boss_death, 1, M(1.0, (1.0, 1.0), voices=1, spatial=False)),
    "boss.intro": (boss_intro, 1, M(0.9, (1.0, 1.0), voices=1, spatial=False)),
    "tk.rewind": (rewind, 1, M(0.85, (1.0, 1.0), voices=1)),
    "tk.star": (star, 2, M(0.45, (0.95, 1.1), 0.05, 4)),
    "tk.pillar": (pillar, 1, M(0.6, voices=4)),
    "tk.summon": (summon, 1, M(0.6, voices=2)),
    "pickup.gold": (coin, 3, M(0.4, (0.95, 1.12), 0.03, 4, spatial=False)),
    "pickup.cell": (cell, 2, M(0.5, (0.95, 1.1), 0.03, 4, spatial=False)),
    "pickup.item": (pickup_item, 1, M(0.7, voices=1, spatial=False)),
    "pickup.scroll": (scroll, 1, M(0.75, (1.0, 1.0), voices=1, spatial=False)),
    "pickup.blueprint": (blueprint, 1, M(0.75, (1.0, 1.0), voices=1, spatial=False)),
    "chest.open": (chest_open, 1, M(0.75, voices=1)),
    "door.open": (door_open, 1, M(0.8, voices=1)),
    "teleport.warp": (warp, 1, M(0.75, (1.0, 1.0), voices=1, spatial=False)),
    "teleport.activate": (activate, 1, M(0.6, (1.0, 1.0), voices=1)),
    "fountain.use": (fountain, 1, M(0.7, voices=1)),
    "lore.read": (lore, 1, M(0.7, voices=1, spatial=False)),
    "shop.buy": (buy, 1, M(0.7, voices=1, spatial=False)),
    "npc.talk": (npc_talk, 2, M(0.45, voices=1)),
    "hazard.spikes": (spikes, 1, M(0.7, voices=2)),
    "hazard.vent": (vent, 1, M(0.5, voices=3)),
    "hazard.sorrow": (sorrow, 1, M(0.4, voices=2)),
    "area.enter": (area_enter, 1, M(0.6, (1.0, 1.0), voices=1, spatial=False)),
    "boss.gate": (gate, 1, M(0.9, (1.0, 1.0), voices=1, spatial=False)),
    "achievement": (achievement, 1, M(0.7, (1.0, 1.0), voices=1, spatial=False)),
    "ui.move": (ui_move, 1, M(0.3, (0.98, 1.02), 0.02, 2, spatial=False)),
    "ui.confirm": (ui_confirm, 1, M(0.4, (1.0, 1.0), 0.03, 2, spatial=False)),
    "ui.back": (ui_back, 1, M(0.4, (1.0, 1.0), 0.03, 2, spatial=False)),
    "ui.error": (ui_error, 1, M(0.4, (1.0, 1.0), 0.08, 1, spatial=False)),
    "ui.open": (ui_open, 1, M(0.4, (1.0, 1.0), 0.05, 1, spatial=False)),
    "ui.close": (ui_close, 1, M(0.35, (1.0, 1.0), 0.05, 1, spatial=False)),
}
