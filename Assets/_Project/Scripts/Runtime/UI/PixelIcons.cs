using System.Collections.Generic;
using UnityEngine;

namespace DeadCells.UI
{
    /// <summary>16x16 pixel-art icons for items, currencies and map markers, built at runtime.</summary>
    public static class PixelIcons
    {
        static readonly Dictionary<char, Color32> Palette = new Dictionary<char, Color32>
        {
            ['k'] = new Color32(12, 10, 20, 255),
            ['w'] = new Color32(240, 240, 235, 255),
            ['g'] = new Color32(150, 160, 175, 255),
            ['G'] = new Color32(215, 222, 232, 255),
            ['r'] = new Color32(140, 64, 30, 255),
            ['R'] = new Color32(196, 38, 44, 255),
            ['b'] = new Color32(118, 72, 38, 255),
            ['B'] = new Color32(70, 40, 20, 255),
            ['y'] = new Color32(255, 205, 80, 255),
            ['Y'] = new Color32(180, 125, 40, 255),
            ['p'] = new Color32(150, 90, 240, 255),
            ['P'] = new Color32(215, 170, 255, 255),
            ['c'] = new Color32(100, 210, 255, 255),
            ['C'] = new Color32(200, 245, 255, 255),
            ['n'] = new Color32(40, 70, 120, 255),
            ['o'] = new Color32(255, 140, 40, 255),
            ['O'] = new Color32(255, 225, 90, 255),
            ['e'] = new Color32(80, 205, 100, 255),
            ['E'] = new Color32(180, 255, 160, 255),
        };

