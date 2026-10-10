using System.Collections.Generic;
using DeadCells.Combat;
using DeadCells.Enemies;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.Run;
using UnityEngine;
using UnityEngine.UI;

namespace DeadCells.UI
{
    /// <summary>
    /// Dead Cells-style HUD built in code: health bar with a damage trail and
    /// flask charges, four equipment slots with icons and cooldowns, gold and
    /// cells, minimap with the area name and run timer, boss bar, the
    /// interaction prompt with an item card, toasts and achievement pop-ups,
    /// area title cards, damage vignette and the fade overlay.
    /// </summary>
    public class GameHUD : MonoBehaviour
    {
        public PlayerController player;
        public float uiScale = 3f;

        public static GameHUD Instance { get; private set; }

        Health health;
        PlayerCombat combat;
        RectTransform root;
        RectTransform fill, trail, recover;
        UILabel statB, statT, statS, curseText, mutationText;
        Image amuletIcon, amuletFrame, packIcon, packFrame;
        UILabel cardAffix;
        UILabel hpText, goldText, cellsText, timerText, areaText, flaskText, coordText;
        Image damageOverlay, fadeOverlay, goldIcon, cellIcon;
        readonly Image[] slotFrame = new Image[4];
        readonly Image[] slotIcon = new Image[4];
        readonly Image[] slotCooldown = new Image[4];
        readonly UILabel[] slotKey = new UILabel[4];
        readonly UILabel[] slotTimer = new UILabel[4];
        RawImage minimap;
        RectTransform minimapMarkers;
        readonly List<Image> markerPool = new List<Image>();
        RectTransform bossRoot, bossFill;
        UILabel bossName;
        EnemyBase boss;
        RectTransform promptRoot;
        UILabel promptText, cardTitle, cardKind, cardStats, cardDesc, cardPrice;
        Image cardIcon;
        RectTransform cardRoot;
        RectTransform toastRoot;
        readonly List<(UILabel label, float until)> toasts = new List<(UILabel, float)>();
        RectTransform achRoot;
        UILabel achName;
        Image achIcon;
        float achUntil;
        UILabel titleText, subtitleText;
        float titleUntil, titleStart;
        float trailValue = 1f;
        float trailHold;
        float damagePulse;
        float fadeTarget, fadeValue;
        float goldPulse, cellPulse;

        static readonly Color[] KindColor =
        {
            new Color(0.62f, 0.16f, 0.14f, 1f), // melee
            new Color(0.2f, 0.5f, 0.24f, 1f),   // shield
            new Color(0.42f, 0.22f, 0.66f, 1f), // bow
            new Color(0.2f, 0.36f, 0.66f, 1f),  // skill
        };

        void Awake()
        {
            Instance = this;
            Build();
        }

        void Start()
        {
            if (player != null)
            {
                health = player.Health;
                combat = player.GetComponent<PlayerCombat>();
                health.Damaged += (_, result) =>
                {
                    if (result != DamageResult.Parried && result != DamageResult.Blocked)
                        damagePulse = 1f;
                    trailHold = 0.45f;
                };
                if (combat != null)
                    combat.SlotsChanged += RefreshSlots;
            }
            Achievements.Unlocked += OnAchievement;
            Loc.Changed += RefreshSlots;
            RefreshSlots();
        }

        void OnDestroy()
        {
            if (Instance == this)
                Instance = null;
            Achievements.Unlocked -= OnAchievement;
            Loc.Changed -= RefreshSlots;
        }

        // --------------------------------------------------------------- build

