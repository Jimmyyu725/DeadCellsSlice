"""Validate Dead Cells Slice room templates (Assets/_Project/Resources/Rooms/*.txt).

Checks per room: equal row widths, 3-cell doors on the outer columns with a
floor below, 3-wide side openings, markers standing on floors, and an
approximate platformer reachability test (walk, fall, jump <= 3 up / 4 across,
ledge mantle, drop through one-way platforms) from the entry to the exit, every
side opening and every interactive marker.

Usage: python3 Tools/Rooms/validate_rooms.py [--verbose]
"""
import glob
import os
import sys
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOM_DIR = os.path.join(ROOT, "Assets/_Project/Resources/Rooms")

SOLID = set("#")
ONEWAY = set("=")
HAZARD = set("~X")
MARKERS_ON_FLOOR = set("PeEoTCMpLFKDBW$sG")
INTERACT = set("TCMpLFKDWs$")


def parse(path):
    rooms, cur, rows = [], None, []

    def flush():
        nonlocal cur, rows
        if cur is not None and rows:
            cur["rows"] = rows
            rooms.append(cur)
        cur, rows = None, []

    for line in open(path, encoding="utf-8").read().split("\n"):
        line = line.rstrip("\r \t")
        if line.startswith("@"):
            flush()
            cur = {"file": os.path.basename(path), "meta": {}}
            for part in line[1:].split():
                if "=" in part:
                    k, v = part.split("=", 1)
                    cur["meta"][k] = v
                else:
                    cur["meta"][part] = True
            continue
        if line.startswith("#!") or line.startswith("//"):
            continue
        if not line:
            flush()
            continue
        if cur is not None:
            rows.append(line)
    flush()
    return rooms