        static readonly Dictionary<string, string[]> Art = new Dictionary<string, string[]>
        {
            ["melee_cleaver"] = new[]
            {
                "................", ".........kkkkkk.", "........kGGGGGGk", ".......kGgggggGk", "......kGgggggGk.", ".....kGgggrgGk..",
                "....kGggrgggk...", "...kGgggggGk....", "...kgggrggk.....", "....kgggk.......", "...kBkkk........", "..kbBk..........",
                ".kbBk...........", "kbBk............", "kBk.............", ".k..............",
            },
            ["melee_rusty"] = new[]
            {
                "..............kk", ".............kGk", "............kGgk", "...........kGgk.", "..........kGgk..", ".........kGrk...",
                "........kGgk....", ".......kGgk.....", "..kk..kGrk......", "..kYkkGgk.......", "...kYYgk........", "....kYYk........",
                "...kbkYYk.......", "..kbk.kkYk......", ".kBk.....k......", ".kk.............",
            },
            ["melee_broadsword"] = new[]
            {
                ".............kkk", "............kGGk", "...........kGggk", "..........kGggk.", ".........kGggk..", "........kGggk...",
                ".......kGggk....", "......kGggk.....", "..kk.kGggk......", "..kYkGggk.......", "...kYYgk........", "....kYYYk.......",
                "...kbkkYYk......", "..kbk...kk......", ".kBk............", ".kk.............",
            },
            ["melee_spear"] = new[]
            {
                ".............kk.", "............kGGk", "...........kGGgk", "...........kGgk.", "..........kGgk..", ".........kYk....",
                "........kbk.....", ".......kbk......", "......kbk.......", ".....kbk........", "....kbk.........", "...kbk..........",
                "..kbk...........", ".kBk............", ".kk.............", "................",
            },
            ["melee_daggers"] = new[]
            {
                "................", ".kk..........kk.", "kGGk........kGGk", ".kGgk......kgGk.", "..kGgk....kgGk..", "...kGgk..kgGk...",
                "....kGgkkgGk....", ".....kGggGk.....", ".....kYkkYk.....", "....kYk..kYk....", "...kbk....kbk...", "..kbk......kbk..",
                ".kBk........kBk.", ".kk..........kk.", "................", "................",
            },
            ["melee_bellmaul"] = new[]
            {
                "..........kkk...", ".........kYyYk..", "........kYyyyYk.", "......kkYyyyyOOk", ".....kgkYyyyyOOk", "......kkYyyyyYk.",
                ".......kkYyyYk..", "......kbk.kkk...", ".....kbk........", "....kbk.........", "...kbk..........", "..kbk...........",
                ".kBk............", "kBk.............", "kgk.............", ".k..............",
            },
            ["melee_rapier"] = new[]
            {
                "..............kk", ".............kGk", "............kGk.", "...........kGk..", "..........kGk...", ".........kGk....",
                "........kGk.....", ".......kGk......", "..kyk.kGk.......", "...kykOk........", "....kyyk........", "...kbkkyk.......",
                "..kbk..kyk......", ".kbk....kk......", ".kyk............", "..k.............",
            },
            ["melee_scythe"] = new[]
            {
                ".....kkkkkk.....", "...kkGGGGGGkk...", "..kGGkkkkkkGGk..", "..kbk......kGGk.", "..kbk.......kGk.", "..kbk........kk.",
                "..kbk...........", "..kbkk..........", "..kbbbk.........", "..kbkk..........", "..kbk...........", "..kbk...........",
                "..kbk...........", "..kbk...........", "..kgk...........", "...k............",
            },
            ["melee_flail"] = new[]
            {
                "...........k....", "........kk.g.k..", ".......kgkkgkk..", "........kgggggk.", ".......kgggOOgk.", "......kkggOOggkk",
                "........kgggggk.", ".......kk.kgk.k.", "......kg...k....", ".....kg.........", "....kg..........", "...kbk..........",
                "..kbbk..........", ".kbk............", ".kgk............", "..k.............",
            },
            ["melee_shovel"] = new[]
            {
                "............kk..", "..........kkGGk.", ".........kGgggGk", "........kGgOgggk", ".........kgggOgk", "........kkgggGk.",
                ".......kbkkkkk..", "......kbk.......", ".....kbk........", "....kbk.........", "...kbk..........", "..kbk...........",
                ".kgk............", "kgkgk...........", ".kkk............", "................",
            },
            ["bow_crossbow"] = new[]
            {
                "...........kk...", "..........kwwk..", "..........kw.k..", "..........kw..k.", "..........kw..k.", "kkkkkkkkkkkwkkk.",
                "kbbbbbbbbbbGGGGk", "kBbbkkbbbbbwkkk.", "kkkk.kbk..kw..k.", ".....kbk..kw..k.", ".....kkk..kw.k..", "..........kwwk..",
                "...........kk...", "................", "................", "................",
            },
            ["shield_frontline"] = new[]
            {
                "................", "...kkkkkkkkkk...", "..kGGGGGGGGGGk..", "..kGRRRRRRRRGk..", "..kGRRRyyRRRGk..", "..kGRRRyyRRRGk..",
                "..kGRRyyyyRRGk..", "..kGRRRyyRRRGk..", "..kGRRRyyRRRGk..", "...kGRRRRRRGk...", "...kGRRRRRRGk...", "....kGRRRRGk....",
                ".....kGRRGk.....", "......kGGk......", ".......kk.......", "................",
            },
            ["bow_spiked"] = new[]
            {
                ".....kk.........", "....kbBk........", "....kbk.k.......", "...kbk..wk......", "...kbk...w......", "..kbkG...w......",
                "..kbk....w......", "..kbk...kGGGGGk.", "..kbk....w......", "..kbk....w......", "..kbkG...w......", "...kbk...w......",
                "...kbk..wk......", "....kbk.k.......", "....kbBk........", ".....kk.........",
            },
            ["skill_fire_grenade"] = new[]
            {
                "..........O.....", ".........oO.....", "........kok.....", ".......k..k.....", ".....kkkkk......", "....kBBBBBk.....",
                "...kBoooooBk....", "..kBoOOooooBk...", "..kBoOOooooBk...", "..kBooooooooBk..", "..kBooooooooBk..", "..kBBooooooBBk..",
                "...kBBooooBBk...", "....kBBBBBBk....", ".....kkkkkk.....", "................",
            },
            ["skill_ice_grenade"] = new[]
            {
                "..........C.....", ".........cC.....", "........kck.....", ".......k..k.....", ".....kkkkk......", "....knnnnnk.....",
                "...kncccccnk....", "..kncCCccccnk...", "..kncCCccccnk...", "..knccccccccnk..", "..knccccccccnk..", "..knnccccccnnk..",
                "...knnccccnnk...", "....knnnnnnk....", ".....kkkkkk.....", "................",
            },
            ["skill_harpoon"] = new[]
            {
                "............kkk.", "...........kCCk.", "..........kCCck.", ".........kCck.k.", "........kCck....", ".......kgk..O...",
                "......kgk..O....", ".....kbk..OO....", "....kbk....O....", "...kbk....O.....", "..kbk...........", ".kbk............",
                "kBk.............", "kk..............", "................", "................",
            },
            ["flask"] = new[]
            {
                "......kkkk......", "......kbbk......", ".......kk.......", "......kGGk......", ".....kGEEGk.....", "....kGEEEEGk....",
                "...kGeEEEEeGk...", "...kGeeeeeeGk...", "...kGeeeeeeGk...", "...kGeeeeeeGk...", "....kGeeeeGk....", ".....kkkkkk.....",
                "................", "................", "................", "................",
            },
            ["gold"] = new[]
            {
                "................", "................", ".....kkkkkk.....", "....kyyyyyyk....", "...kyYyyyyyyk...", "...kyYyyyyyyk...",
                "...kyYyyyyYyk...", "...kyYyyyyYyk...", "...kyyyyyyYyk...", "...kyyyyyyYyk...", "....kyyyyyyk....", ".....kkkkkk.....",
                "................", "................", "................", "................",
            },
            ["cell"] = new[]
            {
                "................", "................", "......kkkk......", ".....kccccK.....", "....kcCCcccK....", "....kcCcccck....",
                "....kcccccck....", "....kccccnck....", ".....kccnck.....", "......kkkk......", "................", "................",
                "................", "................", "................", "................",
            },
            ["teleporter"] = new[]
            {
                "......kkkk......", ".....kPppPk.....", ".....kpPPpk.....", "......kppk......", "......kppk......", ".....kpPPpk.....",
                "....kppPPppk....", "....kpppppppk...", "....kkkkkkkk....", "................", "................", "................",
                "................", "................", "................", "................",
            },
            ["door"] = new[]
            {
                "....kkkkkkkk....", "...kbbbbbbbbk...", "...kbBbbbbBbk...", "...kbBbbbbBbk...", "...kbBbbbbBbk...", "...kbBbbybBbk...",
                "...kbBbbbbBbk...", "...kbBbbbbBbk...", "...kkkkkkkkkk...", "................", "................", "................",
                "................", "................", "................", "................",
            },
            ["chest"] = new[]
            {
                "................", "...kkkkkkkkkk...", "..kbbbbbbbbbbk..", "..kbYYYYYYYYbk..", "..kkkkkyykkkkk..", "..kbbbbyybbbbk..",
                "..kbbbbbbbbbbk..", "..kYbbbbbbbbYk..", "..kkkkkkkkkkkk..", "................", "................", "................",
                "................", "................", "................", "................",
            },
            ["lore"] = new[]
            {
                "....kkkkkkk.....", "...kgGGGGGgk....", "...kgkkGkkgk....", "...kgGGGGGgk....", "...kgkGkkGgk....", "...kgGGGGGgk....",
                "...kgkkGkkgk....", "...kgGGGGGgk....", "...kkkkkkkkk....", "................", "................", "................",
                "................", "................", "................", "................",
            },
            ["shop"] = new[]
            {
                "......kkk.......", ".....kyYk.......", "....kkkkkk......", "...kyyyyyyk.....", "..kyyYyyyyyk....", "..kyYyyyyyyk....",
                "..kyyyyyyYyk....", "...kyyyyyyk.....", "....kkkkkk......", "................", "................", "................",
                "................", "................", "................", "................",
            },
            ["player"] = new[]
            {
                "......kkkk......", ".....kPPPPk.....", ".....kPwwPk.....", "......kppk......", ".....kRRRRk.....", "....kRRRRRRk....",
                ".....kggggk.....", ".....kg..gk.....", ".....kk..kk.....", "................", "................", "................",
                "................", "................", "................", "................",
            },
        };

