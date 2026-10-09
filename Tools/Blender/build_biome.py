"""Biome environment kit generator (Tools/BIOMES.md).

Headless only:
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      -P Tools/Blender/build_biome.py -- --biome Promenade
Options after "--":
  --biome <Id>|all   Promenade, Ossuary, StiltVillage, ClockLung (or all)
  --fast             1024/512 atlases (iteration only)
  --build-only       geometry + Workbench previews, no bake/export
  --verify           re-import the exported FBX files and check bounds/pivots/sockets
  --gpu              bake on Metal instead of the CPU (faster, but can drop chunks when VRAM is short)
"""

import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import biome_kit as bk  # noqa: E402

BIOMES = {
    "Promenade": "biomes.promenade",
    "Ossuary": "biomes.ossuary",
    "StiltVillage": "biomes.stilt_village",
    "ClockLung": "biomes.clock_lung",
}


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ids = []
    for i, a in enumerate(args):
        if a == "--biome" and i + 1 < len(args):
            ids = list(BIOMES) if args[i + 1] == "all" else args[i + 1].split(",")
        elif a.startswith("--biome="):
            v = a.split("=", 1)[1]
            ids = list(BIOMES) if v == "all" else v.split(",")
    if not ids:
        raise SystemExit("usage: build_biome.py -- --biome <Id>|all [--fast] [--build-only] [--verify]")
    bk.BAKE_GPU = "--gpu" in args
    ok = True
    for bid in ids:
        mod = importlib.import_module(BIOMES[bid])
        kit = mod.make_kit()
        if "--verify" in args:
            ok &= bk.verify(kit)
        else:
            bk.run(kit, fast="--fast" in args, build_only="--build-only" in args)
    if not ok:
        print("[biome] VERIFY FAILED")


if __name__ == "__main__":
    main()
