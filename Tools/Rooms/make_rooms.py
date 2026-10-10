"""Author the room templates by coordinates and write Resources/Rooms/*.txt.

Vertical grid (2-thick floor): floor top y=1, stand y=2, platforms at
y=4/7/10/13 (stand 5/8/11/14), side opening '^' at y=17 for H=18.
Single-floor rooms with a bottom opening use floor y=0, stand y=1.
Run, then: python3 Tools/Rooms/validate_rooms.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "Assets/_Project/Resources/Rooms")


class Room:
    def __init__(self, name, w, h, tags, biomes="all", weight=1.0, nomirror=False):
        self.name, self.w, self.h = name, w, h
        self.tags, self.biomes, self.weight, self.nomirror = tags, biomes, weight, nomirror
        self.g = [["." for _ in range(w)] for _ in range(h)]
        self.box(0, 0, w - 1, h - 1, "#", hollow=True)

    def set(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch

    def box(self, x0, y0, x1, y1, ch="#", hollow=False):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                if hollow and x0 < x < x1 and y0 < y < y1:
                    continue
                self.set(x, y, ch)
        return self

    def floor(self, top, x0=0, x1=None):
        return self.box(x0, 0, self.w - 1 if x1 is None else x1, top, "#")

    def air(self, x0, y0, x1, y1):
        return self.box(x0, y0, x1, y1, ".")

    def plat(self, x0, x1, y):
        return self.box(x0, y, x1, y, "=")

    def door_l(self, y):
        for k in range(3):
            self.set(0, y + k, "<")
        return self

    def door_r(self, y):
        for k in range(3):
            self.set(self.w - 1, y + k, ">")
        return self

    def up(self, x):
        for k in range(3):
            self.set(x + k, self.h - 1, "^")
        return self

    def down(self, x):
        for k in range(3):
            self.set(x + k, 0, "v")
        return self

    def put(self, x, y, ch):
        self.set(x, y, ch)
        return self

    def puts(self, y, items):
        for x, ch in items:
            self.set(x, y, ch)
        return self

    def text(self):
        head = f"@name={self.name} tags={self.tags} biomes={self.biomes} weight={self.weight}"
        if self.nomirror:
            head += " nomirror"
        rows = ["".join(r) for r in reversed(self.g)]
        return head + "\n" + "\n".join(rows) + "\n"


ROOMS = {}


def add(file, room):
    ROOMS.setdefault(file, []).append(room)
    return room


# =========================================================== main: combat
r = add("rooms_main", Room("cmb_hall_a", 40, 17, "combat", weight=1.2))
r.floor(1).door_l(2).door_r(2).up(17)
r.box(12, 2, 13, 4).box(25, 2, 26, 4)
r.plat(3, 7, 4).plat(31, 36, 4)
r.plat(6, 10, 7).plat(28, 33, 7)
r.plat(11, 15, 10).plat(23, 27, 10)
r.plat(15, 21, 13)
r.puts(2, [(6, "e"), (19, "e"), (32, "e")]).put(19, 9, "f")
r.puts(9, [(3, "t"), (36, "t")])

r = add("rooms_main", Room("cmb_hall_b", 46, 15, "combat", weight=1.2))
r.floor(0).door_l(1).door_r(1).down(25)
r.box(17, 1, 22, 3)
r.plat(5, 9, 3).plat(34, 38, 3)
r.plat(14, 18, 6).plat(21, 25, 6)
r.plat(8, 12, 9).plat(30, 35, 9)
r.puts(1, [(6, "e"), (31, "e"), (41, "e")]).put(19, 4, "e").put(20, 9, "f")
r.puts(11, [(6, "t"), (22, "t"), (38, "t")])

r = add("rooms_main", Room("cmb_pillars", 44, 15, "combat"))
r.floor(1).door_l(2).door_r(2)
for px in (8, 20, 32):
    r.box(px, 2, px + 2, 4)
    r.plat(px - 3, px - 1, 7).plat(px + 3, px + 5, 7)
    r.box(px, 8, px + 2, 9)
r.plat(13, 17, 10).plat(25, 29, 10)
r.puts(2, [(4, "e"), (15, "e"), (27, "e"), (39, "e")]).put(21, 10, "e").put(15, 6, "f")
r.puts(12, [(6, "t"), (21, "t"), (36, "t")])

r = add("rooms_main", Room("cmb_pit", 44, 17, "combat"))
r.floor(1).door_l(5).door_r(5).up(12)
r.floor(4, 0, 12).floor(4, 28, 43)
r.air(13, 2, 27, 4)
r.box(13, 2, 27, 2, "X")
r.plat(15, 18, 7).plat(23, 26, 7)
r.plat(9, 13, 10).plat(29, 33, 10)
r.plat(11, 15, 13)
r.puts(5, [(5, "e"), (33, "e"), (39, "e")]).put(20, 11, "f")
r.puts(9, [(4, "t"), (38, "t")])
r.put(16, 8, "$")

r = add("rooms_main", Room("cmb_tiers", 42, 17, "combat"))
r.floor(1).door_l(2).door_r(2).up(23)
r.box(12, 2, 31, 4).box(16, 5, 27, 7)
r.plat(7, 11, 4).plat(32, 36, 4)
r.plat(20, 24, 10).plat(20, 24, 13)
r.puts(2, [(5, "e"), (37, "e")]).puts(5, [(14, "e"), (29, "e")]).put(21, 8, "e")
r.puts(11, [(8, "t"), (34, "t")])

r = add("rooms_main", Room("cmb_tiers_b", 48, 16, "combat"))
r.floor(0).door_l(1).door_r(1).down(37)
r.box(4, 1, 34, 3).box(10, 4, 28, 6)
r.plat(35, 39, 3)
r.plat(14, 18, 9).plat(22, 26, 9)
r.puts(1, [(2, "e"), (42, "e")]).puts(4, [(6, "e"), (31, "e")]).put(19, 7, "e").put(40, 8, "f")
r.puts(11, [(8, "t"), (24, "t"), (40, "t")])

r = add("rooms_main", Room("cmb_arena", 54, 19, "combat", weight=0.9))
r.floor(1).door_l(2).door_r(2).up(25)
r.box(8, 2, 10, 4).box(44, 2, 46, 4)
r.plat(13, 22, 4).plat(32, 41, 4)
r.plat(4, 8, 7).plat(46, 50, 7)
r.plat(11, 16, 10).plat(38, 43, 10)
r.plat(18, 24, 13).plat(30, 36, 13).plat(24, 30, 15)
r.puts(2, [(4, "e"), (18, "e"), (27, "e"), (36, "e"), (50, "e")]).puts(14, [(20, "f"), (34, "f")])
r.puts(11, [(6, "t"), (27, "t"), (48, "t")])

r = add("rooms_main", Room("cmb_liquid", 46, 16, "combat", weight=0.9))
r.floor(3).door_l(4).door_r(4).up(37)
r.air(9, 2, 35, 3).box(9, 2, 35, 3, "~")
r.plat(13, 17, 6).plat(27, 31, 6)
r.plat(19, 25, 9).plat(9, 11, 5).plat(34, 36, 5).plat(29, 33, 9)
r.plat(33, 38, 12)
r.puts(4, [(5, "e"), (40, "e")]).put(22, 10, "e").put(20, 13, "f")
r.puts(10, [(5, "t"), (40, "t")])

r = add("rooms_main", Room("cmb_bridge", 46, 14, "combat"))
r.floor(0).door_l(6).door_r(6).down(17)
r.box(0, 1, 6, 5).box(27, 1, 33, 5).box(39, 1, 45, 5)
r.plat(7, 26, 5).plat(34, 38, 5)
r.plat(14, 18, 8)
r.puts(1, [(10, "e"), (21, "e"), (36, "e")]).puts(6, [(3, "e"), (15, "e"), (30, "e"), (42, "e")]).put(24, 10, "f")
r.puts(10, [(8, "t"), (30, "t")])
r.plat(8, 11, 3).plat(22, 25, 3).plat(34, 37, 3)

r = add("rooms_main", Room("cmb_ledges", 45, 17, "combat"))
r.floor(1).door_l(2).door_r(9).up(16)
r.box(13, 2, 17, 5).box(22, 2, 27, 8).box(39, 2, 44, 8)
r.plat(5, 9, 4).plat(8, 12, 7)
r.plat(28, 32, 4).plat(32, 36, 7)
r.plat(11, 15, 10).plat(14, 19, 13)
r.puts(2, [(4, "e"), (20, "e"), (33, "e")]).put(15, 6, "e").put(24, 9, "e").put(41, 9, "e").put(34, 12, "f")
r.puts(11, [(4, "t"), (30, "t")])

r = add("rooms_main", Room("cmb_columns", 50, 16, "combat"))
r.floor(1).door_l(2).door_r(2)
r.box(10, 2, 11, 3).box(24, 2, 25, 3).box(38, 2, 39, 3)
r.plat(14, 21, 5).plat(28, 35, 5)
r.plat(6, 10, 8).plat(21, 28, 8).plat(39, 43, 8)
r.plat(13, 17, 11).plat(32, 36, 11)
r.puts(2, [(5, "e"), (17, "e"), (31, "e"), (44, "e")]).put(24, 9, "e").put(16, 12, "f").put(34, 12, "f")
r.puts(12, [(5, "t"), (25, "t"), (45, "t")])
r.put(25, 4, "$")

# ============================================================== climb / drop
r = add("rooms_main", Room("climb_a", 32, 20, "climb"))
r.floor(1).door_l(2).door_r(14)
r.box(26, 2, 31, 13)
r.plat(4, 9, 4).plat(10, 15, 7).plat(16, 21, 10).plat(21, 25, 13)
r.plat(3, 7, 10).plat(8, 12, 13)
r.puts(2, [(6, "e"), (17, "e")]).put(28, 14, "e").put(12, 8, "e").put(18, 15, "f")
r.puts(9, [(3, "t"), (24, "t")])

r = add("rooms_main", Room("climb_b", 38, 22, "climb"))
r.floor(1).door_l(2).door_r(17).up(5)
r.box(0, 13, 8, 16).box(30, 2, 37, 16)
r.plat(10, 15, 4).plat(16, 21, 7).plat(22, 28, 10).plat(16, 21, 13).plat(9, 14, 16)
r.plat(24, 29, 16)
r.plat(4, 8, 19)
r.put(5, 17, "e").puts(2, [(5, "e"), (20, "e")]).put(33, 17, "e").put(25, 11, "e").put(18, 18, "f")
r.puts(9, [(5, "t"), (27, "t")])

r = add("rooms_main", Room("drop_a", 34, 20, "drop"))
r.floor(1).door_l(14).door_r(2)
r.box(0, 2, 7, 13)
r.plat(8, 12, 13).plat(14, 19, 10).plat(20, 25, 7).plat(25, 30, 4)
r.plat(10, 14, 7)
r.put(3, 14, "e").puts(2, [(14, "e"), (28, "e")]).put(17, 11, "e").put(20, 15, "f")
r.puts(9, [(26, "t"), (5, "t")])
r.put(11, 8, "$")

r = add("rooms_main", Room("drop_b", 40, 21, "drop"))
r.floor(0).door_l(15).door_r(1).down(14)
r.box(0, 1, 10, 14).box(33, 1, 39, 3)
r.plat(11, 15, 13).plat(16, 21, 10).plat(22, 27, 7).plat(28, 32, 4)
r.plat(18, 22, 3)
r.put(4, 15, "e").put(19, 11, "e").puts(1, [(17, "e"), (26, "e")]).put(36, 4, "e").put(25, 14, "f")
r.puts(9, [(14, "t"), (34, "t")])

r = add("rooms_main", Room("climb_c", 36, 20, "climb", weight=0.8))
r.floor(1).door_l(2).door_r(11)
r.box(28, 2, 35, 10).box(14, 2, 16, 6)
r.plat(5, 9, 4).plat(9, 13, 7).plat(17, 21, 7).plat(20, 25, 10).plat(21, 25, 4)
r.plat(6, 10, 10).plat(10, 14, 13)
r.puts(2, [(5, "e"), (22, "e")]).put(15, 7, "e").put(31, 11, "e").put(13, 15, "f")
r.puts(9, [(3, "t"), (25, "t")])

# ================================================================ corridors
r = add("rooms_main", Room("corridor_a", 36, 11, "corridor"))
r.floor(1).door_l(2).door_r(2)
r.box(0, 7, 35, 10).air(1, 7, 34, 7)
r.box(14, 2, 15, 2).box(22, 2, 23, 2)
r.puts(2, [(9, "e"), (28, "e")]).put(19, 2, "$")
r.puts(6, [(6, "t"), (18, "t"), (30, "t")])

r = add("rooms_main", Room("corridor_b", 40, 11, "corridor"))
r.floor(1).door_l(2).door_r(2).up(18)
r.box(12, 2, 27, 2, "X").box(11, 0, 28, 1)
r.plat(11, 16, 4).plat(23, 28, 4).plat(17, 22, 7)
r.puts(2, [(6, "e"), (33, "e")]).put(19, 8, "e")
r.puts(7, [(5, "t"), (34, "t")])

r = add("rooms_main", Room("corridor_c", 34, 12, "corridor", weight=0.8))
r.floor(1).door_l(2).door_r(2)
r.box(9, 2, 12, 3).box(21, 2, 24, 3)
r.plat(13, 20, 5)
r.puts(2, [(5, "e"), (17, "e"), (29, "e")]).put(16, 6, "C")
r.puts(8, [(4, "t"), (16, "t"), (29, "t")])

# ===================================================================== exits
r = add("rooms_main", Room("exit_a", 30, 14, "exit", nomirror=True))
r.floor(1).door_l(2)
r.box(18, 2, 29, 3)
r.plat(13, 17, 4)
r.puts(2, [(6, "e")]).put(24, 4, "D").put(20, 4, "T")
r.puts(8, [(21, "t"), (27, "t")])

r = add("rooms_main", Room("exit_b", 34, 16, "exit", nomirror=True))
r.floor(1).door_l(2)
r.plat(5, 9, 4).plat(10, 14, 7)
r.box(15, 2, 33, 7)
r.puts(2, [(4, "e"), (12, "e")]).put(20, 8, "T").put(27, 8, "D").put(12, 8, "e")
r.puts(11, [(18, "t"), (30, "t")])


# ============================================================ side: shop
r = add("rooms_side", Room("shop_up", 24, 10, "shop", nomirror=True))
r.floor(0).down(10)
r.puts(1, [(3, "M"), (7, "p"), (16, "p"), (20, "p")])
r.puts(5, [(6, "t"), (17, "t")])
r.box(1, 8, 22, 8).air(2, 8, 21, 8)

r = add("rooms_side", Room("shop_down", 24, 11, "shop", nomirror=True))
r.floor(1).up(10)
r.plat(9, 15, 4).plat(9, 15, 7)
r.puts(2, [(3, "M"), (7, "p"), (17, "p"), (20, "p")])
r.puts(6, [(4, "t"), (19, "t")])

# ======================================================== side: treasure
r = add("rooms_side", Room("treasure_up", 22, 11, "treasure"))
r.floor(0).down(4)
r.box(10, 1, 20, 2).plat(7, 9, 3)
r.put(16, 3, "C").put(12, 3, "e").put(2, 1, "$")
r.puts(6, [(5, "t"), (17, "t")])

r = add("rooms_side", Room("treasure_down", 24, 11, "treasure"))
r.floor(1).up(3)
r.plat(2, 7, 4).plat(2, 7, 7)
r.box(9, 2, 22, 2, "X").box(9, 0, 22, 1)
r.plat(10, 13, 6).plat(17, 20, 6)
r.box(21, 2, 22, 4).put(21, 5, "C")
r.put(11, 7, "s")
r.puts(8, [(15, "t")])

r = add("rooms_side", Room("treasure_vault", 26, 12, "treasure", weight=0.8))
r.floor(0).down(11)
r.box(1, 1, 8, 3).box(17, 1, 24, 3)
r.plat(9, 16, 4)
r.put(4, 4, "C").put(21, 4, "s").put(12, 1, "e").put(19, 4, "e")
r.puts(8, [(4, "t"), (21, "t")])

# ============================================================ side: lore
r = add("rooms_side", Room("lore_up", 18, 10, "lore"))
r.floor(0).down(3)
r.box(10, 1, 16, 1)
r.put(13, 2, "L").put(8, 1, "e")
r.puts(6, [(10, "t"), (16, "t")])

r = add("rooms_side", Room("lore_down", 18, 11, "lore"))
r.floor(1).up(2)
r.plat(1, 5, 4).plat(1, 5, 7)
r.put(13, 2, "L").put(9, 2, "e")
r.puts(6, [(12, "t")])

# =========================================================== side: elite
r = add("rooms_side", Room("elite_up", 30, 12, "elite"))
r.floor(0).down(2)
r.box(26, 1, 28, 1)
r.put(17, 1, "E").put(27, 2, "C")
r.plat(10, 14, 4).plat(19, 23, 4)
r.puts(7, [(8, "t"), (22, "t")])

r = add("rooms_side", Room("elite_down", 30, 11, "elite"))
r.floor(1).up(2)
r.plat(1, 5, 4).plat(1, 5, 7)
r.put(17, 2, "E").put(26, 2, "C")
r.plat(10, 14, 4).plat(19, 23, 4)
r.puts(8, [(10, "t"), (24, "t")])


# =================================================================== starts
r = add("rooms_special", Room("oub_start", 40, 16, "start", "Oubliette", nomirror=True))
r.floor(1).door_r(2)
r.box(1, 2, 9, 2, "~")
r.box(1, 10, 6, 14).box(7, 12, 9, 14)
r.put(13, 2, "P").put(20, 2, "W").put(24, 2, "W").put(30, 2, "T")
r.plat(15, 19, 4).plat(21, 25, 7)
r.puts(9, [(17, "t"), (33, "t")])

r = add("rooms_special", Room("start_gate", 32, 14, "start", "Promenade,Ossuary,StiltVillage,ClockLung", nomirror=True))
r.floor(1).door_r(2)
r.box(1, 2, 5, 4)
r.put(8, 2, "P").put(15, 2, "T")
r.plat(19, 23, 5)
r.puts(8, [(10, "t"), (26, "t")])

# ================================================================== passage
r = add("rooms_special", Room("passage_a", 46, 14, "passage", "Passage", nomirror=True))
r.floor(1)
r.box(36, 2, 45, 3)
r.put(4, 2, "P").put(13, 2, "F").put(22, 2, "K").put(32, 2, "T").put(41, 4, "D")
r.plat(16, 20, 5)
r.puts(8, [(8, "t"), (18, "t"), (28, "t"), (40, "t")])

# ===================================================================== menu
r = add("rooms_special", Room("menu_hall", 40, 14, "menu", "all", nomirror=True))
r.floor(1)
r.box(1, 2, 6, 3).box(33, 2, 38, 4)
r.put(24, 2, "P")
r.puts(7, [(10, "t"), (20, "t"), (30, "t")])
r.plat(9, 13, 5).plat(27, 31, 6)

# ==================================================================== bosses
r = add("rooms_special", Room("boss_guardian", 64, 20, "boss_guardian", "Ossuary", nomirror=True))
r.floor(1).door_l(2)
r.box(1, 9, 8, 19)
r.box(9, 2, 10, 2).put(11, 2, "G")
r.plat(16, 21, 6).plat(42, 47, 6)
r.plat(26, 37, 9)
r.box(52, 2, 63, 3)
r.put(40, 2, "B").put(57, 4, "D").put(55, 4, "T")
r.puts(12, [(14, "t"), (31, "t"), (49, "t")])

r = add("rooms_special", Room("boss_keeper", 70, 22, "boss_keeper", "ClockLung", nomirror=True))
r.floor(1).door_l(2)
r.box(1, 9, 8, 21)
r.put(11, 2, "G")
r.plat(15, 20, 5).plat(49, 54, 5)
r.plat(22, 28, 8).plat(41, 47, 8)
r.plat(30, 39, 11)
r.box(60, 2, 69, 3)
r.put(45, 2, "B").put(64, 4, "D").put(62, 4, "T")
r.puts(14, [(14, "t"), (34, "t"), (56, "t")])


# ===================================================== biome-flavoured rooms
r = add("rooms_biomes", Room("prom_moonbridge", 52, 17, "combat", "Promenade", weight=1.6))
r.floor(3).door_l(4).door_r(4).up(24)
r.air(9, 2, 43, 3).box(9, 2, 43, 3, "~")
r.box(15, 4, 17, 5).box(27, 4, 29, 5).box(39, 4, 41, 5)
r.plat(10, 13, 6).plat(19, 24, 7).plat(31, 36, 7).plat(44, 47, 6)
r.plat(14, 18, 10).plat(26, 30, 10).plat(36, 40, 10)
r.plat(22, 27, 13)
r.puts(4, [(5, "e"), (47, "e")]).puts(6, [(16, "e"), (40, "e")]).puts(12, [(20, "f"), (34, "f")])
r.puts(10, [(5, "t"), (46, "t")])

r = add("rooms_biomes", Room("prom_causeway", 48, 16, "combat", "Promenade", weight=1.4))
r.floor(1).door_l(2).door_r(2)
r.box(14, 2, 33, 4).air(19, 2, 28, 4)
r.box(19, 2, 28, 2, "X")
r.plat(19, 28, 5)
r.plat(6, 10, 7).plat(37, 41, 7).plat(12, 17, 10).plat(30, 35, 10)
r.puts(2, [(6, "e"), (40, "e")]).puts(5, [(16, "e"), (31, "e")]).puts(9, [(23, "f")]).put(23, 13, "f")
r.puts(12, [(8, "t"), (39, "t")])

r = add("rooms_biomes", Room("oss_ribs", 50, 17, "combat", "Ossuary", weight=1.6))
r.floor(1).door_l(2).door_r(2).up(22)
for rx in (9, 19, 29, 39):
    r.box(rx, 2, rx, 3).box(rx + 1, 2, rx + 1, 2)
r.plat(5, 12, 4).plat(15, 22, 7).plat(25, 32, 4).plat(35, 42, 7)
r.plat(10, 17, 10).plat(30, 36, 10).plat(20, 26, 13)
r.box(16, 2, 18, 2, "X").box(36, 2, 38, 2, "X")
r.puts(2, [(5, "e"), (24, "e"), (44, "e")]).puts(5, [(8, "o"), (28, "o")]).puts(8, [(18, "e"), (39, "e")])
r.puts(11, [(4, "t"), (25, "t"), (45, "t")])

r = add("rooms_biomes", Room("oss_crypt", 44, 15, "combat", "Ossuary", weight=1.2))
r.floor(0).door_l(1).door_r(1).down(20)
r.box(8, 1, 15, 3).box(28, 1, 35, 3)
r.plat(16, 27, 4).plat(4, 8, 4).plat(35, 39, 4)
r.plat(11, 16, 7).plat(27, 32, 7)
r.plat(18, 25, 10)
r.puts(1, [(4, "e"), (21, "o"), (39, "e")]).puts(4, [(10, "e"), (31, "e")]).put(21, 11, "e")
r.puts(9, [(5, "t"), (38, "t")])

r = add("rooms_biomes", Room("stilt_wine", 54, 17, "combat", "StiltVillage", weight=1.8))
r.floor(3).door_l(4).door_r(4).up(28)
r.air(7, 2, 46, 3).box(7, 2, 46, 3, "~")
r.plat(8, 13, 5).plat(17, 22, 7).plat(26, 31, 5).plat(35, 40, 7).plat(42, 46, 5)
r.plat(12, 17, 10).plat(23, 28, 10).plat(33, 38, 10)
r.plat(27, 32, 13)
r.puts(4, [(4, "e"), (50, "e")]).puts(6, [(10, "e"), (29, "e"), (44, "e")]).puts(8, [(19, "e"), (37, "e")]).puts(13, [(16, "f"), (40, "f")])
r.puts(10, [(4, "t"), (50, "t")])

r = add("rooms_biomes", Room("stilt_gables", 46, 18, "combat", "StiltVillage", weight=1.3))
r.floor(1).door_l(2).door_r(2)
r.box(10, 2, 15, 4).box(30, 2, 35, 4)
r.plat(10, 15, 7).plat(30, 35, 7).plat(18, 27, 9)
r.plat(5, 9, 10).plat(36, 40, 10).plat(20, 25, 12)
r.puts(2, [(5, "e"), (22, "e"), (40, "e")]).puts(5, [(12, "e"), (33, "e")]).puts(10, [(22, "e")]).put(22, 15, "f")
r.puts(12, [(8, "t"), (37, "t")])

r = add("rooms_biomes", Room("lung_gears", 50, 18, "combat", "ClockLung", weight=1.6))
r.floor(1).door_l(2).door_r(2).up(23)
r.box(12, 2, 14, 4).box(35, 2, 37, 4)
r.plat(6, 11, 4).plat(15, 20, 6).plat(29, 34, 6).plat(38, 43, 4)
r.plat(10, 15, 9).plat(34, 39, 9).plat(19, 30, 11)
r.plat(22, 27, 14)
r.puts(2, [(5, "e"), (25, "e"), (44, "e")]).puts(5, [(13, "o"), (36, "o")]).puts(12, [(24, "e")]).puts(15, [(15, "f"), (35, "f")])
r.puts(12, [(5, "t"), (44, "t")])

r = add("rooms_biomes", Room("lung_furnace", 48, 16, "combat", "ClockLung", weight=1.3))
r.floor(0).door_l(1).door_r(1).down(22)
r.box(17, 1, 19, 1, "X").box(28, 1, 30, 1, "X")
r.plat(6, 11, 3).plat(13, 17, 6).plat(30, 34, 6).plat(36, 41, 3)
r.plat(19, 28, 8)
r.puts(1, [(4, "e"), (24, "e"), (43, "e")]).puts(4, [(8, "e"), (38, "e")]).put(23, 9, "o")
r.puts(10, [(5, "t"), (42, "t")])

r = add("rooms_biomes", Room("oub_sewer", 46, 17, "combat", "Oubliette", weight=1.6))
r.floor(2).door_l(3).door_r(3).up(30)
r.air(10, 2, 17, 2).box(10, 2, 17, 2, "~").air(28, 2, 35, 2).box(28, 2, 35, 2, "~")
r.plat(10, 17, 5).plat(28, 35, 5)
r.plat(20, 25, 7).plat(27, 33, 10).plat(29, 34, 13)
r.puts(3, [(5, "e"), (22, "e"), (40, "e")]).put(13, 6, "e").put(31, 6, "e").put(22, 11, "f")
r.puts(9, [(6, "t"), (39, "t")])

r = add("rooms_biomes", Room("oub_cells", 44, 16, "combat", "Oubliette", weight=1.4))
r.floor(1).door_l(2).door_r(2)
for cx in (6, 15, 24, 33):
    r.box(cx, 6, cx + 6, 6, "=")
r.box(0, 7, 43, 7, "#").air(1, 7, 4, 7).air(39, 7, 42, 7)
r.plat(1, 4, 4).plat(39, 42, 4)
r.puts(2, [(5, "e"), (12, "e"), (21, "e"), (30, "e"), (38, "e")]).puts(8, [(10, "e"), (28, "e")])
r.puts(10, [(8, "t"), (22, "t"), (36, "t")])
r.puts(4, [(9, "t"), (27, "t")])


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.startswith("rooms_") and f.endswith(".txt"):
            os.remove(os.path.join(OUT, f))
    for file, rooms in ROOMS.items():
        header = "// Generated by Tools/Rooms/make_rooms.py - edit there, then run validate_rooms.py.\n\n"
        with open(os.path.join(OUT, file + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(header + "\n".join(r.text() for r in rooms))
    print(sum(len(v) for v in ROOMS.values()), "rooms written")


if __name__ == "__main__":
    main()
