using UnityEngine;
using UnityEngine.UI;

namespace DeadCells.UI
{
    /// <summary>Code-built uGUI helpers shared by the HUD and every menu.</summary>
    public static class UIKit
    {
        public const float U = 3f; // screen pixels per UI "texel" at 1080p
        public static readonly Color Ink = new Color(0.02f, 0.03f, 0.05f, 0.92f);
        public static readonly Color Panel = new Color(0.03f, 0.04f, 0.07f, 0.86f);
        public static readonly Color Accent = new Color(0.62f, 0.38f, 0.95f, 1f);
        public static readonly Color Gold = new Color(1f, 0.82f, 0.32f, 1f);
        public static readonly Color CellBlue = new Color(0.45f, 0.88f, 1f, 1f);
        public static readonly Color TextDim = new Color(0.62f, 0.68f, 0.75f, 1f);
        public static readonly Color TextBright = new Color(0.95f, 0.97f, 1f, 1f);

        static Sprite white;

        public static Sprite White
        {
            get
            {
                if (white == null)
                {
                    var tex = new Texture2D(1, 1) { filterMode = FilterMode.Point, hideFlags = HideFlags.DontSave };
                    tex.SetPixel(0, 0, Color.white);
                    tex.Apply();
                    white = Sprite.Create(tex, new Rect(0, 0, 1, 1), new Vector2(0.5f, 0.5f), 1f);
                }
                return white;
            }
        }

        public static Canvas Canvas(string name, int order, Transform parent = null)
        {
            var go = new GameObject(name, typeof(Canvas), typeof(CanvasScaler));
            if (parent != null)
                go.transform.SetParent(parent, false);
            var canvas = go.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.pixelPerfect = true;
            canvas.sortingOrder = order;
            var scaler = go.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.matchWidthOrHeight = 1f;
            return canvas;
        }

        public static RectTransform Rect(string name, Transform parent, Vector2 anchor, Vector2 pos, Vector2 size, Vector2? pivot = null)
        {
            var go = new GameObject(name, typeof(RectTransform));
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.anchorMin = rt.anchorMax = anchor;
            rt.pivot = pivot ?? anchor;
            rt.anchoredPosition = pos;
            rt.sizeDelta = size;
            return rt;
        }

        public static RectTransform Stretch(string name, Transform parent, float inset = 0f)
        {
            var go = new GameObject(name, typeof(RectTransform));
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = new Vector2(inset, inset);
            rt.offsetMax = new Vector2(-inset, -inset);
            return rt;
        }

        public static Image Box(string name, Transform parent, Vector2 anchor, Vector2 pos, Vector2 size, Color color, Vector2? pivot = null)
        {
            var img = Rect(name, parent, anchor, pos, size, pivot).gameObject.AddComponent<Image>();
            img.sprite = White;
            img.color = color;
            img.raycastTarget = false;
            return img;
        }

        public static Image Fill(string name, Transform parent, Color color, float inset = 0f)
        {
            var img = Stretch(name, parent, inset).gameObject.AddComponent<Image>();
            img.sprite = White;
            img.color = color;
            img.raycastTarget = false;
            return img;
        }

        public static UILabel Label(string name, Transform parent, Vector2 anchor, Vector2 pos, Vector2 size, TextAnchor align, Color color,
            float pixelScale = U, UILabel.Style style = UILabel.Style.Pixel, int fontSize = 30, Vector2? pivot = null)
        {
            var rt = Rect(name, parent, anchor, pos, size, pivot);
            var l = rt.gameObject.AddComponent<UILabel>();
            l.style = style;
            l.pixelScale = pixelScale;
            l.fontSize = fontSize;
            l.alignment = align;
            l.Color = color;
            return l;
        }

        /// <summary>1-texel dark frame around a rect (Dead Cells panels).</summary>
        public static void Frame(Transform target, Color color, float thickness = U)
        {
            var rt = (RectTransform)target;
            foreach (var (a0, a1, off0, off1) in new[]
                     {
                         (new Vector2(0, 1), new Vector2(1, 1), new Vector2(-thickness, 0), new Vector2(thickness, thickness)),
                         (new Vector2(0, 0), new Vector2(1, 0), new Vector2(-thickness, -thickness), new Vector2(thickness, 0)),
                         (new Vector2(0, 0), new Vector2(0, 1), new Vector2(-thickness, 0), new Vector2(0, 0)),
                         (new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 0), new Vector2(thickness, 0)),
                     })
            {
                var go = new GameObject("Frame", typeof(RectTransform), typeof(Image));
                var r = (RectTransform)go.transform;
                r.SetParent(rt, false);
                r.anchorMin = a0;
                r.anchorMax = a1;
                r.offsetMin = off0;
                r.offsetMax = off1;
                var img = go.GetComponent<Image>();
                img.sprite = White;
                img.color = color;
                img.raycastTarget = false;
            }
        }

        public static bool Contains(RectTransform rt, Vector2 screenPoint) =>
            rt != null && rt.gameObject.activeInHierarchy && RectTransformUtility.RectangleContainsScreenPoint(rt, screenPoint, null);

        public static string FormatTime(float seconds)
        {
            int s = Mathf.Max(0, Mathf.FloorToInt(seconds));
            return s >= 3600 ? $"{s / 3600}:{s / 60 % 60:00}:{s % 60:00}" : $"{s / 60}:{s % 60:00}";
        }
    }
}
