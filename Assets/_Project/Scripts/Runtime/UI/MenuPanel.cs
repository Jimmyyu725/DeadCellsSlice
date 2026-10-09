using System;
using System.Collections.Generic;
using DeadCells.Core;
using DeadCells.Meta;
using UnityEngine;
using UnityEngine.UI;

namespace DeadCells.UI
{
    public class MenuItem
    {
        public Func<string> label;
        public Func<string> value;
        public Action confirm;
        public Action<int> change;
        public Func<bool> enabled;
        public Func<string> description;
        public Func<Color?> tint;

        public bool Enabled => enabled == null || enabled();

        public static MenuItem Button(Func<string> label, Action confirm, Func<string> description = null, Func<bool> enabled = null) =>
            new MenuItem { label = label, confirm = confirm, description = description, enabled = enabled };

        public static MenuItem Option(Func<string> label, Func<string> value, Action<int> change, Func<string> description = null) =>
            new MenuItem { label = label, value = value, change = change, confirm = () => change(1), description = description };

        public static MenuItem Info(Func<string> label, Func<string> value = null, Func<string> description = null, Func<Color?> tint = null) =>
            new MenuItem { label = label, value = value, description = description, tint = tint };
    }

    public class MenuPage
    {
        public Func<string> title;
        public Func<string> body;
        public readonly List<MenuItem> items = new List<MenuItem>();
        public int selected;
        public Action onBack;
        public bool canBack = true;
        public int visibleRows = 9;
        public Action<MenuPage> onUpdate;

        public MenuPage Add(MenuItem item)
        {
            items.Add(item);
            return this;
        }
    }

    /// <summary>
    /// Stack of keyboard/gamepad/mouse-driven text menus in the Dead Cells
    /// style (left column, pixel-font rows, description footer).
    /// </summary>
    public class MenuPanel : MonoBehaviour
    {
        const int MaxRows = 12;
        const float RowH = 54f;

        readonly List<MenuPage> stack = new List<MenuPage>();
        Canvas canvas;
        Image dim, column;
        UILabel title, body, footer, hint, scrollUp, scrollDown;
        RectTransform rowsRoot;
        readonly List<(RectTransform rt, Image bar, UILabel label, UILabel value)> rows = new List<(RectTransform, Image, UILabel, UILabel)>();
        int scroll;
        float openedAt;

        public bool IsOpen => stack.Count > 0;
        public MenuPage Top => stack.Count > 0 ? stack[stack.Count - 1] : null;
        public bool dimBackground = true;
        public event Action Closed;

        public static MenuPanel Create(string name, int order, Transform parent = null)
        {
            var c = UIKit.Canvas(name, order, parent);
            var panel = c.gameObject.AddComponent<MenuPanel>();
            panel.canvas = c;
            panel.Build();
            panel.canvas.enabled = false;
            return panel;
        }