class Grid:
    def __init__(self, rows):
        self.h = len(rows)
        self.w = max(len(r) for r in rows)
        self.c = {}
        for r, row in enumerate(rows):
            y = self.h - 1 - r
            for x in range(self.w):
                self.c[(x, y)] = row[x] if x < len(row) else "#"

    def at(self, x, y):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return "#"
        return self.c[(x, y)]

    def solid(self, x, y):
        ch = self.at(x, y)
        return ch in SOLID or (ch in "^v" and False)

    def blocks(self, x, y):
        """Blocks movement (walls)."""
        ch = self.at(x, y)
        if ch in "^" or ch in "v":
            return False
        return ch in SOLID

    def floor(self, x, y):
        ch = self.at(x, y)
        return ch in SOLID or ch in ONEWAY or ch in "^v"

    def free(self, x, y):
        return not self.blocks(x, y) and self.at(x, y) not in HAZARD

    def stand(self, x, y):
        return self.free(x, y) and self.free(x, y + 1) and self.floor(x, y - 1) and self.at(x, y - 1) not in HAZARD

    def clear_column(self, x, y0, y1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            if self.blocks(x, y):
                return False
        return True

    def neighbours(self, x, y):
        out = []
        # walk / step off ledges
        for dx in (-1, 1):
            nx = x + dx
            if self.blocks(nx, y) or self.blocks(nx, y + 1):
                continue
            if self.stand(nx, y):
                out.append((nx, y))
            else:
                fy = y
                while fy > 0 and not self.floor(nx, fy - 1) and not self.blocks(nx, fy - 1):
                    fy -= 1
                if self.stand(nx, fy):
                    out.append((nx, fy))
        # drop through one-way
        if self.at(x, y - 1) in ONEWAY or self.at(x, y - 1) in "v":
            fy = y - 1
            while fy > 0 and not (self.floor(x, fy - 1) and fy - 1 != y - 1) and not self.blocks(x, fy - 1):
                fy -= 1
            if self.stand(x, fy) and fy < y:
                out.append((x, fy))
        # jumps
        for dy in range(-6, 4):
            for dx in range(-5, 6):
                if dx == 0 and dy <= 0:
                    continue
                if dy >= 2 and abs(dx) > 4:
                    continue
                if dy == 3 and abs(dx) > 3:
                    continue
                nx, ny = x + dx, y + dy
                if not self.stand(nx, ny):
                    continue
                # Body is 2 cells tall: feet row + head row.
                apex = max(y, ny)
                if not self.clear_column(x, y, apex + 1):
                    continue
                ok = True
                step = 1 if dx > 0 else -1
                for cx in range(x, nx + step, step) if dx != 0 else []:
                    if self.blocks(cx, apex) or self.blocks(cx, apex + 1):
                        ok = False
                        break
                if ok and self.clear_column(nx, ny, apex + 1):
                    out.append((nx, ny))
        # mantle: jump up beside a wall and climb its lip (up to 4 above feet)
        for dx in (-1, 1):
            for dy in (3, 4):
                nx, ny = x + dx, y + dy
                if self.stand(nx, ny) and self.blocks(nx, ny - 1) and self.clear_column(x, y, y + dy + 1):
                    out.append((nx, ny))
        return out

    def reach(self, start):
        seen = {start}
        q = deque([start])
        while q:
            p = q.popleft()
            for n in self.neighbours(*p):
                if n not in seen:
                    seen.add(n)
                    q.append(n)
        return seen


def groups(g, row, code):
    out, cur = [], []
    for x in range(g.w):
        if g.at(x, row) == code:
            cur.append(x)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def check(room):
    errs = []
    rows = room["rows"]
    name = room["meta"].get("name", "?")
    widths = {len(r) for r in rows}
    if len(widths) != 1:
        errs.append(f"row widths differ: {sorted(widths)}")
        for i, r in enumerate(rows):
            if len(r) != max(widths):
                errs.append(f"  row {i} len {len(r)}: {r}")
        return errs
    g = Grid(rows)
    left = [y for y in range(g.h) if g.at(0, y) == "<"]
    right = [y for y in range(g.h) if g.at(g.w - 1, y) == ">"]
    tags = set(room["meta"].get("tags", "").split(","))
    for side, ys, x in (("left", left, 0), ("right", right, g.w - 1)):
        if ys:
            if len(ys) != 3 or max(ys) - min(ys) != 2:
                errs.append(f"{side} door must be 3 consecutive cells, got rows {ys}")
            elif not g.floor(x, min(ys) - 1):
                errs.append(f"{side} door has no floor below")
    ups = groups(g, g.h - 1, "^")
    downs = groups(g, 0, "v")
    for grp in ups + downs:
        if len(grp) != 3:
            errs.append(f"opening width {len(grp)} != 3 at x={grp}")
    for (x, y), ch in g.c.items():
        if ch in "<>" and x not in (0, g.w - 1):
            errs.append(f"door char {ch} inside room at {x},{y}")
        if ch == "^" and y != g.h - 1:
            errs.append(f"'^' not on top row at {x},{y}")
        if ch == "v" and y != 0:
            errs.append(f"'v' not on bottom row at {x},{y}")
        if ch in MARKERS_ON_FLOOR and not g.floor(x, y - 1):
            errs.append(f"marker {ch} at {x},{y} not on a floor")
    if errs:
        return errs

    # Reachability.
    if left:
        start = (0, min(left))
    elif "P" in "".join(rows):
        start = next(p for p, ch in g.c.items() if ch == "P")
    elif downs:
        start = (downs[0][1], 1)
    elif ups:
        # enter from the top opening: fall down from it
        x = ups[0][1]
        y = g.h - 2
        while y > 0 and not g.floor(x, y - 1):
            y -= 1
        start = (x, y)
    else:
        return ["no entry (door, P or opening)"]
    if not g.stand(*start):
        errs.append(f"entry {start} is not standable")
        return errs
    seen = g.reach(start)
    if right:
        tgt = (g.w - 1, min(right))
        if tgt not in seen:
            errs.append(f"exit door {tgt} unreachable from {start}")
    for grp in ups:
        # The opening row becomes a one-way platform: standing on it puts the feet at
        # row h, so a foothold must exist within 3 rows below (y >= h - 3).
        ok = any((x, y) in seen for x in range(grp[0] - 1, grp[-1] + 2) for y in range(g.h - 3, g.h - 1)
                 if g.clear_column(x, y, g.h - 2))
        if not ok:
            errs.append(f"top opening {grp} unreachable")
    for grp in downs:
        if not any((x, 1) in seen for x in grp):
            errs.append(f"bottom opening {grp} unreachable")
    for (x, y), ch in g.c.items():
        if ch in INTERACT and not any((x + d, y) in seen for d in (-1, 0, 1)):
            errs.append(f"marker {ch} at {x},{y} unreachable")
    # No traps: from every reachable cell the way on (exit door, or the opening
    # back out of a side room) must still be reachable.
    goal = set()
    if right:
        goal.add((g.w - 1, min(right)))
    for (x, y), ch in g.c.items():
        if ch == "D":
            goal.update((x + d, y) for d in (-1, 0, 1))
    if not right and not any(ch == "D" for ch in g.c.values()):
        for grp in ups:
            goal.update((x, y) for x in range(grp[0] - 1, grp[-1] + 2) for y in range(g.h - 3, g.h - 1)
                        if g.clear_column(x, y, g.h - 2))
        for grp in downs:
            goal.update((x, 1) for x in grp)
    goal &= seen
    traps = trap_cells(g, start, goal) if goal else set()
    if traps:
        errs.append(f"{len(traps)} trap cells, e.g. {sorted(traps)[:4]}")
    return errs


def trap_cells(g, start, goal):
    from collections import defaultdict
    rev = defaultdict(list)
    seen = {start}
    q = deque([start])
    while q:
        p = q.popleft()
        for n in g.neighbours(*p):
            rev[n].append(p)
            if n not in seen:
                seen.add(n)
                q.append(n)
    back = set(goal)
    q = deque(goal)
    while q:
        p = q.popleft()
        for n in rev[p]:
            if n not in back:
                back.add(n)
                q.append(n)
    return seen - back


def show(room):
    g = Grid(room["rows"])
    left = [y for y in range(g.h) if g.at(0, y) == "<"]
    if left:
        start = (0, min(left))
    else:
        start = next((p for p, ch in g.c.items() if ch == "P"), None)
        if start is None:
            downs = groups(g, 0, "v")
            ups = groups(g, g.h - 1, "^")
            if downs:
                start = (downs[0][1], 1)
            else:
                x = ups[0][1]
                y = g.h - 2
                while y > 0 and not g.floor(x, y - 1):
                    y -= 1
                start = (x, y)
    seen = g.reach(start)
    for r in range(g.h):
        y = g.h - 1 - r
        print("".join("o" if (x, y) in seen and g.at(x, y) == "." else g.at(x, y) for x in range(g.w)) + f"  y={y}")


def main():
    if "--show" in sys.argv:
        target = sys.argv[sys.argv.index("--show") + 1]
        for f in sorted(glob.glob(os.path.join(ROOM_DIR, "*.txt"))):
            for room in parse(f):
                if room["meta"].get("name") == target:
                    show(room)
        return 0
    verbose = "--verbose" in sys.argv
    files = sorted(glob.glob(os.path.join(ROOM_DIR, "*.txt")))
    total, bad = 0, 0
    tag_count = {}
    names = set()
    for f in files:
        for room in parse(f):
            total += 1
            name = room["meta"].get("name", "?")
            if name in names:
                print(f"DUPLICATE name {name}")
                bad += 1
            names.add(name)
            for t in room["meta"].get("tags", "").split(","):
                for b in room["meta"].get("biomes", "all").split(","):
                    tag_count[(t, b)] = tag_count.get((t, b), 0) + 1
            errs = check(room)
            if not errs and not room["meta"].get("nomirror"):
                # The generator also uses mirror images (doors swap sides).
                mirrored = dict(room)
                mirrored["rows"] = ["".join({"<": ">", ">": "<"}.get(ch, ch) for ch in reversed(r)) for r in room["rows"]]
                errs = ["(mirrored) " + e for e in check(mirrored)]
            if errs:
                bad += 1
                print(f"[{room['file']}] {name}:")
                for e in errs:
                    print("   ", e)
            elif verbose:
                print(f"ok {name} {len(room['rows'][0])}x{len(room['rows'])}")
    print(f"{total} rooms, {bad} with problems")
    if verbose:
        for k in sorted(tag_count):
            print(k, tag_count[k])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