        void Build()
        {
            var canvas = UIKit.Canvas("HUDCanvas", 100, transform);
            root = (RectTransform)canvas.transform;
            hudGroup = canvas.gameObject.AddComponent<CanvasGroup>();
            hudGroup.interactable = false;
            hudGroup.blocksRaycasts = false;
            float u = uiScale;

            damageOverlay = UIKit.Fill("DamageOverlay", root, new Color(0.6f, 0f, 0.05f, 0f));

            // Health bar + flask (bottom-left).
            Vector2 bl = Vector2.zero;
            UIKit.Box("HPFrame", root, bl, new Vector2(18 * u, 10 * u), new Vector2(132 * u, 9 * u), UIKit.Ink);
            UIKit.Box("HPBack", root, bl, new Vector2(19 * u, 11 * u), new Vector2(130 * u, 7 * u), new Color(0.08f, 0.12f, 0.12f, 1f));
            trail = UIKit.Box("HPTrail", root, bl, new Vector2(19 * u, 11 * u), new Vector2(130 * u, 7 * u), new Color(0.85f, 0.25f, 0.2f, 1f)).rectTransform;
            recover = UIKit.Box("HPRecover", root, bl, new Vector2(19 * u, 11 * u), new Vector2(130 * u, 7 * u), new Color(1f, 0.55f, 0.15f, 1f)).rectTransform;
            fill = UIKit.Box("HPFill", root, bl, new Vector2(19 * u, 11 * u), new Vector2(130 * u, 7 * u), new Color(0.18f, 0.78f, 0.38f, 1f)).rectTransform;
            var shine = UIKit.Box("HPShine", fill, new Vector2(0f, 1f), Vector2.zero, new Vector2(0f, 2 * u), new Color(0.6f, 1f, 0.7f, 0.45f)).rectTransform;
            shine.anchorMin = new Vector2(0f, 1f);
            shine.anchorMax = new Vector2(1f, 1f);
            shine.pivot = new Vector2(0.5f, 1f);
            shine.sizeDelta = new Vector2(0f, 2 * u);
            hpText = UIKit.Label("HPText", root, bl, new Vector2(19 * u, 11 * u), new Vector2(130 * u, 7 * u), TextAnchor.MiddleCenter, Color.white, 2f);
            var flaskIcon = UIKit.Box("FlaskIcon", root, bl, new Vector2(153 * u, 8 * u), new Vector2(12 * u, 12 * u), Color.white);
            flaskIcon.sprite = PixelIcons.Get("flask");
            flaskText = UIKit.Label("Flask", root, bl, new Vector2(166 * u, 10 * u), new Vector2(30 * u, 8 * u), TextAnchor.MiddleLeft, new Color(0.7f, 1f, 0.7f), 2.5f);

            // Equipment slots above the bar.
            string[] keys = { "J", "K", "Q", "E" };
            for (int i = 0; i < 4; i++)
            {
                var pos = new Vector2((18 + i * 24 + (i >= 2 ? 6 : 0)) * u, 23 * u);
                slotFrame[i] = UIKit.Box("Slot" + i, root, bl, pos, new Vector2(21 * u, 21 * u), UIKit.Ink);
                var inner = UIKit.Box("SlotInner" + i, slotFrame[i].transform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(19 * u, 19 * u), new Color(0.07f, 0.08f, 0.12f, 1f));
                slotIcon[i] = UIKit.Box("Icon" + i, inner.transform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(16 * u, 16 * u), Color.white);
                slotCooldown[i] = UIKit.Box("Cooldown" + i, inner.transform, new Vector2(0.5f, 0f), Vector2.zero, new Vector2(19 * u, 19 * u), new Color(0f, 0f, 0f, 0.68f), new Vector2(0.5f, 0f));
                slotCooldown[i].type = Image.Type.Filled;
                slotCooldown[i].fillMethod = Image.FillMethod.Vertical;
                slotCooldown[i].fillOrigin = 0;
                slotTimer[i] = UIKit.Label("Timer" + i, inner.transform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(19 * u, 19 * u), TextAnchor.MiddleCenter, Color.white, 2f);
                slotKey[i] = UIKit.Label("Key" + i, slotFrame[i].transform, new Vector2(1f, 0f), new Vector2(-1 * u, 1 * u), new Vector2(8 * u, 7 * u), TextAnchor.LowerRight, new Color(0.85f, 0.9f, 0.95f), 2f, UILabel.Style.Pixel, 30, new Vector2(1f, 0f));
                slotKey[i].Text = keys[i];
            }

            // Amulet + backpack beside the slots, scroll levels and curse above them.
            amuletFrame = UIKit.Box("AmuletSlot", root, bl, new Vector2(122 * u, 23 * u), new Vector2(15 * u, 15 * u), UIKit.Ink);
            UIKit.Box("AmuletInner", amuletFrame.transform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(13 * u, 13 * u), new Color(0.07f, 0.08f, 0.12f, 1f));
            amuletIcon = UIKit.Box("AmuletIcon", amuletFrame.transform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(12 * u, 12 * u), Color.white);
            packFrame = UIKit.Box("PackSlot", root, bl, new Vector2(139 * u, 23 * u), new Vector2(15 * u, 15 * u), UIKit.Ink);
            UIKit.Box("PackInner", packFrame.transform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(13 * u, 13 * u), new Color(0.07f, 0.08f, 0.12f, 1f));
            packIcon = UIKit.Box("PackIcon", packFrame.transform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(12 * u, 12 * u), new Color(1f, 1f, 1f, 0.6f));
            var packKey = UIKit.Label("PackKey", packFrame.transform, new Vector2(1f, 0f), new Vector2(-1 * u, 1 * u), new Vector2(8 * u, 6 * u), TextAnchor.LowerRight, new Color(0.85f, 0.9f, 0.95f), 1.5f, UILabel.Style.Pixel, 30, new Vector2(1f, 0f));
            packKey.Text = "C";
            statB = UIKit.Label("StatB", root, bl, new Vector2(18 * u, 46 * u), new Vector2(20 * u, 7 * u), TextAnchor.MiddleLeft, ScrollPickup.Tint(ItemColor.Brutality), 2.5f);
            statT = UIKit.Label("StatT", root, bl, new Vector2(38 * u, 46 * u), new Vector2(20 * u, 7 * u), TextAnchor.MiddleLeft, ScrollPickup.Tint(ItemColor.Tactics), 2.5f);
            statS = UIKit.Label("StatS", root, bl, new Vector2(58 * u, 46 * u), new Vector2(20 * u, 7 * u), TextAnchor.MiddleLeft, ScrollPickup.Tint(ItemColor.Survival), 2.5f);
            curseText = UIKit.Label("Curse", root, bl, new Vector2(80 * u, 46 * u), new Vector2(80 * u, 7 * u), TextAnchor.MiddleLeft, new Color(0.85f, 0.45f, 1f), 2.5f);
            mutationText = UIKit.Label("Mutations", root, bl, new Vector2(18 * u, 54 * u), new Vector2(200 * u, 7 * u), TextAnchor.MiddleLeft, new Color(0.75f, 0.85f, 0.75f, 0.85f), 2f, UILabel.Style.Body, 22);

            // Gold + cells (bottom-right).
            Vector2 br = new Vector2(1f, 0f);
            goldIcon = UIKit.Box("GoldIcon", root, br, new Vector2(-70 * u, 20 * u), new Vector2(9 * u, 9 * u), Color.white, new Vector2(1f, 0f));
            goldIcon.sprite = PixelIcons.Get("gold");
            goldText = UIKit.Label("Gold", root, br, new Vector2(-18 * u, 21 * u), new Vector2(50 * u, 8 * u), TextAnchor.MiddleLeft, UIKit.Gold, 3f, UILabel.Style.Pixel, 30, new Vector2(1f, 0f));
            cellIcon = UIKit.Box("CellIcon", root, br, new Vector2(-70 * u, 9 * u), new Vector2(9 * u, 9 * u), Color.white, new Vector2(1f, 0f));
            cellIcon.sprite = PixelIcons.Get("cell");
            cellsText = UIKit.Label("Cells", root, br, new Vector2(-18 * u, 10 * u), new Vector2(50 * u, 8 * u), TextAnchor.MiddleLeft, UIKit.CellBlue, 3f, UILabel.Style.Pixel, 30, new Vector2(1f, 0f));

            // Minimap + area + timer (top-right).
            Vector2 tr = Vector2.one;
            var mapFrame = UIKit.Box("MinimapFrame", root, tr, new Vector2(-12 * u, -12 * u), new Vector2(92 * u, 56 * u), UIKit.Ink, Vector2.one);
            minimap = UIKit.Rect("Minimap", mapFrame.transform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(90 * u, 54 * u)).gameObject.AddComponent<RawImage>();
            minimap.raycastTarget = false;
            minimap.color = new Color(1f, 1f, 1f, 0.92f);
            minimapMarkers = UIKit.Rect("Markers", minimap.transform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(90 * u, 54 * u));
            areaText = UIKit.Label("Area", root, tr, new Vector2(-12 * u, -71 * u), new Vector2(160 * u, 8 * u), TextAnchor.MiddleRight, new Color(0.8f, 0.85f, 0.95f), 2f, UILabel.Style.Pixel, 30, Vector2.one);
            timerText = UIKit.Label("Timer", root, tr, new Vector2(-12 * u, -80 * u), new Vector2(80 * u, 8 * u), TextAnchor.MiddleRight, new Color(0.7f, 0.75f, 0.8f, 0.85f), 2f, UILabel.Style.Pixel, 30, Vector2.one);
            coordText = UIKit.Label("Coords", root, tr, new Vector2(-12 * u, -89 * u), new Vector2(300 * u, 16 * u), TextAnchor.UpperRight, new Color(0.55f, 1f, 0.75f), 2f, UILabel.Style.Pixel, 30, Vector2.one);
            coordText.gameObject.SetActive(false);

            // Boss bar (top-centre).
            bossRoot = UIKit.Rect("Boss", root, new Vector2(0.5f, 1f), new Vector2(0f, -14 * u), new Vector2(220 * u, 16 * u), new Vector2(0.5f, 1f));
            bossName = UIKit.Label("BossName", bossRoot, new Vector2(0.5f, 1f), Vector2.zero, new Vector2(220 * u, 7 * u), TextAnchor.MiddleCenter, new Color(1f, 0.85f, 0.75f), 2.5f, UILabel.Style.Pixel, 30, new Vector2(0.5f, 1f));
            UIKit.Box("BossFrame", bossRoot, new Vector2(0.5f, 0f), Vector2.zero, new Vector2(220 * u, 6 * u), UIKit.Ink, new Vector2(0.5f, 0f));
            bossFill = UIKit.Box("BossFill", bossRoot, new Vector2(0f, 0f), new Vector2(1 * u, 1 * u), new Vector2(218 * u, 4 * u), new Color(0.85f, 0.2f, 0.18f), Vector2.zero).rectTransform;
            bossRoot.gameObject.SetActive(false);

            // Interaction prompt + item card (bottom-centre).
            promptRoot = UIKit.Rect("Prompt", root, new Vector2(0.5f, 0f), new Vector2(0f, 64 * u), new Vector2(240 * u, 10 * u), new Vector2(0.5f, 0f));
            UIKit.Fill("PromptBack", promptRoot, new Color(0f, 0f, 0f, 0.55f));
            promptText = UIKit.Label("PromptText", promptRoot, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(236 * u, 8 * u), TextAnchor.MiddleCenter, Color.white, 2.5f);
            // Card sits above the player (the camera keeps the player just below centre).
            cardRoot = UIKit.Rect("Card", root, new Vector2(0.5f, 0.5f), new Vector2(0f, 26 * u), new Vector2(170 * u, 54 * u), new Vector2(0.5f, 0f));
            UIKit.Fill("CardBack", cardRoot, new Color(0.04f, 0.05f, 0.08f, 0.92f));
            UIKit.Frame(cardRoot, new Color(0.35f, 0.25f, 0.5f, 1f), u);
            cardIcon = UIKit.Box("CardIcon", cardRoot, new Vector2(0f, 1f), new Vector2(4 * u, -4 * u), new Vector2(18 * u, 18 * u), Color.white, new Vector2(0f, 1f));
            cardTitle = UIKit.Label("CardTitle", cardRoot, new Vector2(0f, 1f), new Vector2(26 * u, -4 * u), new Vector2(140 * u, 8 * u), TextAnchor.UpperLeft, Color.white, 2.5f, UILabel.Style.Pixel, 30, new Vector2(0f, 1f));
            cardKind = UIKit.Label("CardKind", cardRoot, new Vector2(0f, 1f), new Vector2(26 * u, -14 * u), new Vector2(140 * u, 6 * u), TextAnchor.UpperLeft, UIKit.TextDim, 2f, UILabel.Style.Pixel, 30, new Vector2(0f, 1f));
            cardStats = UIKit.Label("CardStats", cardRoot, new Vector2(0f, 1f), new Vector2(26 * u, -22 * u), new Vector2(140 * u, 6 * u), TextAnchor.UpperLeft, UIKit.Gold, 2f, UILabel.Style.Pixel, 30, new Vector2(0f, 1f));
            cardDesc = UIKit.Label("CardDesc", cardRoot, new Vector2(0f, 1f), new Vector2(4 * u, -31 * u), new Vector2(162 * u, 20 * u), TextAnchor.UpperLeft, new Color(0.82f, 0.86f, 0.9f), 2f, UILabel.Style.Body, 22, new Vector2(0f, 1f));
            cardAffix = UIKit.Label("CardAffix", cardRoot, Vector2.zero, new Vector2(4 * u, 3 * u), new Vector2(162 * u, 6 * u), TextAnchor.LowerLeft, new Color(0.6f, 0.9f, 1f), 2f, UILabel.Style.Body, 22, Vector2.zero);
            cardPrice = UIKit.Label("CardPrice", cardRoot, new Vector2(1f, 1f), new Vector2(-4 * u, -4 * u), new Vector2(60 * u, 8 * u), TextAnchor.UpperRight, UIKit.Gold, 2.5f, UILabel.Style.Pixel, 30, Vector2.one);
            promptRoot.gameObject.SetActive(false);
            cardRoot.gameObject.SetActive(false);

            // Toasts (top-left) and achievement pop-up (top-centre).
            toastRoot = UIKit.Rect("Toasts", root, new Vector2(0f, 1f), new Vector2(18 * u, -14 * u), new Vector2(300 * u, 80 * u), new Vector2(0f, 1f));
            achRoot = UIKit.Rect("Achievement", root, new Vector2(0.5f, 1f), new Vector2(0f, -40 * u), new Vector2(150 * u, 22 * u), new Vector2(0.5f, 1f));
            UIKit.Fill("AchBack", achRoot, new Color(0.05f, 0.04f, 0.09f, 0.95f));
            UIKit.Frame(achRoot, UIKit.Gold, u);
            achIcon = UIKit.Box("AchIcon", achRoot, new Vector2(0f, 0.5f), new Vector2(3 * u, 0f), new Vector2(16 * u, 16 * u), Color.white, new Vector2(0f, 0.5f));
            achIcon.sprite = PixelIcons.Get("chest");
            var achHead = UIKit.Label("AchHead", achRoot, new Vector2(0f, 1f), new Vector2(22 * u, -3 * u), new Vector2(124 * u, 6 * u), TextAnchor.UpperLeft, UIKit.Gold, 2f, UILabel.Style.Pixel, 30, new Vector2(0f, 1f));
            achHead.SetKey("ach.unlocked_toast");
            achName = UIKit.Label("AchName", achRoot, new Vector2(0f, 0f), new Vector2(22 * u, 3 * u), new Vector2(124 * u, 8 * u), TextAnchor.LowerLeft, Color.white, 2.5f, UILabel.Style.Pixel, 30, Vector2.zero);
            achRoot.gameObject.SetActive(false);

            // Area title card.
            titleText = UIKit.Label("Title", root, new Vector2(0.5f, 0.68f), Vector2.zero, new Vector2(1600, 90), TextAnchor.MiddleCenter, Color.white, 7f);
            subtitleText = UIKit.Label("Subtitle", root, new Vector2(0.5f, 0.68f), new Vector2(0f, -70f), new Vector2(1400, 50), TextAnchor.MiddleCenter, new Color(0.8f, 0.85f, 0.9f), 3f, UILabel.Style.Body, 30);
            titleText.gameObject.SetActive(false);
            subtitleText.gameObject.SetActive(false);

            var fadeCanvas = UIKit.Canvas("FadeCanvas", 170, transform);
            fadeOverlay = UIKit.Fill("Fade", fadeCanvas.transform, new Color(0f, 0f, 0f, 1f));
            fadeValue = fadeTarget = 1f;
        }

