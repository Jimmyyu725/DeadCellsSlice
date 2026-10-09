using System.Collections.Generic;
using UnityEngine;

namespace DeadCells.UI
{
    /// <summary>
    /// Tiny 5x7 bitmap font baked into a point-filtered atlas at runtime.
    /// Each glyph cell is 6x8 texels (1 texel gutter) with a 1-texel dark
    /// outline baked into a second layer, so text reads on any background.
    /// </summary>
    public static class PixelFont
    {
        public const int GlyphW = 5;
        public const int GlyphH = 7;
        public const int CellW = 8;   // glyph + 1px outline each side + gutter
        public const int CellH = 10;
        const int Columns = 16;

        static readonly Dictionary<char, string[]> Glyphs = new Dictionary<char, string[]>
        {
            ['0'] = new[] { ".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###." },
            ['1'] = new[] { "..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###." },
            ['2'] = new[] { ".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####" },
            ['3'] = new[] { "####.", "....#", "....#", ".###.", "....#", "....#", "####." },
            ['4'] = new[] { "...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#." },
            ['5'] = new[] { "#####", "#....", "####.", "....#", "....#", "#...#", ".###." },
            ['6'] = new[] { "..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###." },
            ['7'] = new[] { "#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..." },
            ['8'] = new[] { ".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###." },
            ['9'] = new[] { ".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.." },
            ['A'] = new[] { ".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#" },
            ['B'] = new[] { "####.", "#...#", "#...#", "####.", "#...#", "#...#", "####." },
            ['C'] = new[] { ".###.", "#...#", "#....", "#....", "#....", "#...#", ".###." },
            ['D'] = new[] { "####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####." },
            ['E'] = new[] { "#####", "#....", "#....", "####.", "#....", "#....", "#####" },
            ['F'] = new[] { "#####", "#....", "#....", "####.", "#....", "#....", "#...." },
            ['G'] = new[] { ".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####" },
            ['H'] = new[] { "#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#" },
            ['I'] = new[] { ".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###." },
            ['J'] = new[] { "..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.." },
            ['K'] = new[] { "#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#" },
            ['L'] = new[] { "#....", "#....", "#....", "#....", "#....", "#....", "#####" },
            ['M'] = new[] { "#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#" },
            ['N'] = new[] { "#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#" },
            ['O'] = new[] { ".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###." },
            ['P'] = new[] { "####.", "#...#", "#...#", "####.", "#....", "#....", "#...." },
            ['Q'] = new[] { ".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#" },
            ['R'] = new[] { "####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#" },
            ['S'] = new[] { ".####", "#....", "#....", ".###.", "....#", "....#", "####." },
            ['T'] = new[] { "#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.." },
            ['U'] = new[] { "#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###." },
            ['V'] = new[] { "#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.." },
            ['W'] = new[] { "#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#." },
            ['X'] = new[] { "#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#" },
            ['Y'] = new[] { "#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.." },
            ['Z'] = new[] { "#####", "....#", "...#.", "..#..", ".#...", "#....", "#####" },
            ['/'] = new[] { "....#", "....#", "...#.", "..#..", ".#...", "#....", "#...." },
            ['!'] = new[] { "..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.." },
            ['?'] = new[] { ".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.." },
            ['.'] = new[] { ".....", ".....", ".....", ".....", ".....", ".....", "..#.." },
            [':'] = new[] { ".....", "..#..", ".....", ".....", ".....", "..#..", "....." },
            ['-'] = new[] { ".....", ".....", ".....", "#####", ".....", ".....", "....." },
            ['+'] = new[] { ".....", "..#..", "..#..", "#####", "..#..", "..#..", "....." },
            ['%'] = new[] { "##..#", "##..#", "...#.", "..#..", ".#...", "#..##", "#..##" },
            [' '] = new[] { ".....", ".....", ".....", ".....", ".....", ".....", "....." },
            [','] = new[] { ".....", ".....", ".....", ".....", ".....", "..#..", ".#..." },
            ['\''] = new[] { "..#..", "..#..", ".#...", ".....", ".....", ".....", "....." },
            ['"'] = new[] { ".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....." },
            ['('] = new[] { "...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#." },
            [')'] = new[] { ".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..." },
            ['['] = new[] { ".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###." },
            [']'] = new[] { ".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###." },
            [';'] = new[] { ".....", "..#..", ".....", ".....", ".....", "..#..", ".#..." },
            ['='] = new[] { ".....", ".....", "#####", ".....", "#####", ".....", "....." },
            ['<'] = new[] { "...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#." },
            ['>'] = new[] { ".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..." },
            ['_'] = new[] { ".....", ".....", ".....", ".....", ".....", ".....", "#####" },
            ['#'] = new[] { ".#.#.", "#####", ".#.#.", ".#.#.", ".#.#.", "#####", ".#.#." },
            ['*'] = new[] { ".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....." },
            ['&'] = new[] { ".##..", "#..#.", ".##..", ".#...", "#.#.#", "#..#.", ".##.#" },
            ['x'] = new[] { ".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#" },
        };

