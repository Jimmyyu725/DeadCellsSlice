"""Find one-way traps in generated levels: cells the player can reach from the
start but from which the exit door can no longer be reached.
Usage: python3 Tools/Rooms/find_traps.py [files...]   (default: Tools/_out/levels/*.txt)
"""
import glob
import os
import sys
from collections import defaultdict, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_rooms import Grid  # noqa: E402


def analyse(path):
    rows = open(path).read().rstrip('\n').split('\n')
    g = Grid(rows)
    marks = {}
    for (x, y), ch in list(g.c.items()):
        if ch in "PTDKMp":
            marks.setdefault(ch, []).append((x, y))
            g.c[(x, y)] = '.'
    start = marks['P'][0]
    # Forward reachability with the edge list kept for reversing.
    seen = {start}
    q = deque([start])
    rev = defaultdict(list)
    while q:
        p = q.popleft()
        for n in g.neighbours(*p):
            rev[n].append(p)
            if n not in seen:
                seen.add(n)
                q.append(n)
    exits = marks.get('D', [])
    goal = set()
    for (x, y) in exits:
        for dx in (-1, 0, 1):
            if (x + dx, y) in seen:
                goal.add((x + dx, y))
    back = set(goal)
    q = deque(goal)
    while q:
        p = q.popleft()
        for n in rev[p]:
            if n not in back:
                back.add(n)
                q.append(n)
    traps = seen - back
    return traps, rows


def main():
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "_out", "levels", "*.txt")))
    bad = 0
    for f in files:
        traps, rows = analyse(f)
        if traps:
            bad += 1
            xs = sorted(traps)
            room_file = f.replace('.txt', '.rooms')
            rooms = [l.split() for l in open(room_file)] if os.path.exists(room_file) else []
            where = set()
            for (x, y) in xs:
                for t, k, rx, ry, w, h in rooms:
                    rx, ry, w, h = map(int, (rx, ry, w, h))
                    if rx <= x < rx + w and ry <= y < ry + h:
                        where.add(t)
            print(f"{os.path.basename(f)}: {len(traps)} trap cells, e.g. {xs[0]} in {sorted(where) or ['(shaft)']}")
    print(f"{len(files)} levels, {bad} with traps")


if __name__ == "__main__":
    main()