        // ------------------------------------------------------------- public

        public void Fade(bool toBlack) => fadeTarget = toBlack ? 1f : 0f;

        CanvasGroup hudGroup;

        /// <summary>Menus hide the HUD (the fade overlay lives on its own canvas).</summary>
        public void SetVisible(bool visible)
        {
            if (hudGroup != null)
                hudGroup.alpha = visible ? 1f : 0f;
        }

        public void PulseGold() => goldPulse = 1f;

        public void PulseCells() => cellPulse = 1f;

        public void ShowBoss(EnemyBase b)
        {
            boss = b;
            bossRoot.gameObject.SetActive(b != null);
            if (b != null)
                bossName.Text = b.DisplayName;
        }

        public void Toast(string text, Color color)
        {
            var l = UIKit.Label("Toast", toastRoot, new Vector2(0f, 1f), Vector2.zero, new Vector2(300 * uiScale, 8 * uiScale), TextAnchor.MiddleLeft, color, 2.5f, UILabel.Style.Pixel, 30, new Vector2(0f, 1f));
            l.Text = text;
            toasts.Add((l, Time.unscaledTime + 3.2f));
            if (toasts.Count > 5)
            {
                Destroy(toasts[0].label.gameObject);
                toasts.RemoveAt(0);
            }
        }

