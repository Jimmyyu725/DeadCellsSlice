using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using DeadCells.Core;
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
    /// In-game screens: pause (options, achievements, cheats), the map with
    /// Dead Cells-style teleport selection, the Collector, story pages
    /// (prologue, lore tablets, ending), dialogue lines, subtitles and the
    /// death screen. Owns pausing and whether gameplay input is live.
    /// </summary>
    public class GameUI : MonoBehaviour
    {
        public PlayerController player;

        public static GameUI Instance { get; private set; }

        MenuPanel menu;
        Canvas overlayCanvas;
        // Story pages.
        RectTransform storyRoot;
        Image storyBack;
        UILabel storyTitle, storyBody, storyHint;
        bool storyOpen;
        // Map.
        RectTransform mapRoot;
        RawImage mapImage;
        RectTransform mapMarkers;
        UILabel mapTitle, mapHint, mapLegend;
        readonly List<Image> mapMarkerPool = new List<Image>();
        bool mapOpen, teleportMode;
        List<Teleporter> teleportChoices = new List<Teleporter>();
        int teleportIndex;
        Teleporter teleportFrom;
        // Dialogue / subtitles.
        RectTransform sayRoot;
        UILabel sayName, sayText;
        float sayUntil;
        Coroutine subtitles;

        public bool AnyOpen => menu.IsOpen || storyOpen || mapOpen;

        void Awake()
        {
            Instance = this;
            menu = MenuPanel.Create("GameMenu", 200, transform);
            menu.Closed += () => { };
            BuildOverlay();
            GameUIBridge.Say = Say;
        }

        void OnDestroy()
        {
            if (Instance == this)
                Instance = null;
            GameUIBridge.Say = null;
            GameInput.GameplayEnabled = true;
            GamePause.Set(false);
        }

        void BuildOverlay()
        {
            overlayCanvas = UIKit.Canvas("Overlay", 180, transform);
            var root = overlayCanvas.transform;

            // Map.
            mapRoot = UIKit.Stretch("Map", root);
            UIKit.Fill("MapBack", mapRoot, new Color(0.01f, 0.01f, 0.03f, 0.9f));
            var mapClip = UIKit.Rect("MapClip", mapRoot, new Vector2(0.5f, 0.5f), new Vector2(0f, 10f), new Vector2(1760f, 840f));
            mapClip.gameObject.AddComponent<RectMask2D>();
            UIKit.Frame(mapClip, new Color(0.35f, 0.25f, 0.5f, 1f), 3f);
            mapImage = UIKit.Rect("MapImage", mapClip, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(1700f, 820f)).gameObject.AddComponent<RawImage>();
            mapImage.raycastTarget = false;
            mapMarkers = UIKit.Rect("MapMarkers", mapImage.transform, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(1700f, 820f));
            mapTitle = UIKit.Label("MapTitle", mapRoot, new Vector2(0.5f, 1f), new Vector2(0f, -50f), new Vector2(1200f, 60f), TextAnchor.MiddleCenter, Color.white, 5f);
            mapHint = UIKit.Label("MapHint", mapRoot, new Vector2(0.5f, 0f), new Vector2(0f, 40f), new Vector2(1600f, 40f), TextAnchor.MiddleCenter, UIKit.TextDim, 3f);
            mapLegend = UIKit.Label("MapLegend", mapRoot, new Vector2(0f, 0f), new Vector2(60f, 90f), new Vector2(1200f, 30f), TextAnchor.MiddleLeft, UIKit.TextDim, 2f);
            mapLegend.gameObject.SetActive(false);
            string[] legendIcons = { "player", "teleporter", "door", "shop", "chest", "lore" };
            for (int i = 0; i < legendIcons.Length; i++)
            {
                var icon = UIKit.Box("LegendIcon" + i, mapRoot, new Vector2(0f, 0f), new Vector2(80f + i * 210f, 70f), new Vector2(36f, 36f), Color.white);
                icon.sprite = PixelIcons.Get(legendIcons[i]);
                var l = UIKit.Label("LegendText" + i, mapRoot, new Vector2(0f, 0f), new Vector2(124f + i * 210f, 70f), new Vector2(160f, 36f), TextAnchor.MiddleLeft, UIKit.TextDim, 2.5f);
                l.SetKey("map.legend." + legendIcons[i]);
            }
            mapRoot.gameObject.SetActive(false);

            // Dialogue box.
            sayRoot = UIKit.Rect("Say", root, new Vector2(0.5f, 0f), new Vector2(0f, 260f), new Vector2(1100f, 130f), new Vector2(0.5f, 0f));
            UIKit.Fill("SayBack", sayRoot, new Color(0.03f, 0.03f, 0.06f, 0.88f));
            UIKit.Frame(sayRoot, new Color(0.4f, 0.28f, 0.6f), 3f);
            sayName = UIKit.Label("SayName", sayRoot, new Vector2(0f, 1f), new Vector2(24f, -16f), new Vector2(800f, 36f), TextAnchor.UpperLeft, UIKit.Gold, 3f, UILabel.Style.Pixel, 30, new Vector2(0f, 1f));
            sayText = UIKit.Label("SayText", sayRoot, new Vector2(0f, 1f), new Vector2(24f, -58f), new Vector2(1050f, 70f), TextAnchor.UpperLeft, Color.white, 3f, UILabel.Style.Body, 30, new Vector2(0f, 1f));
            sayRoot.gameObject.SetActive(false);

            // Story pages (full screen, above everything).
            storyRoot = UIKit.Stretch("Story", root);
            storyBack = UIKit.Fill("StoryBack", storyRoot, Color.black);
            storyTitle = UIKit.Label("StoryTitle", storyRoot, new Vector2(0.5f, 0.72f), Vector2.zero, new Vector2(1600f, 80f), TextAnchor.MiddleCenter, new Color(0.85f, 0.7f, 1f), 5f);
            storyBody = UIKit.Label("StoryBody", storyRoot, new Vector2(0.5f, 0.5f), new Vector2(0f, -20f), new Vector2(1250f, 420f), TextAnchor.MiddleCenter, new Color(0.92f, 0.9f, 0.95f), 3f, UILabel.Style.Body, 38);
            storyHint = UIKit.Label("StoryHint", storyRoot, new Vector2(0.5f, 0f), new Vector2(0f, 50f), new Vector2(1400f, 30f), TextAnchor.MiddleCenter, new Color(0.5f, 0.5f, 0.6f), 2f);
            storyRoot.gameObject.SetActive(false);
        }

        // ---------------------------------------------------------------- loop

        void Update()
        {
            bool open = AnyOpen;
            GameInput.GameplayEnabled = !open;
            GamePause.Set(open);
            GameHUD.Instance?.SetVisible(!open);
            if (sayRoot.gameObject.activeSelf && Time.unscaledTime > sayUntil)
                sayRoot.gameObject.SetActive(false);
            if (mapOpen)
            {
                UpdateMap();
                return;
            }
            if (open || player == null)
                return;
            var rm = RunManager.Instance;
            if (rm != null && rm.Transitioning)
                return;
            if (player.State == PlayerState.Dead)
                return;
            if (player.Input.pausePressed)
                OpenPause();
            else if (player.Input.mapPressed)
                OpenMap(null);
        }

        // Test hooks for the autoplay verifier.
        public void OpenPauseForTest() => OpenPause();
        public void OpenMapForTest() => OpenMap(null);

        public void CloseAllForTest()
        {
            menu.CloseAll();
            if (mapOpen)
                CloseMap();
            if (storyOpen)
            {
                StopAllCoroutines();
                storyRoot.gameObject.SetActive(false);
                storyOpen = false;
            }
        }

        // --------------------------------------------------------------- pause

        public void OpenPause()
        {
            Audio.Sfx.Play("ui.open");
            var page = new MenuPage { title = () => Loc.Get("menu.paused"), body = () => RunSummary() };
            page.Add(MenuItem.Button(() => Loc.Get("menu.resume"), menu.CloseAll));
            page.Add(MenuItem.Button(() => Loc.Get("map.title"), () =>
            {
                menu.CloseAll();
                OpenMap(null);
            }));
            page.Add(MenuItem.Button(() => Loc.Get("menu.options"), () => menu.Push(MenuPages.Options(menu))));
            page.Add(MenuItem.Button(() => Loc.Get("menu.achievements"), () => menu.Push(MenuPages.Achievements(menu))));
            page.Add(MenuItem.Button(() => Loc.Get("menu.changelog"), () => menu.Push(MenuPages.Changelog(menu))));
            if (Cheats.Unlocked)
                page.Add(MenuItem.Button(() => Loc.Get("menu.cheats"), () => menu.Push(MenuPages.Cheats(menu))));
            page.Add(MenuItem.Button(() => Loc.Get("menu.unstuck"), () =>
            {
                menu.CloseAll();
                RunManager.Instance.TeleportToNearest();
            }, () => Loc.Get("menu.unstuck.desc")));
            page.Add(MenuItem.Button(() => Loc.Get("menu.main_menu"), () => RunManager.Instance.SaveAndQuit(), () => Loc.Get("hud.saved")));
            page.Add(MenuItem.Button(() => Loc.Get("menu.abandon"), () => menu.Confirm(() => Loc.Get("menu.abandon_confirm"), () => RunManager.Instance.AbandonRun())));
            page.onBack = menu.CloseAll;
            menu.Push(page);
        }

        static string RunSummary()
        {
            var run = SaveSystem.Data.run;
            string diff = Difficulty.Label(run.difficulty);
            string bc = run.bossCells > 0 ? $"  BC {run.bossCells}" : "";
            return $"{diff}{bc}   {UIKit.FormatTime(run.time)}   {Loc.Get("hud.biome_kills", run.kills)}";
        }

        // ----------------------------------------------------------------- map

        public void OpenTeleportMap(Teleporter from) => OpenMap(from);

        void OpenMap(Teleporter from)
        {
            var rm = RunManager.Instance;
            var map = MapSystem.Instance;
            if (rm == null || map == null || map.Texture == null)
                return;
            mapOpen = true;
            Audio.Sfx.Play("ui.open");
            teleportMode = from != null;
            teleportFrom = from;
            teleportChoices = rm.Level.teleporters.Where(t => t != null && t.Discovered && t != from).OrderBy(t => t.transform.position.x).ToList();
            teleportIndex = 0;
            if (teleportMode && teleportChoices.Count == 0)
                teleportMode = false;
            mapRoot.gameObject.SetActive(true);
            mapImage.texture = map.Texture;
            // Six screen pixels per tile, centred on the player (the clip rect hides the rest).
            const float scale = 6f;
            var size = new Vector2(map.Width * scale, map.Height * scale);
            mapImage.rectTransform.sizeDelta = size;
            mapMarkers.sizeDelta = size;
            CenterMap(player != null ? player.transform.position : new Vector3(map.Width * 0.5f, map.Height * 0.5f, 0f));
            mapTitle.Text = teleportMode ? Loc.Get("map.teleport_title") : rm.Current.DisplayName;
            mapHint.Text = teleportMode ? Loc.Get("map.teleport_hint") : Loc.Get("map.hint");
            mapLegend.Text = Loc.Get("map.legend");
        }

        void CenterMap(Vector3 world)
        {
            var map = MapSystem.Instance;
            var size = mapImage.rectTransform.sizeDelta;
            var offset = new Vector2((0.5f - world.x / map.Width) * size.x, (0.5f - (world.y + 1f) / map.Height) * size.y);
            // Keep the map edges inside the panel when the map is larger than it.
            float maxX = Mathf.Max(0f, (size.x - 1760f) * 0.5f), maxY = Mathf.Max(0f, (size.y - 840f) * 0.5f);
            offset.x = Mathf.Clamp(offset.x, -maxX, maxX);
            offset.y = Mathf.Clamp(offset.y, -maxY, maxY);
            mapImage.rectTransform.anchoredPosition = offset;
        }

        void CloseMap()
        {
            if (mapOpen)
                Audio.Sfx.Play("ui.close");
            mapOpen = false;
            teleportMode = false;
            mapRoot.gameObject.SetActive(false);
        }

        void UpdateMap()
        {
            var rm = RunManager.Instance;
            var map = MapSystem.Instance;
            if (rm == null || map == null)
            {
                CloseMap();
                return;
            }
            if (teleportMode)
            {
                if (MenuInput.Left || MenuInput.Up) teleportIndex = (teleportIndex - 1 + teleportChoices.Count) % teleportChoices.Count;
                if (MenuInput.Right || MenuInput.Down) teleportIndex = (teleportIndex + 1) % teleportChoices.Count;
                CenterMap(teleportChoices[teleportIndex].transform.position);
                if (MenuInput.Confirm)
                {
                    var target = teleportChoices[teleportIndex];
                    CloseMap();
                    rm.TeleportTo(target);
                    return;
                }
            }
            if (MenuInput.Cancel || (!teleportMode && MenuInput.Map))
            {
                CloseMap();
                return;
            }
            var size = mapImage.rectTransform.sizeDelta;
            int used = 0;
            Vector2 ToMap(Vector3 w) => new Vector2((w.x / map.Width - 0.5f) * size.x, ((w.y + 1f) / map.Height - 0.5f) * size.y);
            foreach (var t in rm.Level.teleporters)
            {
                if (t == null || !t.Discovered)
                    continue;
                bool selected = teleportMode && teleportChoices.Count > 0 && teleportChoices[teleportIndex] == t;
                float pulse = selected ? 1.4f + Mathf.PingPong(Time.unscaledTime * 2f, 0.5f) : 1f;
                used = MapMarker(used, ToMap(t.transform.position), "teleporter", pulse);
            }
            foreach (var e in rm.Level.exits)
                if (map.Explored(e))
                    used = MapMarker(used, ToMap(e), "door", 1f);
            foreach (var s in rm.Level.shops)
                if (map.Explored(s))
                    used = MapMarker(used, ToMap(s), "shop", 1f);
            foreach (var c in rm.Level.treasures)
                if (map.Explored(c))
                    used = MapMarker(used, ToMap(c), "chest", 1f);
            foreach (var l in rm.Level.lore)
                if (map.Explored(l))
                    used = MapMarker(used, ToMap(l), "lore", 1f);
            if (player != null)
                used = MapMarker(used, ToMap(player.transform.position), "player", 1.2f + Mathf.PingPong(Time.unscaledTime, 0.3f));
            for (int i = used; i < mapMarkerPool.Count; i++)
                mapMarkerPool[i].enabled = false;
        }

        int MapMarker(int index, Vector2 pos, string icon, float scale)
        {
            while (mapMarkerPool.Count <= index)
                mapMarkerPool.Add(UIKit.Box("Marker", mapMarkers, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(40f, 40f), Color.white));
            var m = mapMarkerPool[index];
            m.enabled = true;
            m.sprite = PixelIcons.Get(icon);
            m.rectTransform.anchoredPosition = pos;
            m.rectTransform.localScale = Vector3.one * scale;
            return index + 1;
        }

        // ----------------------------------------------------------- collector

        public void OpenCollector()
        {
            var page = new MenuPage
            {
                title = () => Loc.Get("npc.collector.title"),
                body = () => Loc.Get("npc.collector.greet") + "\n" + Loc.Get("npc.collector.cells", SaveSystem.Data.run.cells),
                visibleRows = 8,
            };
            var meta = SaveSystem.Data.meta;
            int[] flaskCost = { 40, 80, 120 };
            int[] vitalityCost = { 30, 60, 90, 120, 150 };
            page.Add(new MenuItem
            {
                label = () => Loc.Get("npc.collector.flask"),
                value = () => meta.flaskLevel >= flaskCost.Length ? Loc.Get("npc.collector.max") : Loc.Get("npc.collector.cost", flaskCost[meta.flaskLevel]),
                description = () => Loc.Get("npc.collector.flask.desc"),
                enabled = () => meta.flaskLevel < flaskCost.Length,
                confirm = () =>
                {
                    if (Spend(flaskCost[meta.flaskLevel]))
                    {
                        meta.flaskLevel++;
                        SaveSystem.Data.run.flaskCharges++;
                        SaveSystem.Save();
                    }
                },
            });
            page.Add(new MenuItem
            {
                label = () => Loc.Get("npc.collector.vitality"),
                value = () => meta.vitalityLevel >= vitalityCost.Length ? Loc.Get("npc.collector.max") : Loc.Get("npc.collector.cost", vitalityCost[meta.vitalityLevel]),
                description = () => Loc.Get("npc.collector.vitality.desc"),
                enabled = () => meta.vitalityLevel < vitalityCost.Length,
                confirm = () =>
                {
                    if (Spend(vitalityCost[meta.vitalityLevel]))
                    {
                        meta.vitalityLevel++;
                        player.RecalculateStats(false);
                        SaveSystem.Save();
                    }
                },
            });
            var db = ItemDatabase.Instance;
            if (db != null)
            {
                foreach (var item in db.items.Where(i => i != null && i.unlockCost > 0).OrderBy(i => i.unlockCost))
                {
                    var it = item;
                    page.Add(new MenuItem
                    {
                        label = () => it.DisplayName,
                        value = () => it.IsUnlocked ? Loc.Get("npc.collector.unlocked")
                            : meta.blueprints.Contains(it.id) ? Loc.Get("npc.collector.cost", it.unlockCost) : "?",
                        description = () => (it.IsUnlocked || meta.blueprints.Contains(it.id) ? "" : Loc.Get("npc.collector.no_blueprint") + " - ") + it.Description,
                        enabled = () => !it.IsUnlocked && meta.blueprints.Contains(it.id),
                        tint = () => it.IsUnlocked ? new Color(0.55f, 0.75f, 0.55f) : (Color?)null,
                        confirm = () =>
                        {
                            if (Spend(it.unlockCost))
                            {
                                meta.blueprints.Remove(it.id);
                                meta.unlockedItems.Add(it.id);
                                Achievements.CheckThresholds();
                                SaveSystem.Save();
                                GameHUD.Instance?.Toast(Loc.Get("npc.collector.done"), UIKit.CellBlue);
                            }
                        },
                    });
                }
            }
            page.Add(MenuItem.Button(() => Loc.Get("npc.collector.leave"), menu.CloseAll));
            page.onBack = menu.CloseAll;
            menu.Push(page);
        }

        bool Spend(int cells)
        {
            var run = SaveSystem.Data.run;
            if (run.cells < cells)
            {
                GameHUD.Instance?.Toast(Loc.Get("npc.collector.need_cells"), new Color(1f, 0.5f, 0.4f));
                return false;
            }
            run.cells -= cells;
            SaveSystem.Data.stats.cellsSpent += cells;
            return true;
        }

        // ------------------------------------------------------- story pages

        IEnumerator Pages(IList<(string title, string body)> pages, bool skippable, float minTime = 0.6f)
        {
            storyOpen = true;
            storyRoot.gameObject.SetActive(true);
            storyHint.Text = skippable ? Loc.Get("story.continue") + "     " + Loc.Get("story.skip") : Loc.Get("story.continue");
            float hold = 0f;
            for (int i = 0; i < pages.Count; i++)
            {
                storyTitle.Text = pages[i].title;
                storyBody.Text = pages[i].body;
                float t = 0f;
                while (true)
                {
                    t += Time.unscaledDeltaTime;
                    float a = Mathf.Clamp01(t / 0.5f);
                    storyTitle.Color = new Color(0.85f, 0.7f, 1f, a);
                    storyBody.Color = new Color(0.92f, 0.9f, 0.95f, a);
                    if (skippable && (UnityEngine.InputSystem.Keyboard.current?.escapeKey.isPressed ?? false))
                    {
                        hold += Time.unscaledDeltaTime;
                        if (hold > 0.6f)
                        {
                            i = pages.Count;
                            break;
                        }
                    }
                    else
                    {
                        hold = 0f;
                    }
                    if (t > minTime && (MenuInput.Confirm || MenuInput.MouseClicked))
                        break;
                    if (AutoplayDirector.Active && t > 1.2f)
                        break;
                    yield return null;
                }
                yield return null;
            }
            storyRoot.gameObject.SetActive(false);
            storyOpen = false;
        }

        static (string, string) P(string titleKey, string bodyKey) => (titleKey != null ? Loc.Get(titleKey) : "", Loc.Get(bodyKey));

        public IEnumerator PlayPrologue()
        {
            var pages = new List<(string, string)> { ("", Loc.Get("story.quote")) };
            for (int i = 1; i <= 6; i++)
                pages.Add(P("story.prologue.title", "story.prologue." + i));
            for (int i = 1; i <= 2; i++)
                pages.Add(P("story.act1.title", "story.act1." + i));
            for (int i = 1; i <= 2; i++)
                pages.Add(P("story.act2.title", "story.act2." + i));
            storyBack.color = Color.black;
            yield return Pages(pages, true);
        }

        public void ShowLore(string id)
        {
            storyBack.color = new Color(0.02f, 0.02f, 0.04f, 0.92f);
            StartCoroutine(Pages(new List<(string, string)> { (Loc.Get($"lore.{id}.title"), Loc.Get($"lore.{id}.text")) }, false, 0.3f));
        }

        public void ShowTitle(BiomeDef def)
        {
            GameHUD.Instance?.ShowTitle(def.DisplayName, def.isPassage ? def.Subtitle : def.Subtitle, def.titleColor);
            if (!def.isPassage && !AutoplayDirector.Active)
                Subtitles(new[] { $"biome.{def.locKey}.intro" }, 5f);
        }

        public IEnumerator PlayEnding(bool newBossCell, float time, int kills, int gold, BaseDifficulty diff, int bossCells)
        {
            storyBack.color = Color.black;
            var pages = new List<(string, string)>();
            for (int i = 1; i <= 4; i++)
                pages.Add(P("story.ending.title", "story.ending." + i));
            string stats = Loc.Get("story.ending.stats", UIKit.FormatTime(time), kills, gold, Difficulty.Label(diff), bossCells);
            pages.Add((Loc.Get("story.ending.title"), (newBossCell ? Loc.Get("story.ending.bc") + "\n\n" : "") + stats + "\n\n" + Loc.Get("ending.credits")));
            yield return Pages(pages, false);
        }

        // ------------------------------------------------------------- death

        public IEnumerator ShowDeath(int cells, int gold, float time, int kills, string biome, Action<bool> choose)
        {
            int deaths = SaveSystem.Data.stats.deaths;
            int line = (deaths - 1) % 5 + 1;
            bool chosen = false;
            var page = new MenuPage
            {
                title = () => Loc.Get("death.title"),
                body = () => Loc.Get("story.death.title") + "\n" + Loc.Get("story.death." + line) + "\n\n"
                             + Loc.Get("death.stats", UIKit.FormatTime(time), kills, biome) + "\n"
                             + Loc.Get("death.cells_lost", cells, gold),
                canBack = false,
            };
            page.Add(MenuItem.Button(() => Loc.Get("death.retry"), () =>
            {
                chosen = true;
                menu.CloseAll();
                choose(true);
            }));
            page.Add(MenuItem.Button(() => Loc.Get("death.menu"), () =>
            {
                chosen = true;
                menu.CloseAll();
                choose(false);
            }));
            menu.Push(page);
            float waited = 0f;
            while (!chosen)
            {
                waited += Time.unscaledDeltaTime;
                if (AutoplayDirector.Active && waited > 1.5f)
                {
                    chosen = true;
                    menu.CloseAll();
                    choose(AutoplayDirector.Instance != null && AutoplayDirector.Instance.retryOnDeath);
                }
                yield return null;
            }
        }

        // -------------------------------------------------------- dialogue

        public void Say(string speaker, string text)
        {
            sayName.Text = speaker;
            sayText.Text = text;
            sayUntil = Time.unscaledTime + Mathf.Clamp(text.Length * 0.06f, 2.5f, 6f);
            sayRoot.gameObject.SetActive(true);
        }

        public void Subtitles(string[] keys, float each = 3.2f)
        {
            if (subtitles != null)
                StopCoroutine(subtitles);
            subtitles = StartCoroutine(SubtitleRoutine(keys, each));
        }

        IEnumerator SubtitleRoutine(string[] keys, float each)
        {
            foreach (var k in keys)
            {
                sayName.Text = "";
                sayText.Text = Loc.Get(k);
                sayRoot.gameObject.SetActive(true);
                sayUntil = Time.unscaledTime + each;
                yield return new WaitForSecondsRealtime(each);
            }
            subtitles = null;
        }
    }
}