        static readonly Dictionary<string, Sprite> Cache = new Dictionary<string, Sprite>();

        public static bool Has(string id) => Art.ContainsKey(id);

        public static Sprite Get(string id)
        {
            if (string.IsNullOrEmpty(id))
                return null;
            if (Cache.TryGetValue(id, out var s))
                return s;
            if (!Art.TryGetValue(id, out var rows))
                return null;
            var tex = new Texture2D(16, 16, TextureFormat.RGBA32, false)
            {
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                name = "Icon_" + id,
                hideFlags = HideFlags.DontSave,
            };
            var px = new Color32[256];
            for (int r = 0; r < 16; r++)
            {
                string row = r < rows.Length ? rows[r] : "";
                for (int c = 0; c < 16; c++)
                {
                    char ch = c < row.Length ? row[c] : '.';
                    if (ch == 'K')
                        ch = 'k';
                    px[(15 - r) * 16 + c] = Palette.TryGetValue(ch, out var col) ? col : new Color32(0, 0, 0, 0);
                }
            }
            tex.SetPixels32(px);
            tex.Apply(false, true);
            s = Sprite.Create(tex, new Rect(0, 0, 16, 16), new Vector2(0.5f, 0.5f), 16f);
            s.name = id;
            Cache[id] = s;
            return s;
        }

        public static Sprite For(Items.ItemDef item) => item == null ? null : item.icon != null ? item.icon : Get(item.id);
    }
}
