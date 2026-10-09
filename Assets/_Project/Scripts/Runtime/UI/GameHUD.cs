using DeadCells.Combat;
using DeadCells.Player;
using UnityEngine;
using UnityEngine.UI;

namespace DeadCells.UI
{
    /// <summary>
    /// Dead Cells-style HUD built in code: health bar (bottom-left) with a
    /// delayed damage trail and numeric readout, weapon slots, cells counter and
    /// run timer (bottom-right), plus a red vignette pulse on damage and a
    /// fade-to-black overlay for death/respawn.
    /// </summary>
    public class GameHUD : MonoBehaviour
    {
        public PlayerController player;
        public float uiScale = 3f;

        Health health;
        PlayerCombat combat;
        RectTransform fill, trail;
        PixelText hpText, cellsText, timerText, weaponText, hintText;
        Image damageOverlay, fadeOverlay;
        Image[] slotFrames;
        float trailValue = 1f;
        float trailHold;
        float damagePulse;
        float fadeTarget, fadeValue;
        float runStart;
        int cells;
        static Sprite white;

        public static GameHUD Instance { get; private set; }

        void Awake()
        {
            Instance = this;
        }

        void Start()
        {
            runStart = Time.time;
            Build();
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
                    combat.WeaponChanged += _ => RefreshWeapon();
            }
            Enemies.ZombieEnemy.Killed += _ => AddCells(Random.Range(2, 5));
            RefreshWeapon();
        }

        void OnDestroy()
        {
            if (Instance == this)
                Instance = null;
        }

        static Sprite White
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

        RectTransform Rect(string name, Transform parent, Vector2 anchor, Vector2 pos, Vector2 size)
        {
            var go = new GameObject(name, typeof(RectTransform));
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.anchorMin = rt.anchorMax = anchor;
            rt.pivot = anchor;
            rt.anchoredPosition = pos;
            rt.sizeDelta = size;
            return rt;
        }

        Image Box(string name, Transform parent, Vector2 anchor, Vector2 pos, Vector2 size, Color color)
        {
            var img = Rect(name, parent, anchor, pos, size).gameObject.AddComponent<Image>();
            img.sprite = White;
            img.color = color;
            img.raycastTarget = false;
            return img;
        }

        PixelText Label(string name, Transform parent, Vector2 anchor, Vector2 pos, Vector2 size, TextAnchor align, Color color)
        {
            var t = Rect(name, parent, anchor, pos, size).gameObject.AddComponent<PixelText>();
            t.pixelScale = uiScale;
            t.alignment = align;
            t.color = color;
            t.raycastTarget = false;
            return t;
        }