        public void ShowTitle(string title, string subtitle, Color color)
        {
            titleText.Text = title;
            titleText.Color = color;
            subtitleText.Text = subtitle;
            titleStart = Time.unscaledTime;
            titleUntil = Time.unscaledTime + 3.6f;
            titleText.gameObject.SetActive(true);
            subtitleText.gameObject.SetActive(true);
        }

        void OnAchievement(string id)
        {
            achName.Text = Loc.Get($"ach.{id}.name");
            achUntil = Time.unscaledTime + 4f;
            achRoot.gameObject.SetActive(true);
        }

        void RefreshSlots()
        {
            if (combat == null)
                return;
            for (int i = 0; i < 4; i++)
            {
                var item = combat.Slot(i);
                var sprite = PixelIcons.For(item);
                slotIcon[i].sprite = sprite;
                slotIcon[i].enabled = sprite != null;
                slotFrame[i].color = item != null ? (item.quality > 0 ? ItemForge.QualityColor(item.quality) * 0.75f : KindColor[(int)item.kind]) : UIKit.Ink;
            }
            var amulet = combat.Amulet;
            amuletIcon.sprite = PixelIcons.For(amulet);
            amuletIcon.enabled = amuletIcon.sprite != null;
            amuletFrame.color = amulet != null ? ItemForge.QualityColor(amulet.quality) * 0.75f : UIKit.Ink;
            bool hasPack = SaveSystem.Data.meta.backpackUnlocked;
            packFrame.gameObject.SetActive(hasPack);
            var pack = combat.Backpack;
            packIcon.sprite = PixelIcons.For(pack);
            packIcon.enabled = packIcon.sprite != null;
        }

