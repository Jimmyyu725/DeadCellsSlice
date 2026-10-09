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
            float w = PixelFont.Width(text, pixelScale);
            float h = PixelFont.GlyphH * pixelScale;
            float x = alignment switch
            {
                TextAnchor.UpperCenter or TextAnchor.MiddleCenter or TextAnchor.LowerCenter => r.center.x - w * 0.5f,
                TextAnchor.UpperRight or TextAnchor.MiddleRight or TextAnchor.LowerRight => r.xMax - w,
                _ => r.xMin,
            };
            float y = alignment switch
            {
                TextAnchor.UpperLeft or TextAnchor.UpperCenter or TextAnchor.UpperRight => r.yMax - h,
                TextAnchor.LowerLeft or TextAnchor.LowerCenter or TextAnchor.LowerRight => r.yMin,
                _ => r.center.y - h * 0.5f,
            };
            x = Mathf.Round(x);
            y = Mathf.Round(y);
            PixelFont.AppendQuads(text, new Vector2(x, y), pixelScale, color, v, uv, c, t);
            for (int i = 0; i < v.Count; i++)
                vh.AddVert(v[i], c[i], uv[i]);
            for (int i = 0; i < t.Count; i += 3)
                vh.AddTriangle(t[i], t[i + 1], t[i + 2]);
        }
    }
}
