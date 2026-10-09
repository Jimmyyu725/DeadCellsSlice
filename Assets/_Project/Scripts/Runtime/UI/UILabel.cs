using DeadCells.Meta;
using UnityEngine;
using UnityEngine.UI;

namespace DeadCells.UI
{
    /// <summary>
    /// Text that switches renderer by content: the outlined pixel font for
    /// English headings/HUD, an OS font (PingFang on macOS) for Chinese and for
    /// long-form body text. Can bind to a localization key and re-localize when
    /// the language changes.
    /// </summary>
    [RequireComponent(typeof(RectTransform))]
    public class UILabel : MonoBehaviour
    {
        public enum Style
        {
            Pixel,
            Body,
        }

        public Style style = Style.Pixel;
        [SerializeField] float scale = 3f;

        public float pixelScale
        {
            get => scale;
            set
            {
                if (Mathf.Approximately(scale, value))
                    return;
                scale = value;
                if (built)
                    Assign(text, true);
            }
        }
        public int fontSize = 30;
        public TextAnchor alignment = TextAnchor.MiddleLeft;
        public bool wrap;

        string text = "";
        string key;
        object[] args;
        Color color = Color.white;
        PixelText pixel;
        Text body;
        Outline outline;
        bool built;

        static Font cjk, latin;

        public static Font CJKFont => cjk != null ? cjk : cjk = Font.CreateDynamicFontFromOSFont(
            new[] { "PingFang SC", "Hiragino Sans GB", "Heiti SC", "STHeiti", "Microsoft YaHei", "Noto Sans CJK SC", "Arial Unicode MS" }, 32);

        public static Font LatinFont => latin != null ? latin : latin = Font.CreateDynamicFontFromOSFont(
            new[] { "Georgia", "Palatino", "Times New Roman", "Helvetica Neue", "Arial" }, 32);

        public Color Color
        {
            get => color;
            set
            {
                color = value;
                if (pixel != null) pixel.color = value;
                if (body != null) body.color = value;
            }
        }

        public string Text
        {
            get => text;
            set
            {
                key = null;
                Assign(value ?? "");
            }
        }

        public RectTransform RectTransform => (RectTransform)transform;

        /// <summary>Bind to a string-table key (re-localized on language change).</summary>
        public void SetKey(string locKey, params object[] formatArgs)
        {
            key = locKey;
            args = formatArgs;
            Assign(args != null && args.Length > 0 ? Loc.Get(key, args) : Loc.Get(key));
        }

        void OnEnable() => Loc.Changed += Relocalize;
        void OnDisable() => Loc.Changed -= Relocalize;

        void Relocalize()
        {
            if (key != null)
                SetKey(key, args);
            else
                Assign(text, true);
        }

        static bool NeedsOsFont(string s)
        {
            foreach (char ch in s)
                if (ch > 0x2000)
                    return true;
            return false;
        }

        void Build()
        {
            if (built)
                return;
            built = true;
            pixel = Child("Pixel").AddComponent<PixelText>();
            pixel.raycastTarget = false;
            body = Child("Body").AddComponent<Text>();
            body.raycastTarget = false;
            body.horizontalOverflow = HorizontalWrapMode.Wrap;
            body.verticalOverflow = VerticalWrapMode.Overflow;
            body.supportRichText = false;
            outline = body.gameObject.AddComponent<Outline>();
            outline.effectColor = new Color(0.02f, 0.01f, 0.05f, 0.9f);
            outline.effectDistance = new Vector2(2f, -2f);
        }

        GameObject Child(string name)
        {
            var go = new GameObject(name, typeof(RectTransform));
            var rt = (RectTransform)go.transform;
            rt.SetParent(transform, false);
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = rt.offsetMax = Vector2.zero;
            return go;
        }

        void Assign(string value, bool force = false)
        {
            Build();
            if (!force && value == text && (pixel.enabled || body.enabled))
                return;
            text = value;
            bool osFont = style == Style.Body || NeedsOsFont(value) || !PixelFont.Supports(value);
            pixel.enabled = !osFont;
            body.enabled = osFont;
            if (osFont)
            {
                bool chinese = NeedsOsFont(value) || Loc.IsChinese;
                body.font = chinese ? CJKFont : LatinFont;
                body.fontSize = style == Style.Body ? fontSize : Mathf.RoundToInt(pixelScale * 8.5f);
                body.fontStyle = style == Style.Pixel ? FontStyle.Bold : FontStyle.Normal;
                body.alignment = alignment;
                body.horizontalOverflow = wrap || style == Style.Body ? HorizontalWrapMode.Wrap : HorizontalWrapMode.Overflow;
                body.lineSpacing = chinese ? 1.25f : 1.1f;
                body.color = color;
                body.text = value;
                pixel.Text = "";
            }
            else
            {
                pixel.pixelScale = pixelScale;
                pixel.alignment = alignment;
                pixel.wrap = wrap;
                pixel.color = color;
                pixel.Text = value;
                body.text = "";
            }
        }

        public float PreferredHeight
        {
            get
            {
                Build();
                if (pixel.enabled)
                    return pixel.PreferredHeight;
                return body.preferredHeight;
            }
        }
    }
}
