"""Generate every sound effect, music loop and ambience bed for the game.

Run with Blender's bundled Python (it ships numpy):
  /Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13 Tools/Audio/make_audio.py
Options: --sfx / --music / --ambience to build one group, --only=id1,id2 to
build a subset (prefix match), --preview to also write a listening reel.

Writes Assets/_Project/Audio/{Sfx,Music,Ambience}/*.wav and
Assets/_Project/Audio/audio_manifest.json plus audio_bank.json (the same as
lists, read by the Unity sound bank builder: per-event clip list, volume, pitch range, cooldown, voices,
spatial).
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dsp  # noqa: E402
import music  # noqa: E402
import music_dc  # noqa: E402
import sfx  # noqa: E402
import sfx_dc  # noqa: E402

sfx_dc.apply()

ROOT = HERE.parent.parent
OUT = ROOT / "Assets" / "_Project" / "Audio"
MANIFEST = OUT / "audio_manifest.json"
MUSIC_VOLUME = {"music.boss": 0.9, "music.death": 0.8}


def main():
    args = sys.argv[1:]
    groups = [g for g in ("--sfx", "--music", "--ambience") if g in args] or ["--sfx", "--music", "--ambience"]
    only = next((a.split("=", 1)[1].split(",") for a in args if a.startswith("--only=")), None)

    def wanted(i):
        return only is None or any(i.startswith(o) for o in only)

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    manifest.setdefault("sfx", {})
    manifest.setdefault("music", {})
    manifest.setdefault("ambience", {})
    t0 = time.time()

    if "--sfx" in groups:
        d = OUT / "Sfx"
        d.mkdir(parents=True, exist_ok=True)
        for sid, (fn, variants, meta) in sfx.REGISTRY.items():
            if not wanted(sid):
                continue
            files = []
            for k in range(variants):
                rng = np.random.default_rng(sum(map(ord, sid)) * 131 + k)
                x = fn(rng)
                path = d / f"{sid}__{k + 1}.wav"
                dsp.write_wav(path, x, dsp.SR)
                files.append(str(path.relative_to(ROOT)))
            manifest["sfx"][sid] = dict(meta, files=files)
            print(f"[sfx] {sid:22s} x{variants}  {len(x) / dsp.SR:.2f}s")

    if "--music" in groups:
        d = OUT / "Music"
        d.mkdir(parents=True, exist_ok=True)
        for mid, fn in music_dc.TRACKS.items():
            if not wanted(mid):
                continue
            ts = time.time()
            x = fn()
            path = d / f"{mid}.wav"
            dsp.write_wav(path, x, music.MSR)
            manifest["music"][mid] = dict(file=str(path.relative_to(ROOT)), volume=MUSIC_VOLUME.get(mid, 0.75),
                                          loop=mid != "music.death", seconds=round(len(x) / music.MSR, 2))
            print(f"[music] {mid:18s} {len(x) / music.MSR:5.1f}s  built in {time.time() - ts:.1f}s")

    if "--ambience" in groups:
        d = OUT / "Ambience"
        d.mkdir(parents=True, exist_ok=True)
        for aid, fn in music.AMBIENCE.items():
            if not wanted(aid):
                continue
            x = fn()
            path = d / f"{aid}.wav"
            dsp.write_wav(path, x, music.MSR)
            manifest["ambience"][aid] = dict(file=str(path.relative_to(ROOT)), volume=0.6, loop=True,
                                             seconds=round(len(x) / music.MSR, 2))
            print(f"[amb] {aid:16s} {len(x) / music.MSR:5.1f}s")

    if "--preview" in args:
        reel = []
        for sid, entry in manifest["sfx"].items():
            if wanted(sid):
                import wave
                with wave.open(str(ROOT / entry["files"][0])) as w:
                    reel.append(np.frombuffer(w.readframes(w.getnframes()), "<i2") / 32767.0)
                    reel.append(np.zeros(dsp.secs(0.35)))
        if reel:
            dsp.write_wav(HERE.parent / "_out" / "sfx_reel.wav", np.concatenate(reel))

    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True))
    # Same data as lists, the shape Unity's JsonUtility can read.
    bank = {group: [dict(id=k, **v) for k, v in sorted(manifest[group].items())] for group in ("sfx", "music", "ambience")}
    (OUT / "audio_bank.json").write_text(json.dumps(bank, indent=1))
    print(f"[audio] manifest {MANIFEST.relative_to(ROOT)}  done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
