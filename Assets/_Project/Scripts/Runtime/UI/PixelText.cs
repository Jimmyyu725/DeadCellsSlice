using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace DeadCells.UI
{
    /// <summary>uGUI graphic that draws text with the PixelFont atlas (crisp, outlined).</summary>
    public class PixelText : MaskableGraphic
    {
        [SerializeField] string text = "";
        [Tooltip("Screen pixels per font texel.")]
        public float pixelScale = 3f;
        public TextAnchor alignment = TextAnchor.MiddleLeft;
        [Tooltip("Wrap words to the rect width; '\\n' always breaks.")]
        public bool wrap;
        public float lineSpacing = 3f;

        readonly List<Vector3> v = new List<Vector3>();
        readonly List<Vector2> uv = new List<Vector2>();
        readonly List<Color32> c = new List<Color32>();
        readonly List<int> t = new List<int>();

        public override Texture mainTexture => PixelFont.Atlas;

        public string Text
        {
            get => text;
            set
            {
                if (text == value)
                    return;
                text = value;
                SetVerticesDirty();
            }
        }

        readonly List<string> lines = new List<string>();

        void Layout(float width)
        {
            lines.Clear();
            foreach (var para in text.Split('\n'))
            {
                if (!wrap)
                {
                    lines.Add(para);
                    continue;
                }
                string line = "";
                foreach (var word in para.Split(' '))
                {
                    string candidate = line.Length == 0 ? word : line + " " + word;
                    if (line.Length > 0 && PixelFont.Width(candidate, pixelScale) > width)
                    {
                        lines.Add(line);
                        line = word;
                    }
                    else
                    {
                        line = candidate;
                    }
                }
                lines.Add(line);
            }
        }

        public float PreferredHeight
        {
            get
            {
                Layout(rectTransform.rect.width);
                return lines.Count * (PixelFont.GlyphH + lineSpacing) * pixelScale - lineSpacing * pixelScale;
            }
        }

        protected override void OnPopulateMesh(VertexHelper vh)
        {
            vh.Clear();
            if (string.IsNullOrEmpty(text))
                return;
            v.Clear();
            uv.Clear();
            c.Clear();
            t.Clear();
            Rect r = rectTransform.rect;
            Layout(r.width);
            float lineH = (PixelFont.GlyphH + lineSpacing) * pixelScale;
            float h = lines.Count * lineH - lineSpacing * pixelScale;
            float top = alignment switch
            {
                TextAnchor.UpperLeft or TextAnchor.UpperCenter or TextAnchor.UpperRight => r.yMax,
                TextAnchor.LowerLeft or TextAnchor.LowerCenter or TextAnchor.LowerRight => r.yMin + h,
                _ => r.center.y + h * 0.5f,
            };
            for (int i = 0; i < lines.Count; i++)
            {
                string line = lines[i];
                if (line.Length == 0)
                    continue;
                float w = PixelFont.Width(line, pixelScale);
                float x = alignment switch
                {
                    TextAnchor.UpperCenter or TextAnchor.MiddleCenter or TextAnchor.LowerCenter => r.center.x - w * 0.5f,
                    TextAnchor.UpperRight or TextAnchor.MiddleRight or TextAnchor.LowerRight => r.xMax - w,
                    _ => r.xMin,
                };
                float y = top - (i + 1) * lineH + lineSpacing * pixelScale;
                PixelFont.AppendQuads(line, new Vector2(Mathf.Round(x), Mathf.Round(y)), pixelScale, color, v, uv, c, t);
            }
            for (int i = 0; i < v.Count; i++)
                vh.AddVert(v[i], c[i], uv[i]);
            for (int i = 0; i < t.Count; i += 3)
                vh.AddTriangle(t[i], t[i + 1], t[i + 2]);
        }
    }
}