        // ------------------------------------------------------------- update

        /// <summary>Coordinate readout (Options > Show coordinates); F8 copies a bug-report line.</summary>
        void UpdateCoords()
        {
            var rm = Run.RunManager.Instance;
            var p = Player.PlayerController.Main;
            bool on = SaveSystem.Data.settings.showCoords && rm != null && rm.Level != null && p != null;
            coordText.gameObject.SetActive(on);
            if (!on)
                return;
            var cell = Run.RunManager.Cell(p.transform.position);
            var room = rm.RoomAt(cell);
            coordText.Text = $"X {cell.x}  Y {cell.y}\n{(room != null ? room.template : "-")}  #{rm.LevelSeed}";
            var kb = UnityEngine.InputSystem.Keyboard.current;
            if (kb != null && kb.f8Key.wasPressedThisFrame)
            {
                GUIUtility.systemCopyBuffer = rm.LocationReport(cell);
                Toast(Loc.Get("hud.coords_copied"), new Color(0.55f, 1f, 0.75f));
                Debug.Log("[DC] location " + rm.LocationReport(cell));
            }
        }

        void Update()
        {
            float dt = Time.unscaledDeltaTime;
            fadeValue = Mathf.MoveTowards(fadeValue, fadeTarget, dt * 2.6f);
            fadeOverlay.color = new Color(0f, 0f, 0f, fadeValue);
            fadeOverlay.raycastTarget = false;
            if (health == null)
                return;
            var run = SaveSystem.Data.run;
            UpdateCoords();

            float n = health.Normalized;
            float width = 130 * uiScale;
            fill.sizeDelta = new Vector2(width * n, fill.sizeDelta.y);
            trailHold -= dt;
            if (trailHold <= 0f)
                trailValue = Mathf.MoveTowards(trailValue, n, dt * 0.8f);
            trailValue = Mathf.Max(trailValue, n);
            trail.sizeDelta = new Vector2(width * trailValue, trail.sizeDelta.y);
            float rec = player != null ? player.Recoverable : 0f;
            recover.sizeDelta = new Vector2(width * Mathf.Clamp01(n + rec / Mathf.Max(1f, health.maxHealth)), recover.sizeDelta.y);
            hpText.Text = $"{Mathf.CeilToInt(health.Current)} / {Mathf.CeilToInt(health.maxHealth)}";
            statB.Text = run.brutality.ToString();
            statT.Text = run.tactics.ToString();
            statS.Text = run.survival.ToString();
            curseText.Text = run.curse > 0 ? Loc.Get("hud.curse", run.curse) : "";
            mutationText.Text = MutationLine(run);
            flaskText.Text = $"x{run.flaskCharges}";

            damagePulse = Mathf.MoveTowards(damagePulse, 0f, dt * 2.5f);
            damageOverlay.color = new Color(0.6f, 0f, 0.05f, damagePulse * 0.28f + (n < 0.25f ? 0.06f + Mathf.PingPong(Time.unscaledTime, 0.5f) * 0.1f : 0f));

            goldPulse = Mathf.MoveTowards(goldPulse, 0f, dt * 4f);
            cellPulse = Mathf.MoveTowards(cellPulse, 0f, dt * 4f);
            goldText.Text = run.gold.ToString();
            cellsText.Text = run.cells.ToString();
            goldIcon.rectTransform.localScale = Vector3.one * (1f + goldPulse * 0.3f);
            cellIcon.rectTransform.localScale = Vector3.one * (1f + cellPulse * 0.3f);
            timerText.Text = UIKit.FormatTime(run.time);
            var rm = RunManager.Instance;
            if (rm != null && rm.Current != null)
                areaText.Text = rm.Current.DisplayName;

            UpdateSlots();
            UpdateMinimap();
            UpdatePrompt();
            UpdateBoss();
            UpdateToasts();
        }