        static Texture2D atlas;
        static readonly Dictionary<char, int> Index = new Dictionary<char, int>();

        public static Texture2D Atlas
        {
            get
            {
                if (atlas == null)
                    Build();
                return atlas;
            }
        }

        static void Build()
        {
            var keys = new List<char>(Glyphs.Keys);
            int rows = Mathf.CeilToInt(keys.Count / (float)Columns);
            int w = Columns * CellW;
            int h = rows * CellH;
            atlas = new Texture2D(w, h, TextureFormat.RGBA32, false)
            {
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                name = "DC_PixelFont",
                hideFlags = HideFlags.DontSave,
            };
            var px = new Color32[w * h];
            for (int i = 0; i < keys.Count; i++)
            {
                Index[keys[i]] = i;
                int cx = (i % Columns) * CellW;
                int cy = (i / Columns) * CellH;
                string[] g = Glyphs[keys[i]];
                // Pass 1: outline (dark, alpha 1) around every lit texel.
                for (int r = 0; r < GlyphH; r++)
                for (int c = 0; c < GlyphW; c++)
                {
                    if (g[r][c] != '#')
                        continue;
                    for (int oy = -1; oy <= 1; oy++)
                    for (int ox = -1; ox <= 1; ox++)
                    {
                        int x = cx + 1 + c + ox;
                        int y = cy + 1 + (GlyphH - 1 - r) + oy;
                        int k = y * w + x;
                        if (px[k].a == 0)
                            px[k] = new Color32(10, 6, 16, 255);
                    }
                }
                // Pass 2: glyph body (white; tinted by vertex colour).
                for (int r = 0; r < GlyphH; r++)
                for (int c = 0; c < GlyphW; c++)
                {
                    if (g[r][c] != '#')
                        continue;
                    int x = cx + 1 + c;
                    int y = cy + 1 + (GlyphH - 1 - r);
                    px[y * w + x] = new Color32(255, 255, 255, 255);
                }
            }
            atlas.SetPixels32(px);
            atlas.Apply(false, false);
        }

        /// <summary>UV rect of a glyph cell including its outline border (7x9 texels).</summary>
        public static Rect GlyphUV(char c)
        {
            var tex = Atlas;
            if (c != 'x')
                c = char.ToUpperInvariant(c);
            if (!Index.TryGetValue(c, out int i))
                i = Index[' '];
            int cx = (i % Columns) * CellW;
            int cy = (i / Columns) * CellH;
            return new Rect(cx / (float)tex.width, cy / (float)tex.height, 7f / tex.width, 9f / tex.height);
        }

        /// <summary>Advance in font texels (glyph 5 + 1 spacing; outlines overlap neighbours).</summary>
        public const int Advance = 6;
        public const int QuadW = 7;
        public const int QuadH = 9;

        /// <summary>Append quads for `text` (origin = bottom-left, units = texels * scale).</summary>
        public static void AppendQuads(string text, Vector2 origin, float scale, Color32 color,
            List<Vector3> verts, List<Vector2> uvs, List<Color32> colors, List<int> tris)
        {
            float x = origin.x;
            foreach (char ch in text)
            {
                Rect uv = GlyphUV(ch);
                int b = verts.Count;
                float x0 = x - scale, y0 = origin.y - scale;
                float x1 = x0 + QuadW * scale, y1 = y0 + QuadH * scale;
                verts.Add(new Vector3(x0, y0));
                verts.Add(new Vector3(x0, y1));
                verts.Add(new Vector3(x1, y1));
                verts.Add(new Vector3(x1, y0));
                uvs.Add(new Vector2(uv.xMin, uv.yMin));
                uvs.Add(new Vector2(uv.xMin, uv.yMax));
                uvs.Add(new Vector2(uv.xMax, uv.yMax));
                uvs.Add(new Vector2(uv.xMax, uv.yMin));
                for (int k = 0; k < 4; k++)
                    colors.Add(color);
                tris.Add(b); tris.Add(b + 1); tris.Add(b + 2);
                tris.Add(b); tris.Add(b + 2); tris.Add(b + 3);
                x += Advance * scale;
            }
        }

        public static float Width(string text, float scale) => (text.Length * Advance - 1) * scale;

        /// <summary>True when every character has a glyph (otherwise use an OS font).</summary>
        public static bool Supports(string text)
        {
            if (atlas == null)
                Build();
            foreach (char ch in text)
            {
                if (ch == '\n')
                    continue;
                char u = ch == 'x' ? ch : char.ToUpperInvariant(ch);
                if (!Index.ContainsKey(u))
                    return false;
            }
            return true;
        }
    }
}