        void Build()
        {
            var canvasGo = new GameObject("HUDCanvas", typeof(Canvas), typeof(CanvasScaler));
            canvasGo.transform.SetParent(transform, false);
            var canvas = canvasGo.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.pixelPerfect = true;
            canvas.sortingOrder = 100;
            var scaler = canvasGo.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.matchWidthOrHeight = 1f;
            Transform root = canvasGo.transform;
            float u = uiScale;

            damageOverlay = Box("DamageOverlay", root, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(4000, 4000), new Color(0.6f, 0f, 0.05f, 0f));

            // Health bar.
            Vector2 bl = new Vector2(0f, 0f);
            Box("HPFrame", root, bl, new Vector2(18 * u, 10 * u), new Vector2(132 * u, 9 * u), new Color(0.02f, 0.03f, 0.05f, 0.92f));
            Box("HPBack", root, bl, new Vector2(19 * u, 11 * u), new Vector2(130 * u, 7 * u), new Color(0.08f, 0.12f, 0.12f, 1f));
            trail = Box("HPTrail", root, bl, new Vector2(19 * u, 11 * u), new Vector2(130 * u, 7 * u), new Color(0.85f, 0.25f, 0.2f, 1f)).rectTransform;
            fill = Box("HPFill", root, bl, new Vector2(19 * u, 11 * u), new Vector2(130 * u, 7 * u), new Color(0.18f, 0.78f, 0.38f, 1f)).rectTransform;
            var shine = Box("HPShine", fill, new Vector2(0f, 1f), Vector2.zero, new Vector2(0f, 2 * u), new Color(0.6f, 1f, 0.7f, 0.45f)).rectTransform;
            shine.anchorMin = new Vector2(0f, 1f);
            shine.anchorMax = new Vector2(1f, 1f);
            shine.pivot = new Vector2(0.5f, 1f);
            shine.sizeDelta = new Vector2(0f, 2 * u);
            hpText = Label("HPText", root, bl, new Vector2(19 * u, 11 * u), new Vector2(130 * u, 7 * u), TextAnchor.MiddleCenter, Color.white);

            // Weapon slots above the bar, key hint in each slot's corner.
            slotFrames = new Image[3];
            string[] keys = { "J", "Q", "L" };
            Color[] inner = { new Color(0.12f, 0.2f, 0.26f, 1f), new Color(0.2f, 0.16f, 0.1f, 1f), new Color(0.35f, 0.08f, 0.1f, 1f) };
            for (int i = 0; i < 3; i++)
            {
                var pos = new Vector2((18 + i * 24) * u, 23 * u);
                slotFrames[i] = Box("Slot" + i, root, bl, pos, new Vector2(21 * u, 21 * u), new Color(0.05f, 0.06f, 0.09f, 0.9f));
                Box("SlotInner" + i, slotFrames[i].transform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(17 * u, 17 * u), inner[i]);
                var key = Label("Key" + i, slotFrames[i].transform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(17 * u, 17 * u), TextAnchor.MiddleCenter, new Color(0.85f, 0.9f, 0.95f));
                key.Text = keys[i];
            }
            weaponText = Label("Weapon", root, bl, new Vector2(92 * u, 29 * u), new Vector2(200 * u, 8 * u), TextAnchor.MiddleLeft, new Color(0.85f, 0.95f, 1f));

            // Cells + timer bottom-right.
            Vector2 br = new Vector2(1f, 0f);
            Box("CellIcon", root, br, new Vector2(-62 * u, 12 * u), new Vector2(6 * u, 6 * u), new Color(0.35f, 0.85f, 1f, 1f));
            cellsText = Label("Cells", root, br, new Vector2(-18 * u, 11 * u), new Vector2(40 * u, 8 * u), TextAnchor.MiddleRight, new Color(0.6f, 0.95f, 1f));
            timerText = Label("Timer", root, new Vector2(1f, 1f), new Vector2(-18 * u, -12 * u), new Vector2(80 * u, 8 * u), TextAnchor.MiddleRight, new Color(0.75f, 0.8f, 0.85f, 0.85f));
            hintText = Label("Hint", root, new Vector2(0f, 1f), new Vector2(18 * u, -12 * u), new Vector2(400 * u, 8 * u), TextAnchor.MiddleLeft, new Color(0.7f, 0.8f, 0.85f, 0.75f));
            hintText.pixelScale = 2f;
            hintText.Text = "MOVE A/D  JUMP SPACE  ATTACK J  ROLL SHIFT  SHIELD L  SLAM S+SPACE  SWAP Q  FLAME F";

            fadeOverlay = Box("Fade", root, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(4000, 4000), new Color(0f, 0f, 0f, 0f));
        }

        void RefreshWeapon()
        {
            if (weaponText != null && combat != null && combat.Weapon != null)
                weaponText.Text = combat.Weapon.displayName.ToUpperInvariant();
        }

        public void AddCells(int amount)
        {
            cells += amount;
        }

        public void Fade(bool toBlack) => fadeTarget = toBlack ? 1f : 0f;

        void Update()
        {
            if (health == null || fill == null)
                return;
            float dt = Time.unscaledDeltaTime;
            float n = health.Normalized;
            float width = 130 * uiScale;
            fill.sizeDelta = new Vector2(width * n, fill.sizeDelta.y);
            trailHold -= dt;
            if (trailHold <= 0f)
                trailValue = Mathf.MoveTowards(trailValue, n, dt * 0.8f);
            trailValue = Mathf.Max(trailValue, n);
            trail.sizeDelta = new Vector2(width * trailValue, trail.sizeDelta.y);
            hpText.Text = $"{Mathf.CeilToInt(health.Current)} / {Mathf.CeilToInt(health.maxHealth)}";

            damagePulse = Mathf.MoveTowards(damagePulse, 0f, dt * 2.5f);
            damageOverlay.color = new Color(0.6f, 0f, 0.05f, damagePulse * 0.28f);
            fadeValue = Mathf.MoveTowards(fadeValue, fadeTarget, dt * 1.8f);
            fadeOverlay.color = new Color(0f, 0f, 0f, fadeValue);

            cellsText.Text = cells.ToString();
            float t = Time.time - runStart;
            timerText.Text = $"{Mathf.FloorToInt(t / 60f)}M {Mathf.FloorToInt(t % 60f):00}S";

            if (combat != null && slotFrames != null)
            {
                bool attacking = combat.Attacking;
                bool blocking = player.State == PlayerState.Block;
                slotFrames[0].color = attacking ? new Color(0.9f, 0.85f, 0.6f, 1f) : new Color(0.05f, 0.06f, 0.09f, 0.9f);
                slotFrames[2].color = blocking ? new Color(0.9f, 0.4f, 0.35f, 1f) : new Color(0.05f, 0.06f, 0.09f, 0.9f);
            }
        }
    }
}