        string mutationKey;
        string mutationLine = "";

        string MutationLine(RunState run)
        {
            string key = string.Join(",", run.mutations) + Loc.Current;
            if (key != mutationKey)
            {
                mutationKey = key;
                var names = new List<string>();
                foreach (var id in run.mutations)
                    names.Add(Loc.Get("mutation." + id + ".name"));
                mutationLine = string.Join("  ·  ", names);
            }
            return mutationLine;
        }

        void UpdateSlots()
        {
            if (combat == null)
                return;
            for (int i = 0; i < 4; i++)
            {
                float f = combat.CooldownFraction(i);
                slotCooldown[i].fillAmount = f;
                float remaining = combat.CooldownRemaining(i);
                slotTimer[i].Text = remaining > 0.5f ? Mathf.CeilToInt(remaining).ToString() : "";
            }
        }

        void UpdateMinimap()
        {
            var map = MapSystem.Instance;
            if (map == null || map.Texture == null || player == null)
            {
                minimap.enabled = false;
                return;
            }
            minimap.enabled = true;
            minimap.texture = map.Texture;
            // 3 screen pixels per tile around the player.
            float tilesW = 90f * uiScale / 9f, tilesH = 54f * uiScale / 9f;
            Vector2 p = player.transform.position;
            minimap.uvRect = new Rect((p.x - tilesW * 0.5f) / map.Width, (p.y + 1f - tilesH * 0.5f) / map.Height, tilesW / map.Width, tilesH / map.Height);
            int used = 0;
            var rm = RunManager.Instance;
            if (rm != null && rm.Level != null)
            {
                foreach (var t in rm.Level.teleporters)
                    if (t != null && t.Discovered)
                        used = Marker(used, t.transform.position, p, tilesW, tilesH, "teleporter");
                foreach (var e in rm.Level.exits)
                    if (map.Explored(e))
                        used = Marker(used, e, p, tilesW, tilesH, "door");
            }
            used = Marker(used, p, p, tilesW, tilesH, "player");
            for (int i = used; i < markerPool.Count; i++)
                markerPool[i].enabled = false;
        }