        void Build()
        {
            Transform root = canvas.transform;
            dim = UIKit.Fill("Dim", root, new Color(0f, 0f, 0f, 0.55f));
            column = UIKit.Box("Column", root, new Vector2(0f, 0.5f), new Vector2(0f, 0f), new Vector2(860f, 2400f), UIKit.Panel, new Vector2(0f, 0.5f));
            UIKit.Box("ColumnEdge", column.transform, new Vector2(1f, 0.5f), Vector2.zero, new Vector2(3f, 2400f), new Color(0.35f, 0.22f, 0.55f, 0.8f), new Vector2(1f, 0.5f));
            title = UIKit.Label("Title", root, new Vector2(0f, 1f), new Vector2(120f, -110f), new Vector2(720f, 80f), TextAnchor.MiddleLeft, UIKit.TextBright, 6f);
            body = UIKit.Label("Body", root, new Vector2(0f, 1f), new Vector2(120f, -200f), new Vector2(680f, 220f), TextAnchor.UpperLeft, UIKit.TextDim, UIKit.U, UILabel.Style.Body, 28);
            rowsRoot = UIKit.Rect("Rows", root, new Vector2(0f, 1f), new Vector2(120f, -300f), new Vector2(700f, MaxRows * RowH), new Vector2(0f, 1f));
            for (int i = 0; i < MaxRows; i++)
            {
                var rt = UIKit.Rect("Row" + i, rowsRoot, new Vector2(0f, 1f), new Vector2(0f, -i * RowH), new Vector2(700f, RowH - 6f), new Vector2(0f, 1f));
                var bar = UIKit.Box("Bar", rt, new Vector2(0f, 0.5f), new Vector2(-14f, 0f), new Vector2(714f, RowH - 6f), new Color(0.45f, 0.25f, 0.8f, 0.35f), new Vector2(0f, 0.5f));
                var label = UIKit.Label("Label", rt, new Vector2(0f, 0.5f), new Vector2(10f, 0f), new Vector2(460f, RowH - 6f), TextAnchor.MiddleLeft, UIKit.TextBright, 4f, UILabel.Style.Pixel, 30, new Vector2(0f, 0.5f));
                var value = UIKit.Label("Value", rt, new Vector2(1f, 0.5f), new Vector2(-6f, 0f), new Vector2(300f, RowH - 6f), TextAnchor.MiddleRight, UIKit.Gold, 4f, UILabel.Style.Pixel, 30, new Vector2(1f, 0.5f));
                rows.Add((rt, bar, label, value));
            }
            scrollUp = UIKit.Label("ScrollUp", rowsRoot, new Vector2(0f, 1f), new Vector2(330f, 30f), new Vector2(60f, 30f), TextAnchor.MiddleCenter, UIKit.TextDim, 3f);
            scrollUp.Text = "^";
            scrollDown = UIKit.Label("ScrollDown", rowsRoot, new Vector2(0f, 1f), new Vector2(330f, 0f), new Vector2(60f, 30f), TextAnchor.MiddleCenter, UIKit.TextDim, 3f);
            scrollDown.Text = "v";
            footer = UIKit.Label("Footer", root, new Vector2(0f, 0f), new Vector2(120f, 120f), new Vector2(680f, 160f), TextAnchor.LowerLeft, UIKit.TextDim, UIKit.U, UILabel.Style.Body, 26);
            hint = UIKit.Label("Hint", root, new Vector2(0f, 0f), new Vector2(120f, 50f), new Vector2(700f, 30f), TextAnchor.MiddleLeft, new Color(0.5f, 0.55f, 0.62f), 2f);
        }

        public void Push(MenuPage page)
        {
            stack.Add(page);
            canvas.enabled = true;
            scroll = 0;
            openedAt = Time.unscaledTime;
            ClampSelection(page, 0);
            Refresh();
        }

        public void Pop()
        {
            if (stack.Count == 0)
                return;
            stack.RemoveAt(stack.Count - 1);
            if (stack.Count == 0)
            {
                canvas.enabled = false;
                Closed?.Invoke();
            }
            else
            {
                Refresh();
            }
        }

        public void ReplaceTop(MenuPage page)
        {
            if (stack.Count > 0)
                stack.RemoveAt(stack.Count - 1);
            Push(page);
        }

        public void CloseAll()
        {
            bool was = stack.Count > 0;
            stack.Clear();
            canvas.enabled = false;
            if (was)
                Closed?.Invoke();
        }

        /// <summary>Yes/No confirmation page.</summary>
        public void Confirm(Func<string> question, Action yes)
        {
            var page = new MenuPage { title = () => "", body = question };
            page.Add(MenuItem.Button(() => Loc.Get("menu.no"), Pop));
            page.Add(MenuItem.Button(() => Loc.Get("menu.yes"), () =>
            {
                Pop();
                yes();
            }));
            Push(page);
        }

        static void ClampSelection(MenuPage page, int dir)
        {
            if (page.items.Count == 0)
                return;
            page.selected = Mathf.Clamp(page.selected, 0, page.items.Count - 1);
            // Skip pure info rows only when they have no action and others exist.
            for (int guard = 0; guard < page.items.Count; guard++)
            {
                var it = page.items[page.selected];
                bool actionable = it.confirm != null || it.change != null || it.description != null;
                if (actionable || dir == 0)
                    break;
                page.selected = (page.selected + dir + page.items.Count) % page.items.Count;
            }
        }

        void Update()
        {
            var page = Top;
            if (page == null)
                return;
            page.onUpdate?.Invoke(page);
            if (Top != page)
                return;
            // Ignore the key press that opened this page.
            bool live = Time.unscaledTime - openedAt > 0.05f;
            if (live)
                HandleInput(page);
            if (Top == page)
                Refresh();
        }

