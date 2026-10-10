using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace DeadCells.Run
{
    public enum Tile : byte
    {
        Solid,
        Air,
        OneWay,
        Liquid,
        Spikes,
    }

    public class RoomInfo
    {
        public RectInt rect;
        public string kind;
        public bool main;
        public int order;
        public string template;
    }

    public struct SpawnPoint
    {
        public char code;
        public Vector2Int cell;
        public int room;
    }

    public class LevelData
    {
        public int width, height;
        public Tile[,] tiles;
        public readonly List<RoomInfo> rooms = new List<RoomInfo>();
        public readonly List<SpawnPoint> spawns = new List<SpawnPoint>();
        public readonly List<RectInt> shafts = new List<RectInt>();
        public int seed;

        public Tile At(int x, int y) => x < 0 || y < 0 || x >= width || y >= height ? Tile.Solid : tiles[x, y];
        public bool Solid(int x, int y) => At(x, y) == Tile.Solid;

        public int RoomAt(Vector2 p)
        {
            for (int i = 0; i < rooms.Count; i++)
                if (rooms[i].rect.Contains(new Vector2Int(Mathf.FloorToInt(p.x), Mathf.FloorToInt(p.y))))
                    return i;
            return -1;
        }
    }

    /// <summary>
    /// One hand-authored room from Resources/Rooms/*.txt. Grid rows are written
    /// top to bottom; cells are stored with y = 0 at the bottom.
    /// </summary>
    public class RoomTemplate
    {
        public string name;
        public HashSet<string> tags = new HashSet<string>();
        public string[] biomes = { "all" };
        public float weight = 1f;
        public bool noMirror;
        public int w, h;
        public char[,] c;

        public readonly List<int> left = new List<int>();
        public readonly List<int> right = new List<int>();
        public readonly List<List<int>> up = new List<List<int>>();
        public readonly List<List<int>> down = new List<List<int>>();

        public int EntryY => left.Count > 0 ? left.Min() : 0;
        public int ExitY => right.Count > 0 ? right.Min() : 0;

        public bool AllowedIn(string biome) => biomes.Contains("all") || biomes.Contains(biome);

        public void Index()
        {
            left.Clear();
            right.Clear();
            up.Clear();
            down.Clear();
            for (int y = 0; y < h; y++)
            {
                if (c[0, y] == '<') left.Add(y);
                if (c[w - 1, y] == '>') right.Add(y);
            }
            Groups(h - 1, '^', up);
            Groups(0, 'v', down);
        }

        void Groups(int row, char code, List<List<int>> into)
        {
            List<int> cur = null;
            for (int x = 0; x < w; x++)
            {
                if (c[x, row] == code)
                {
                    cur ??= new List<int>();
                    cur.Add(x);
                }
                else if (cur != null)
                {
                    into.Add(cur);
                    cur = null;
                }
            }
            if (cur != null)
                into.Add(cur);
        }

        public RoomTemplate Mirrored()
        {
            var m = new RoomTemplate { name = name + "~m", tags = tags, biomes = biomes, weight = weight, noMirror = noMirror, w = w, h = h, c = new char[w, h] };
            for (int x = 0; x < w; x++)
            for (int y = 0; y < h; y++)
            {
                char ch = c[w - 1 - x, y];
                m.c[x, y] = ch == '<' ? '>' : ch == '>' ? '<' : ch;
            }
            m.Index();
            return m;
        }
    }

    public static class RoomLibrary
    {
        static List<RoomTemplate> all;

        public static List<RoomTemplate> All
        {
            get
            {
                if (all == null)
                    Load();
                return all;
            }
        }

        public static void Load()
        {
            all = new List<RoomTemplate>();
            foreach (var asset in Resources.LoadAll<TextAsset>("Rooms"))
                Parse(asset.text, asset.name);
        }

        static void Parse(string text, string file)
        {
            RoomTemplate cur = null;
            var rows = new List<string>();
            void Flush()
            {
                if (cur == null || rows.Count == 0)
                {
                    cur = null;
                    rows.Clear();
                    return;
                }
                cur.h = rows.Count;
                cur.w = rows.Max(r => r.Length);
                cur.c = new char[cur.w, cur.h];
                for (int r = 0; r < rows.Count; r++)
                for (int x = 0; x < cur.w; x++)
                    cur.c[x, cur.h - 1 - r] = x < rows[r].Length ? rows[r][x] : '#';
                cur.Index();
                all.Add(cur);
                cur = null;
                rows.Clear();
            }
            foreach (var raw in text.Split('\n'))
            {
                string line = raw.TrimEnd('\r', ' ', '\t');
                if (line.StartsWith("@"))
                {
                    Flush();
                    cur = new RoomTemplate();
                    foreach (var part in line.Substring(1).Split(new[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries))
                    {
                        int eq = part.IndexOf('=');
                        if (eq < 0)
                        {
                            if (part == "nomirror") cur.noMirror = true;
                            continue;
                        }
                        string k = part.Substring(0, eq), v = part.Substring(eq + 1);
                        switch (k)
                        {
                            case "name": cur.name = v; break;
                            case "tags": cur.tags = new HashSet<string>(v.Split(',')); break;
                            case "biomes": cur.biomes = v.Split(','); break;
                            case "weight": cur.weight = float.Parse(v, System.Globalization.CultureInfo.InvariantCulture); break;
                        }
                    }
                    continue;
                }
                if (line.StartsWith("#!") || line.StartsWith("//"))
                    continue;
                if (line.Length == 0)
                {
                    Flush();
                    continue;
                }
                if (cur != null)
                    rows.Add(line);
            }
            Flush();
        }
    }

    /// <summary>
    /// Builds a level from room templates: a left-to-right main path (doors
    /// aligned at their floor rows, so the path climbs and drops), with side
    /// rooms (shop, treasure, lore, elite) hung above or below through
    /// vertical shafts. Unused openings are sealed.
    /// </summary>
    public static class LevelGenerator
    {
        class Placed
        {
            public RoomTemplate t;
            public Vector2Int o;
            public bool main;
            public int order;
            public string kind;
            public readonly HashSet<int> openUp = new HashSet<int>();
            public readonly HashSet<int> openDown = new HashSet<int>();
            public RectInt Rect => new RectInt(o.x, o.y, t.w, t.h);
        }

        const int Margin = 8;

        public static LevelData Generate(BiomeDef biome, int seed, string singleRoomTag = null)
        {
            var rng = new System.Random(seed);
            var lib = RoomLibrary.All;
            var placed = new List<Placed>();
            var shafts = new List<(RectInt rect, int platformTop, int platformBottom)>();

            if (singleRoomTag != null || biome.isPassage)
            {
                string tag = singleRoomTag ?? "passage";
                var t = Choose(lib, tag, biome.isPassage ? "Passage" : biome.id, rng, false, false);
                placed.Add(new Placed { t = t, o = Vector2Int.zero, main = true, kind = tag });
            }
            else
            {
                var plan = Plan(biome, rng);
                int x = 0, doorY = 0;
                for (int i = 0; i < plan.Count; i++)
                {
                    bool needL = i > 0, needR = i < plan.Count - 1;
                    var t = Choose(lib, plan[i], biome.id, rng, needL, needR);
                    int oy = i == 0 ? 0 : doorY - t.EntryY;
                    placed.Add(new Placed { t = t, o = new Vector2Int(x, oy), main = true, order = i, kind = plan[i] });
                    if (needR)
                        doorY = oy + t.ExitY;
                    x += t.w;
                }
                AttachSideRooms(biome, rng, lib, placed, shafts);
            }

            // Bounds.
            int minX = int.MaxValue, minY = int.MaxValue, maxX = int.MinValue, maxY = int.MinValue;
            foreach (var p in placed)
            {
                var r = p.Rect;
                minX = Mathf.Min(minX, r.xMin); minY = Mathf.Min(minY, r.yMin);
                maxX = Mathf.Max(maxX, r.xMax); maxY = Mathf.Max(maxY, r.yMax);
            }
            var shift = new Vector2Int(Margin - minX, Margin - minY);
            var level = new LevelData
            {
                width = maxX - minX + Margin * 2,
                height = maxY - minY + Margin * 2,
                seed = seed,
            };
            level.tiles = new Tile[level.width, level.height]; // all Solid

            int index = 0;
            foreach (var p in placed)
            {
                p.o += shift;
                Carve(level, p, index++);
            }
            foreach (var (rect, top, bottom) in shafts)
            {
                var r = new RectInt(rect.position + shift, rect.size);
                level.shafts.Add(r);
                for (int sx = r.xMin; sx < r.xMax; sx++)
                for (int sy = r.yMin; sy < r.yMax; sy++)
                    level.tiles[sx, sy] = Tile.Air;
                // Climbing platforms between the two openings, evenly spaced 2-3 rows
                // apart (never adjacent: a platform one row up sits inside the body).
                int low = bottom + shift.y, high = top + shift.y;
                int gap = high - low;
                int steps = Mathf.Max(1, Mathf.CeilToInt(gap / 3f));
                int py = low;
                for (int i = 0; i < steps - 1; i++)
                {
                    int remaining = high - py;
                    py += Mathf.CeilToInt(remaining / (float)(steps - i));
                    for (int sx = r.xMin; sx < r.xMax; sx++)
                        if (py >= r.yMin && py < r.yMax)
                            level.tiles[sx, py] = Tile.OneWay;
                }
            }
            ThinTeleporters(level, rng);
            return level;
        }

        static List<string> Plan(BiomeDef biome, System.Random rng)
        {
            var plan = new List<string> { "start" };
            string prev = "start";
            for (int i = 0; i < biome.mainRooms; i++)
            {
                string kind;
                double r = rng.NextDouble();
                if (prev != "combat")
                    kind = "combat";
                else if (r < 0.58) kind = "combat";
                else if (r < 0.72) kind = "climb";
                else if (r < 0.86) kind = "drop";
                else kind = "corridor";
                plan.Add(kind);
                prev = kind;
            }
            plan.Add(string.IsNullOrEmpty(biome.bossTag) ? "exit" : biome.bossTag);
            return plan;
        }

        static RoomTemplate Choose(List<RoomTemplate> lib, string tag, string biome, System.Random rng, bool needL, bool needR, bool needUp = false, bool needDown = false)
        {
            var pool = new List<RoomTemplate>();
            foreach (var t in lib)
            {
                if (!t.tags.Contains(tag) || !t.AllowedIn(biome))
                    continue;
                foreach (var v in t.noMirror || tag == "start" || tag == "passage" || tag.StartsWith("boss") || tag == "exit"
                             ? new[] { t } : new[] { t, t.Mirrored() })
                {
                    if (needL != (v.left.Count > 0) || needR != (v.right.Count > 0))
                        continue;
                    if (needUp && v.up.Count == 0) continue;
                    if (needDown && v.down.Count == 0) continue;
                    pool.Add(v);
                }
            }
            if (pool.Count == 0)
            {
                // Fall back to any combat room so generation never fails.
                if (tag != "combat")
                    return Choose(lib, "combat", biome, rng, needL, needR);
                throw new System.InvalidOperationException($"No room template for tag '{tag}' in {biome}");
            }
            float total = pool.Sum(t => t.weight);
            double pick = rng.NextDouble() * total;
            foreach (var t in pool)
            {
                pick -= t.weight;
                if (pick <= 0)
                    return t;
            }
            return pool[pool.Count - 1];
        }

        static void AttachSideRooms(BiomeDef biome, System.Random rng, List<RoomTemplate> lib, List<Placed> placed, List<(RectInt, int, int)> shafts)
        {
            var needs = new List<string>();
            if (biome.merchant) needs.Add("shop");
            for (int i = 0; i < biome.treasureRooms; i++) needs.Add("treasure");
            for (int i = 0; i < Mathf.Min(3, biome.lore.Length); i++) needs.Add("lore");
            for (int i = 0; i < biome.eliteRooms; i++) needs.Add("elite");
            // Shuffle, but keep the shop early in the list so it is placed first.
            for (int i = needs.Count - 1; i > 0; i--)
            {
                int j = rng.Next(i + 1);
                (needs[i], needs[j]) = (needs[j], needs[i]);
            }
            int shop = needs.IndexOf("shop");
            if (shop > 0)
                (needs[0], needs[shop]) = (needs[shop], needs[0]);

            var hosts = placed.Where(p => p.main && p.order > 0).OrderBy(_ => rng.Next()).ToList();
            foreach (var host in hosts)
            {
                foreach (var group in host.t.up.Concat(host.t.down).OrderBy(_ => rng.Next()).ToList())
                {
                    if (needs.Count == 0)
                        break;
                    bool upward = host.t.up.Contains(group);
                    for (int attempt = 0; attempt < needs.Count; attempt++)
                    {
                        string kind = needs[attempt];
                        if (TryAttach(host, group, upward, kind, biome, rng, lib, placed, shafts))
                        {
                            needs.RemoveAt(attempt);
                            break;
                        }
                    }
                }
            }
        }

        static bool TryAttach(Placed host, List<int> group, bool upward, string kind, BiomeDef biome, System.Random rng,
            List<RoomTemplate> lib, List<Placed> placed, List<(RectInt, int, int)> shafts)
        {
            for (int tries = 0; tries < 6; tries++)
            {
                RoomTemplate t;
                try
                {
                    t = Choose(lib, kind, biome.id, rng, false, false, !upward, upward);
                }
                catch (System.InvalidOperationException)
                {
                    return false;
                }
                var groups = upward ? t.down : t.up;
                var match = groups.FirstOrDefault(g => g.Count == group.Count);
                if (match == null)
                    continue;
                int len = rng.Next(3, 8);
                int sx = host.o.x + group[0] - match[0];
                int sy = upward ? host.o.y + host.t.h + len : host.o.y - len - t.h;
                var rect = new RectInt(sx, sy, t.w, t.h);
                var shaft = upward
                    ? new RectInt(host.o.x + group[0], host.o.y + host.t.h, group.Count, len)
                    : new RectInt(host.o.x + group[0], sy + t.h, group.Count, len);
                if (Overlaps(Pad(rect, 2), placed, host, null) || Overlaps(Pad(shaft, 1), placed, host, null))
                    continue;
                bool clash = false;
                foreach (var (r, _, _) in shafts)
                    if (Pad(r, 2).Overlaps(rect) || Pad(r, 1).Overlaps(shaft))
                        clash = true;
                if (clash)
                    continue;
                var side = new Placed { t = t, o = new Vector2Int(sx, sy), main = false, kind = kind };
                foreach (int gx in match)
                    (upward ? side.openDown : side.openUp).Add(gx);
                foreach (int gx in group)
                    (upward ? host.openUp : host.openDown).Add(gx);
                placed.Add(side);
                // Platforms run from the upper room's opening row down to the lower room's.
                int upperRow = upward ? sy : host.o.y;
                int lowerRow = upward ? host.o.y + host.t.h - 1 : sy + t.h - 1;
                shafts.Add((shaft, upperRow, lowerRow));
                return true;
            }
            return false;
        }

        static RectInt Pad(RectInt r, int p) => new RectInt(r.x - p, r.y - p, r.width + p * 2, r.height + p * 2);

        static bool Overlaps(RectInt r, List<Placed> placed, Placed except, Placed except2)
        {
            foreach (var p in placed)
            {
                if (p == except || p == except2)
                    continue;
                if (p.Rect.Overlaps(r))
                    return true;
            }
            return false;
        }

        static void Carve(LevelData level, Placed p, int index)
        {
            var t = p.t;
            level.rooms.Add(new RoomInfo { rect = p.Rect, kind = p.kind, main = p.main, order = p.order, template = t.name });
            for (int x = 0; x < t.w; x++)
            for (int y = 0; y < t.h; y++)
            {
                char ch = t.c[x, y];
                int gx = p.o.x + x, gy = p.o.y + y;
                Tile tile;
                switch (ch)
                {
                    case '#': tile = Tile.Solid; break;
                    case '=': tile = Tile.OneWay; break;
                    case '~': tile = Tile.Liquid; break;
                    case 'X': tile = Tile.Spikes; break;
                    case '^': tile = p.openUp.Contains(x) ? Tile.OneWay : Tile.Solid; break;
                    case 'v': tile = p.openDown.Contains(x) ? Tile.OneWay : Tile.Solid; break;
                    case '.':
                    case '<':
                    case '>':
                        tile = Tile.Air;
                        break;
                    default:
                        tile = Tile.Air;
                        level.spawns.Add(new SpawnPoint { code = ch, cell = new Vector2Int(gx, gy), room = index });
                        break;
                }
                level.tiles[gx, gy] = tile;
            }
        }

        /// <summary>Keep teleporters at the start, the exit and roughly every third room.</summary>
        static void ThinTeleporters(LevelData level, System.Random rng)
        {
            int lastKept = -10;
            for (int i = level.spawns.Count - 1; i >= 0; i--)
            {
                var s = level.spawns[i];
                if (s.code != 'T')
                    continue;
                var room = level.rooms[s.room];
                bool keep = !room.main || room.kind == "start" || room.kind == "exit" || room.kind.StartsWith("boss") || room.kind == "passage";
                if (!keep && room.main && Mathf.Abs(room.order - lastKept) >= 3)
                    keep = rng.NextDouble() < 0.8;
                if (keep && room.main)
                    lastKept = room.order;
                if (!keep)
                    level.spawns.RemoveAt(i);
            }
        }
    }
}