        int Marker(int index, Vector2 world, Vector2 center, float tilesW, float tilesH, string icon)
        {
            Vector2 local = new Vector2((world.x - center.x) / tilesW, (world.y - center.y - 1f) / tilesH);
            if (Mathf.Abs(local.x) > 0.5f || Mathf.Abs(local.y) > 0.5f)
                return index;
            while (markerPool.Count <= index)
            {
                var img = UIKit.Box("Marker", minimapMarkers, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(10 * uiScale * 0.8f, 10 * uiScale * 0.8f), Color.white);
                markerPool.Add(img);
            }
            var m = markerPool[index];
            m.enabled = true;
            m.sprite = PixelIcons.Get(icon);
            m.rectTransform.anchoredPosition = new Vector2(local.x * 90f * uiScale, local.y * 54f * uiScale);
            return index + 1;
        }

        void UpdatePrompt()
        {
            var it = Interactable.Current;
            bool show = it != null && player != null && player.InControl;
            promptRoot.gameObject.SetActive(show);
            var item = show ? it.CardItem : null;
            cardRoot.gameObject.SetActive(item != null);
            if (!show)
                return;
            promptText.Text = Loc.Get("hud.interact", it.Prompt);
            if (item == null)
                return;
            cardIcon.sprite = PixelIcons.For(item);
            cardTitle.Text = ItemForge.FullName(item);
            cardTitle.Color = ItemForge.QualityColor(item.quality);
            string affix = ItemForge.AffixLines(item).TrimStart('\n');
            int lines = affix.Length == 0 ? 0 : affix.Split('\n').Length;
            cardAffix.Text = affix;
            // Body text runs ~13.5 units per line at this size.
            ((RectTransform)cardAffix.transform).sizeDelta = new Vector2(162 * uiScale, 14 * uiScale * lines);
            cardRoot.sizeDelta = new Vector2(170 * uiScale, (54 + 14 * lines) * uiScale);
            int slot = combat != null ? combat.SlotFor(item) : -1;
            var replaced = slot >= 0 ? combat.Slot(slot) : null;
            string kind = Loc.Get("kind." + item.kind.ToString().ToLowerInvariant());
            string colors = ItemForge.ColorTags(item);
            if (colors.Length > 0)
                kind += "  ·  " + colors;
            cardKind.Text = replaced != null ? kind + "  -  " + Loc.Get("hud.replace", ItemForge.FullName(replaced)) : kind;
            string crit = item.crit == CritRule.None ? "" : "   " + Loc.Get("hud.crit_label", Loc.Get("crit." + item.crit.ToString().ToLowerInvariant()));
            cardStats.Text = item.StatLine + crit;
            cardDesc.Text = item.Description;
            int price = it.CardPrice;
            cardPrice.Text = price > 0 ? price.ToString() : "";
            cardPrice.Color = price > SaveSystem.Data.run.gold ? new Color(1f, 0.4f, 0.35f) : UIKit.Gold;
        }