        void HandleInput(MenuPage page)
        {
            int n = page.items.Count;
            if (n > 0)
            {
                if (MenuInput.Up)
                {
                    page.selected = (page.selected - 1 + n) % n;
                    ClampSelection(page, -1);
                }
                if (MenuInput.Down)
                {
                    page.selected = (page.selected + 1) % n;
                    ClampSelection(page, 1);
                }
                var item = page.items[page.selected];
                if (item.Enabled && item.change != null)
                {
                    if (MenuInput.Left) item.change(-1);
                    if (MenuInput.Right) item.change(1);
                }
                // Mouse hover / click.
                Vector2 mouse = MenuInput.MousePosition;
                for (int i = 0; i < rows.Count; i++)
                {
                    int idx = scroll + i;
                    if (idx >= n || !UIKit.Contains(rows[i].rt, mouse))
                        continue;
                    if (MenuInput.MouseMoved)
                        page.selected = idx;
                    if (MenuInput.MouseClicked)
                    {
                        page.selected = idx;
                        var clicked = page.items[idx];
                        if (clicked.Enabled)
                            clicked.confirm?.Invoke();
                        return;
                    }
                }
                if (MenuInput.Confirm && item.Enabled && item.confirm != null)
                {
                    item.confirm();
                    return;
                }
            }
            else if (MenuInput.Confirm && page.onBack != null)
            {
                page.onBack();
                return;
            }
            if (MenuInput.Cancel && page.canBack)
            {
                if (page.onBack != null)
                    page.onBack();
                else
                    Pop();
            }
        }

        void Refresh()
        {
            var page = Top;
            if (page == null)
                return;
            dim.enabled = dimBackground;
            title.Text = page.title != null ? page.title() : "";
            string b = page.body != null ? page.body() : "";
            body.Text = b;
            float bodyH = string.IsNullOrEmpty(b) ? 0f : Mathf.Max(40f, body.PreferredHeight) + 30f;
            rowsRoot.anchoredPosition = new Vector2(120f, -200f - bodyH);

            int n = page.items.Count;
            int visible = Mathf.Min(page.visibleRows, MaxRows);
            if (page.selected < scroll) scroll = page.selected;
            if (page.selected >= scroll + visible) scroll = page.selected - visible + 1;
            scroll = Mathf.Clamp(scroll, 0, Mathf.Max(0, n - visible));
            for (int i = 0; i < rows.Count; i++)
            {
                int idx = scroll + i;
                var row = rows[i];
                bool show = i < visible && idx < n;
                row.rt.gameObject.SetActive(show);
                if (!show)
                    continue;
                var it = page.items[idx];
                bool sel = idx == page.selected;
                bool en = it.Enabled;
                string label = it.label != null ? it.label() : "";
                string v = it.value != null ? it.value() : "";
                string shownValue = it.change != null && sel && en ? "< " + v + " >" : v;
                // Shrink the pixel font until label and value both fit the row.
                float valueW = PixelFont.Width(shownValue, 4f) + 24f;
                float room = 690f - valueW;
                float scale = 4f;
                while (scale > 2f && PixelFont.Width((sel ? "> " : "") + label, scale) > room)
                    scale -= 0.5f;
                row.label.pixelScale = scale;
                row.label.RectTransform.sizeDelta = new Vector2(Mathf.Max(120f, room), RowH - 6f);
                row.label.Text = sel ? "> " + label : label;
                Color c = en ? (sel ? UIKit.TextBright : new Color(0.7f, 0.74f, 0.8f)) : new Color(0.38f, 0.4f, 0.45f);
                var tint = it.tint?.Invoke();
                if (tint.HasValue)
                    c = sel ? Color.Lerp(tint.Value, Color.white, 0.3f) : tint.Value;
                row.label.Color = c;
                row.value.Text = shownValue;
                row.value.Color = en ? UIKit.Gold : new Color(0.45f, 0.42f, 0.35f);
                row.bar.enabled = sel;
            }
            scrollUp.gameObject.SetActive(scroll > 0);
            scrollDown.gameObject.SetActive(scroll + visible < n);
            scrollDown.RectTransform.anchoredPosition = new Vector2(330f, -visible * RowH - 6f);
            var selItem = n > 0 ? page.items[Mathf.Clamp(page.selected, 0, n - 1)] : null;
            footer.Text = selItem?.description != null ? selItem.description() : "";
            hint.Text = Loc.Get("menu.nav_hint");
        }
    }
}
