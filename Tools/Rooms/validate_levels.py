"""Whole-level reachability for generated levels dumped by DCBatch.DumpLevels.

Starts from the player start (P), or the leftmost floor for passages, and
checks the exit door (D), every teleporter (T), shop pedestal (p), merchant (M)
and collector (K) are reachable with the room validator's movement model.
Usage: python3 Tools/Rooms/validate_levels.py [Tools/_out/levels]
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_rooms import Grid  # noqa: E402


def check(path):
    rows = open(path).read().rstrip('\n').split('\n')
    g = Grid(rows)
    marks = {}
    for (x, y), ch in g.c.items():
        if ch in "PTDKMp":
            marks.setdefault(ch, []).append((x, y))
            g.c[(x, y)] = '.'
    if 'P' not in marks:
        return ["no player start"]
    start = marks['P'][0]
    seen = g.reach(start)
    problems = []
    for ch, cells in marks.items():
        for (x, y) in cells:
            if not any((x + dx, y) in seen for dx in (-1, 0, 1)):
                problems.append(f"{ch} at {x},{y} unreachable")
    return problems


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "_out", "levels")
    files = sorted(glob.glob(os.path.join(folder, "*.txt")))
    bad = 0
    for f in files:
        probs = check(f)
        if probs:
            bad += 1
            print(os.path.basename(f), "; ".join(probs[:4]))
    print(f"{len(files)} levels, {bad} with unreachable targets")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