        void UpdateBoss()
        {
            if (boss == null)
            {
                if (bossRoot.gameObject.activeSelf)
                    bossRoot.gameObject.SetActive(false);
                return;
            }
            float n = boss.Health != null ? boss.Health.Normalized : 0f;
            bossFill.sizeDelta = new Vector2(218 * uiScale * n, bossFill.sizeDelta.y);
            if (boss.IsDead)
                ShowBoss(null);
        }

        void UpdateToasts()
        {
            float now = Time.unscaledTime;
            for (int i = toasts.Count - 1; i >= 0; i--)
            {
                var (label, until) = toasts[i];
                if (now > until)
                {
                    Destroy(label.gameObject);
                    toasts.RemoveAt(i);
                    continue;
                }
                float a = Mathf.Clamp01((until - now) / 0.6f);
                var c = label.Color;
                label.Color = new Color(c.r, c.g, c.b, a);
            }
            for (int i = 0; i < toasts.Count; i++)
                toasts[i].label.RectTransform.anchoredPosition = new Vector2(0f, -i * 10 * uiScale);

            if (achRoot.gameObject.activeSelf && now > achUntil)
                achRoot.gameObject.SetActive(false);

            if (titleText.gameObject.activeSelf)
            {
                float t = now - titleStart;
                float a = Mathf.Clamp01(t / 0.5f) * Mathf.Clamp01((titleUntil - now) / 0.8f);
                var tc = titleText.Color;
                titleText.Color = new Color(tc.r, tc.g, tc.b, a);
                subtitleText.Color = new Color(0.8f, 0.85f, 0.9f, a);
                if (now > titleUntil)
                {
                    titleText.gameObject.SetActive(false);
                    subtitleText.gameObject.SetActive(false);
                }
            }
        }
    }
}
