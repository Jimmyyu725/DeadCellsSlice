using System.Collections.Generic;
using System.IO;
using System.Linq;
using DeadCells.Enemies;
using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.Run;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace DeadCells.Core
{
    /// <summary>
    /// Verification driver enabled by -autoplay. Survives scene loads: walks
    /// the main menu (optional captures), starts a run and plays it with a
    /// path-finding bot over the generated tile graph (fight, skills, flask,
    /// exit doors). Captures screenshots, logs errors, area entries and
    /// timings, and quits after -autoplaySeconds.
    ///
    /// Args: -autoplay -captureDir D -autoplaySeconds S -captureInterval I
    ///       -burst t0 t1 -autoplayBiome N -autoplayDifficulty easy|normal|hard
    ///       -autoplayMenu (capture menu pages) -autoplayGod (cheat god mode)
    ///       -autoplaySkip S (skip to the next area every S seconds: screenshot tour)
    ///       -autoplayLang en|zh
    /// </summary>
    public class AutoplayDirector : MonoBehaviour, IInputSource
    {
        public static bool Active { get; private set; }
        public static AutoplayDirector Instance { get; private set; }

        public float duration = 60f;
        public float captureInterval = 1f;
        public string captureDir = "Captures";
        public Vector2 burstWindow = new Vector2(-1f, -1f);
        public float burstInterval = 1f / 30f;
        public int startBiome;
        public BaseDifficulty difficulty = BaseDifficulty.Normal;
        public bool captureMenu;
        public bool god;
        public float skipEvery;
        public string language = "";
        public bool warpBoss;
        public bool uiTour;
        public bool dieTest;
        public bool noVsync;
        public bool shaftTest;
        public bool retryOnDeath;
        public bool allowPrologue;
        public float dieAfter;
        public bool breakPost;
        public bool armoryTest;
        public bool armoryFight;
        public string armoryFilter = "";
        public bool jumpTest;
        public bool cancelTest;
        public bool systemsTest;
        InputFrame? overrideInput;
        bool holdAttack;
        bool standStill;
        bool diedOnce;
        bool scripted;
        float scriptJumpAt, scriptHoldUntil;
        int shaftAreas;
        bool uiTourDone;
        string warpedArea = "";

        float startTime;
        float nextCapture;
        int captureIndex;
        StreamWriter log;
        int errors;
        float lastSkip;
        string lastArea = "";
        // Bot state.
        float attackTimer, jumpHoldUntil, skillTimer, stuckTimer, pathTimer;
        Vector3 lastProgressPos;
        readonly List<Vector2Int> path = new List<Vector2Int>();
        int pathIndex;
        float dropUntil;
        float jumpDir = 1f;
        float fightStuck, lastFightX, ignoreFightUntil;
        readonly FrameTiming[] frameTimings = new FrameTiming[1];

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Boot()
        {
            var args = System.Environment.GetCommandLineArgs();
            if (System.Array.IndexOf(args, "-autoplay") < 0)
                return;
            var go = new GameObject("AutoplayDirector");
            go.SetActive(false); // configure before Awake opens the log in the capture folder
            DontDestroyOnLoad(go);
            var d = go.AddComponent<AutoplayDirector>();
            for (int i = 0; i < args.Length; i++)
            {
                string next = i + 1 < args.Length ? args[i + 1] : "";
                switch (args[i])
                {
                    case "-captureDir": d.captureDir = next; break;
                    case "-autoplaySeconds": float.TryParse(next, out d.duration); break;
                    case "-captureInterval": float.TryParse(next, out d.captureInterval); break;
                    case "-autoplayBiome": int.TryParse(next, out d.startBiome); break;
                    case "-autoplaySkip": float.TryParse(next, out d.skipEvery); break;
                    case "-autoplayMenu": d.captureMenu = true; break;
                    case "-autoplayGod": d.god = true; break;
                    case "-autoplayLang": d.language = next; break;
                    case "-autoplayWarpBoss": d.warpBoss = true; break;
                    case "-autoplayUiTour": d.uiTour = true; break;
                    case "-autoplayDie": d.dieTest = true; break;
                    case "-autoplayNoVsync": d.noVsync = true; break;
                    case "-autoplayShaftTest": d.shaftTest = true; break;
                    case "-autoplayRetry": d.retryOnDeath = true; break;
                    case "-autoplayPrologue": d.allowPrologue = true; break;
                    case "-autoplayDieAfter": float.TryParse(next, out d.dieAfter); break;
                    case "-autoplayBreakPost": d.breakPost = true; break;
                    case "-autoplayArmory": d.armoryTest = true; break;
                    case "-autoplayArmoryFight": d.armoryTest = true; d.armoryFight = true; break;
                    case "-autoplayArmoryFilter": d.armoryFilter = next ?? ""; break;
                    case "-autoplayJumpTest": d.jumpTest = true; break;
                    case "-autoplayCancelTest": d.cancelTest = true; break;
                    case "-autoplaySystems": d.systemsTest = true; break;
                    case "-autoplayDifficulty":
                        d.difficulty = next == "easy" ? BaseDifficulty.Easy : next == "hard" ? BaseDifficulty.Hard : BaseDifficulty.Normal;
                        break;
                    case "-burst":
                        if (i + 2 < args.Length && float.TryParse(args[i + 1], out float b0) && float.TryParse(args[i + 2], out float b1))
                            d.burstWindow = new Vector2(b0, b1);
                        break;
                }
            }
            Active = true;
            Instance = d;
            go.SetActive(true);
        }

        void Awake()
        {
            Directory.CreateDirectory(captureDir);
            log = new StreamWriter(Path.Combine(captureDir, "autoplay_log.txt"), false) { AutoFlush = true };
            Application.logMessageReceived += OnLog;
            startTime = Time.realtimeSinceStartup;
            nextCapture = 1f;
            if (language == "en") SaveSystem.Data.settings.language = Language.English;
            if (language == "zh") SaveSystem.Data.settings.language = Language.Chinese;
            Loc.Current = SaveSystem.Data.settings.language;
            SceneManager.sceneLoaded += (s, _) => log.WriteLine($"[{Elapsed:F1}] scene {s.name}");
        }

        void OnDestroy()
        {
            Application.logMessageReceived -= OnLog;
            log?.Dispose();
        }

        float Elapsed => Time.realtimeSinceStartup - startTime;

        void OnLog(string condition, string stackTrace, LogType type)
        {
            if (type == LogType.Error || type == LogType.Exception || type == LogType.Assert)
            {
                errors++;
                log?.WriteLine($"[{Elapsed:F2}] {type}: {condition}\n{stackTrace}");
            }
            else if (condition.StartsWith("[DC]"))
            {
                log?.WriteLine($"[{Elapsed:F2}] {condition}");
            }
        }

        /// <summary>Main menu asks this to start the run the bot will play.</summary>
        public void StartRun()
        {
            RunManager.NewRun(difficulty, 0);
            SaveSystem.Data.run.biome = Mathf.Clamp(startBiome, 0, 4);
            SaveSystem.Save();
            SceneFlow.LoadGame();
        }

        public void Capture(string tag)
        {
            string path = Path.Combine(captureDir, $"frame_{captureIndex++:000}_{Elapsed:000.0}s_{tag}.png");
            ScreenCapture.CaptureScreenshot(path);
            log?.WriteLine($"[{Elapsed:F1}] capture {path}");
        }

        // ------------------------------------------------------------- loop

        void Update()
        {
            if (noVsync && QualitySettings.vSyncCount != 0)
            {
                QualitySettings.vSyncCount = 0;
                Application.targetFrameRate = 1000;
            }
            var player = PlayerController.Main;
            if (player != null && !ReferenceEquals(player.InputSource, this))
            {
                player.InputSource = this;
                if (god)
                    Cheats.SetGodMode(true);
            }
            var rm = RunManager.Instance;
            if (rm != null && rm.Current != null && rm.Level != null && !rm.Transitioning)
            {
                string area = rm.Current.id + (rm.InPassage ? "/passage" : "");
                if (area != lastArea)
                {
                    lastArea = area;
                    lastSkip = Elapsed;
                    path.Clear();
                    log.WriteLine($"[{Elapsed:F1}] area {area} rooms={rm.Level.data.rooms.Count} size={rm.Level.data.width}x{rm.Level.data.height} enemies={rm.Level.enemies.Count} hp={player?.Health.Current:F0}");
                    Invoke(nameof(CaptureArea), 2.5f);
                    if (breakPost)
                        Invoke(nameof(BreakPost), 1.5f);
                    if (cancelTest && rm.InPassage)
                    {
                        cancelTest = false;
                        skipEvery = 0f;
                        StartCoroutine(CancelTest());
                    }
                    if (systemsTest && rm.InPassage)
                    {
                        systemsTest = false;
                        skipEvery = 0f;
                        StartCoroutine(SystemsTest(rm));
                    }
                    if (jumpTest && rm.InPassage)
                    {
                        jumpTest = false;
                        skipEvery = 0f;
                        StartCoroutine(JumpTest());
                    }
                    if (armoryTest && rm.InPassage != armoryFight)
                    {
                        armoryTest = false;
                        skipEvery = 0f;
                        StartCoroutine(ArmoryTest(rm));
                    }
                    if (shaftTest && !rm.InPassage && shaftAreas < 3)
                    {
                        shaftAreas++;
                        StartCoroutine(ShaftTest(rm));
                    }
                    if (uiTour && !uiTourDone && !rm.InPassage)
                    {
                        uiTourDone = true;
                        StartCoroutine(UiTour());
                    }
                }
                if (warpBoss && warpedArea != area && Elapsed - lastSkip > 3f)
                {
                    warpedArea = area;
                    WarpToBoss(rm);
                }
                if (dieAfter > 0f && !diedOnce && Elapsed > dieAfter && player != null)
                {
                    diedOnce = true;
                    skipEvery = 0f;
                    god = false;
                    Cheats.SetGodMode(false);
                    player.Health.InvulnerableUntil = 0f;
                    log.WriteLine($"[{Elapsed:F1}] scripted death in {area}");
                    player.Health.TakeDamage(new Combat.DamageInfo { amount = 99999f, source = gameObject, effect = -1 });
                }
                if (skipEvery > 0f && Elapsed - lastSkip > skipEvery && !rm.Transitioning)
                {
                    lastSkip = Elapsed;
                    log.WriteLine($"[{Elapsed:F1}] skip from {area} kills={SaveSystem.Data.run.kills}");
                    rm.CheatSkipBiome();
                }
            }
        }

        void CaptureArea() => Capture("area_" + lastArea.Replace('/', '_'));

        /// <summary>Test hook: shield and turn responsiveness in the middle of a combo.</summary>
        System.Collections.IEnumerator CancelTest()
        {
            yield return new WaitForSecondsRealtime(1.5f);
            var p = PlayerController.Main;
            var db = Items.ItemDatabase.Instance;
            p.Combat.Equip(0, db.Get("melee_rusty"));
            p.Combat.Equip(1, db.Get("shield_frontline"));
            Cheats.SetGodMode(true);
            // 1) Shield while a combo is swinging.
            overrideInput = new InputFrame { primaryPressed = true, primaryHeld = true };
            yield return null;
            overrideInput = new InputFrame { primaryHeld = true };
            yield return new WaitForSeconds(0.12f);
            var stateBefore = p.State;
            overrideInput = new InputFrame { primaryHeld = true, secondaryPressed = true, secondaryHeld = true };
            int frames = 0;
            while (p.State != PlayerState.Block && frames < 120)
            {
                frames++;
                yield return null;
                overrideInput = new InputFrame { primaryHeld = true, secondaryHeld = true };
            }
            log.WriteLine($"[{Elapsed:F1}] cancel test: shield raised {frames} frame(s) after the press (state before {stateBefore})");
            Capture("cancel_shield");
            overrideInput = new InputFrame();
            yield return new WaitForSeconds(0.4f);
            // 2) Turn around mid-swing.
            int facing = p.Facing;
            overrideInput = new InputFrame { primaryPressed = true, primaryHeld = true };
            yield return null;
            overrideInput = new InputFrame { primaryHeld = true };
            yield return new WaitForSeconds(0.08f);
            overrideInput = new InputFrame { primaryHeld = true, moveX = -facing };
            frames = 0;
            while (p.Facing == facing && frames < 120)
            {
                frames++;
                yield return null;
            }
            log.WriteLine($"[{Elapsed:F1}] cancel test: turned around {frames} frame(s) after reversing (state {p.State})");
            // 3) Hold attack for 2 s and count swings.
            overrideInput = new InputFrame { primaryHeld = true };
            int startHits = p.Combat.ActionsStarted;
            yield return new WaitForSeconds(2f);
            log.WriteLine($"[{Elapsed:F1}] cancel test: {p.Combat.ActionsStarted - startHits} swings in 2 s while held");
            overrideInput = null;
            // Coordinate readout for bug reports.
            SaveSystem.Data.settings.showCoords = true;
            yield return new WaitForSecondsRealtime(0.3f);
            var rmc = RunManager.Instance;
            log.WriteLine($"[{Elapsed:F1}] coords: {rmc.LocationReport(RunManager.Cell(p.transform.position))}");
            Capture("coords_hud");
        }

        /// <summary>
        /// Test hook (0.6 systems, in the passage): scroll choice, mutations,
        /// rolled items + HUD card, amulet, backpack, recovery health, the
        /// Blacksmith / Mutator / Tailor menus, a timed door, a cursed chest and
        /// finally the curse killing the player on the next hit.
        /// </summary>
        System.Collections.IEnumerator SystemsTest(RunManager rm)
        {
            yield return new WaitForSecondsRealtime(2f);
            var p = PlayerController.Main;
            var db = Items.ItemDatabase.Instance;
            var w = WorldPrefabs.Instance;
            var run = SaveSystem.Data.run;
            var ui = UI.GameUI.Instance;
            Cheats.SetGodMode(true);
            overrideInput = new InputFrame();   // hold still: the bot would walk out of the passage
            Capture("sys_passage");
            log.WriteLine($"[{Elapsed:F1}] sys: npcs mutator={Object.FindObjectsByType<NpcInteractable>(FindObjectsSortMode.None).Length} worldPrefabs mutator={(w.mutator != null)} smith={(w.blacksmith != null)} tailor={(w.tailor != null)} timed={(w.timedDoor != null)} shroud={(w.curseShroud != null)}");

            // Scrolls: two colours offered, each pick raises one stat.
            float hp0 = p.Health.maxHealth;
            var scrollGo = Object.Instantiate(w.scroll, p.transform.position + Vector3.right * 1.5f, Quaternion.identity);
            var scroll = scrollGo.GetComponent<ScrollPickup>();
            yield return null;
            scroll.Interact(p);
            yield return new WaitForSecondsRealtime(0.6f);
            Capture("sys_scroll_menu");
            yield return null;
            yield return null;
            ui.CloseAllForTest();
            scroll.Apply(p, Items.ItemColor.Survival);
            log.WriteLine($"[{Elapsed:F1}] sys: scroll B/T/S={run.brutality}/{run.tactics}/{run.survival} maxHP {hp0:F0}->{p.Health.maxHealth:F0}");

            // Mutations.
            foreach (var n in Object.FindObjectsByType<NpcInteractable>(FindObjectsSortMode.None))
            {
                if (n.role == NpcInteractable.Role.Merchant || n.role == NpcInteractable.Role.Collector)
                    continue;
                p.Teleport(n.transform.position + Vector3.left * 1.2f + Vector3.up * 0.1f);
                yield return new WaitForSecondsRealtime(0.5f);
                n.Interact(p);
                yield return new WaitForSecondsRealtime(0.7f);
                Capture("sys_npc_" + n.role.ToString().ToLowerInvariant());
                yield return null;
                yield return null;
                ui.CloseAllForTest();
                yield return new WaitForSecondsRealtime(0.3f);
            }
            float hp1 = p.Health.maxHealth;
            Mutations.Take("tough");
            Mutations.Take("combo");
            Mutations.Take("yolo");
            log.WriteLine($"[{Elapsed:F1}] sys: mutations [{string.Join(",", run.mutations)}] maxHP {hp1:F0}->{p.Health.maxHealth:F0}");

            // Rolled items: a legendary on the floor shows the coloured card with affixes.
            var rusty = db.Get("melee_rusty");
            var legendary = Items.ItemForge.Build(rusty, Items.ItemForge.Legendary, new[] { Items.Affix.Damage, Items.Affix.Bleed, Items.Affix.CritDamage });
            float baseDmg = rusty.combo[0].damage, rolledDmg = legendary.combo[0].damage;
            var drop = Object.Instantiate(w.itemDrop, p.transform.position + Vector3.right * 1.2f, Quaternion.identity);
            drop.GetComponent<ItemPickup>().Setup(legendary, 0);
            yield return new WaitForSecondsRealtime(0.8f);
            Capture("sys_card_legendary");
            yield return null;
            yield return null;
            log.WriteLine($"[{Elapsed:F1}] sys: legendary '{Items.ItemForge.FullName(legendary)}' dmg {baseDmg:F1}->{rolledDmg:F1} roll='{Items.ItemForge.Encode(legendary)}' decode={(Items.ItemForge.Decode(rusty, Items.ItemForge.Encode(legendary)).combo[0].damage):F1}");
            drop.GetComponent<ItemPickup>().Interact(p);
            yield return new WaitForSecondsRealtime(0.3f);
            log.WriteLine($"[{Elapsed:F1}] sys: primary now '{Items.ItemForge.FullName(p.Combat.Slot(0))}' saved='{run.primaryRoll}'");

            // Amulet.
            Loot.DropAmulet(p.transform.position + Vector3.right * 1.0f, 2);
            yield return new WaitForSecondsRealtime(0.6f);
            var amuletPickup = Object.FindObjectsByType<ItemPickup>(FindObjectsSortMode.None).FirstOrDefault(i => i.CardItem != null && i.CardItem.kind == Items.ItemKind.Amulet);
            if (amuletPickup != null)
            {
                p.Teleport(amuletPickup.transform.position + Vector3.left * 0.6f + Vector3.up * 0.1f);
                yield return new WaitForSecondsRealtime(0.5f);
                Capture("sys_card_amulet");
                yield return null;
                yield return null;
                amuletPickup.Interact(p);
            }
            yield return new WaitForSecondsRealtime(0.3f);
            var am = p.Combat.Amulet;
            log.WriteLine($"[{Elapsed:F1}] sys: amulet '{(am != null ? Items.ItemForge.FullName(am) : "none")}' affixes [{(am != null ? string.Join(",", am.affixes) : "")}] maxHP {p.Health.maxHealth:F0}");

            // Backpack.
            SaveSystem.Data.meta.backpackUnlocked = true;
            p.Combat.Equip(0, db.Get("melee_rusty"));
            bool s1 = p.Combat.SwapBackpack();
            string after1 = p.Combat.Slot(0)?.id ?? "none";
            p.Combat.Equip(0, db.Get("melee_spear"));
            bool s2 = p.Combat.SwapBackpack();
            log.WriteLine($"[{Elapsed:F1}] sys: backpack swap1={s1} primary={after1} swap2={s2} primary={p.Combat.Slot(0)?.id} pack={p.Combat.Backpack?.id}");

            // Recovery health: a hit leaves an orange bar that attacks win back.
            Cheats.SetGodMode(false);
            p.Health.InvulnerableUntil = 0f;
            float before = p.Health.Current;
            p.Health.TakeDamage(new Combat.DamageInfo { amount = 30f, source = gameObject, effect = -1 });
            yield return new WaitForSecondsRealtime(0.5f);
            log.WriteLine($"[{Elapsed:F1}] sys: hit {before:F0}->{p.Health.Current:F0} recoverable={p.Recoverable:F1}");
            Capture("sys_recovery_bar");
            Cheats.SetGodMode(true);

            // Timed door: open in time, drops land.
            var td = Object.Instantiate(w.timedDoor, p.transform.position + new Vector3(3f, 0f, 1.2f), Quaternion.identity);
            var tdc = td.GetComponent<TimedDoor>();
            tdc.limit = run.time + 90f;
            yield return new WaitForSecondsRealtime(0.8f);
            Capture("sys_timed_door");
            int pickups0 = Object.FindObjectsByType<ItemPickup>(FindObjectsSortMode.None).Length;
            tdc.Interact(p);
            yield return new WaitForSecondsRealtime(1.6f);
            Capture("sys_timed_door_open");
            log.WriteLine($"[{Elapsed:F1}] sys: timed door opened, item pickups {pickups0}->{Object.FindObjectsByType<ItemPickup>(FindObjectsSortMode.None).Length}");
            var expired = Object.Instantiate(w.timedDoor, p.transform.position + new Vector3(-3f, 0f, 1.2f), Quaternion.identity).GetComponent<TimedDoor>();
            expired.limit = 1f;
            yield return null;
            log.WriteLine($"[{Elapsed:F1}] sys: expired door prompt '{expired.Prompt}'");

            // Cursed chest.
            var chestGo = Object.Instantiate(w.chest, p.transform.position + new Vector3(-2f, 0f, 0.6f), Quaternion.identity);
            var chest = chestGo.GetComponent<Chest>();
            chest.Curse(w.curseShroud);
            yield return new WaitForSecondsRealtime(0.8f);
            Capture("sys_cursed_chest");
            log.WriteLine($"[{Elapsed:F1}] sys: cursed chest prompt '{chest.Prompt}'");
            chest.Interact(p);
            yield return new WaitForSecondsRealtime(1.2f);
            Capture("sys_cursed_open");
            log.WriteLine($"[{Elapsed:F1}] sys: curse={run.curse}");

            // YOLO saves the first lethal hit; the curse makes any hit lethal.
            Cheats.SetGodMode(false);
            god = false;
            p.Health.InvulnerableUntil = 0f;
            p.Health.TakeDamage(new Combat.DamageInfo { amount = 5f, source = gameObject, effect = -1 });
            yield return new WaitForSecondsRealtime(0.5f);
            log.WriteLine($"[{Elapsed:F1}] sys: cursed hit -> dead={p.Health.IsDead} hp={p.Health.Current:F0} yoloLeft={Mutations.Has("yolo")} curse={run.curse}");
            Capture("sys_after_curse");
            overrideInput = null;
        }

        /// <summary>Test hook: measure single and double jump heights from flat floor.</summary>
        System.Collections.IEnumerator JumpTest()
        {
            yield return new WaitForSecondsRealtime(1.5f);
            var p = PlayerController.Main;
            foreach (bool twice in new[] { false, true })
            {
                overrideInput = new InputFrame();
                yield return new WaitForSeconds(0.5f);
                float y0 = p.transform.position.y, best = y0, t0 = Time.time;
                overrideInput = new InputFrame { jumpPressed = true, jumpHeld = true };
                yield return null;
                overrideInput = new InputFrame { jumpHeld = true };
                bool second = false;
                while (Time.time - t0 < 1.6f)
                {
                    best = Mathf.Max(best, p.transform.position.y);
                    if (twice && !second && Time.time - t0 > 0.36f)
                    {
                        second = true;
                        overrideInput = new InputFrame { jumpPressed = true, jumpHeld = true };
                        yield return null;
                        overrideInput = new InputFrame { jumpHeld = true };
                        Capture("double_jump_flip");
                    }
                    yield return null;
                }
                log.WriteLine($"[{Elapsed:F1}] jump test {(twice ? "double" : "single")}: height {best - y0:F2} m");
            }
            overrideInput = null;
        }

        /// <summary>Player chest position in screen pixels, for cropping test captures.</summary>
        static string ScreenTag(PlayerController p)
        {
            var cam = Camera.main;
            if (cam == null)
                return "0x0";
            Vector3 sp = cam.WorldToScreenPoint(p.transform.position + Vector3.up * 1.1f);
            return $"{Mathf.RoundToInt(sp.x)}x{Mathf.RoundToInt(sp.y)}";
        }

        /// <summary>
        /// Test hook: equip every weapon in turn, hold the attack button (the
        /// combo must keep chaining) and capture close-ups mid-swing.
        /// </summary>
        System.Collections.IEnumerator ArmoryTest(RunManager rm)
        {
            yield return new WaitForSecondsRealtime(2f);
            Cheats.SetGodMode(true);
            standStill = true;
            var composer = rm.vcam != null ? rm.vcam.GetComponent<Unity.Cinemachine.CinemachinePositionComposer>() : null;
            float distance = composer != null ? composer.CameraDistance : 0f;
            if (composer != null)
                composer.CameraDistance = 8f;
            var p = PlayerController.Main;
            // Stand in the open: the widest stretch of clear floor in the room.
            // (In fight mode stay at the entrance so enemies come to us.)
            var tiles = rm.Level.data.tiles;
            int bestX = -1, bestRun = 0;
            int floorY = Mathf.FloorToInt(rm.Level.playerStart.y) - 1;
            for (int x = 1, run = 0; x < rm.Level.data.width - 1; x++)
            {
                bool clear = tiles[x, floorY] == Tile.Solid;
                for (int dy = 1; dy <= 5 && clear; dy++)
                    clear = floorY + dy < rm.Level.data.height && tiles[x, floorY + dy] == Tile.Air;
                run = clear ? run + 1 : 0;
                if (run > bestRun)
                {
                    bestRun = run;
                    bestX = x - run + 3; // left end: lunges travel right across the open floor
                }
            }
            foreach (var item in Items.ItemDatabase.Instance.items)
            {
                if (!string.IsNullOrEmpty(armoryFilter) && !item.id.StartsWith(armoryFilter) || item.kind == Items.ItemKind.Amulet)
                    continue;
                if (item.kind == Items.ItemKind.Skill)
                {
                    p.Combat.Equip(2, item);
                    yield return new WaitForSecondsRealtime(0.3f);
                    int before = p.Combat.ActionsStarted;
                    overrideInput = new InputFrame { skill1Pressed = true };
                    yield return null;
                    overrideInput = new InputFrame();
                    yield return new WaitForSeconds(0.45f);
                    Capture($"armory_{item.id}_a_{ScreenTag(p)}");
                    yield return new WaitForSeconds(1.1f);
                    Capture($"armory_{item.id}_b_{ScreenTag(p)}");
                    overrideInput = null;
                    log.WriteLine($"[{Elapsed:F1}] armory {item.id}: skill used={p.Combat.ActionsStarted - before}");
                    yield return new WaitForSecondsRealtime(0.8f);
                    continue;
                }
                if (bestX > 0 && !armoryFight)
                {
                    p.Teleport(new Vector3(bestX + 0.5f, floorY + 1.05f, 0f));
                    p.anim.SetFacing(1);
                    if (rm.vcam != null)
                        rm.vcam.PreviousStateIsValid = false;
                    yield return new WaitForSecondsRealtime(0.3f);
                }
                p.Combat.Equip(0, item);
                yield return new WaitForSecondsRealtime(0.4f);
                int startHits = p.Combat.ActionsStarted;
                holdAttack = true; // shields block while held
                float t0 = Time.time;
                yield return new WaitForSeconds(0.12f);
                Capture($"armory_{item.id}_a_{ScreenTag(p)}");
                yield return new WaitForSeconds(0.3f);
                Capture($"armory_{item.id}_b_{ScreenTag(p)}");
                yield return new WaitForSeconds(0.4f);
                Capture($"armory_{item.id}_c_{ScreenTag(p)}");
                while (Time.time - t0 < 2.2f)
                    yield return null;
                holdAttack = false;
                log.WriteLine($"[{Elapsed:F1}] armory {item.id}: {p.Combat.ActionsStarted - startHits} attacks while held 2.2 s");
                yield return new WaitForSecondsRealtime(0.6f);
            }
            if (composer != null)
                composer.CameraDistance = distance;
            standStill = false;
            log.WriteLine($"[{Elapsed:F1}] armory test done");
        }

        /// <summary>Test hook: wipe the post profile's component list the way a bad reload did.</summary>
        void BreakPost()
        {
            foreach (var v in FindObjectsByType<UnityEngine.Rendering.Volume>())
                if (v.sharedProfile != null)
                    v.sharedProfile.components = null;
            log.WriteLine($"[{Elapsed:F1}] post profile components wiped");
        }

        /// <summary>Physics test: stand at the bottom of each shaft and climb out using jumps only.</summary>
        System.Collections.IEnumerator ShaftTest(RunManager rm)
        {
            yield return new WaitForSecondsRealtime(2f);
            var shafts = new List<RectInt>(rm.Level.data.shafts);
            int tested = 0, passed = 0;
            foreach (var r in shafts)
            {
                if (tested >= 5)
                    break;
                tested++;
                var p = PlayerController.Main;
                p.Teleport(new Vector3(r.xMin + 1.5f, r.yMin + 0.05f, 0f));
                if (rm.vcam != null)
                    rm.vcam.PreviousStateIsValid = false;
                float best = p.transform.position.y;
                float target = r.yMax + 0.9f;
                float t0 = Time.time;
                scripted = true;
                scriptJumpAt = Time.time + 0.3f;
                while (Time.time - t0 < 8f)
                {
                    best = Mathf.Max(best, p.transform.position.y);
                    if (p.Grounded && p.transform.position.y >= target)
                        break;
                    yield return null;
                }
                scripted = false;
                bool ok = p.Grounded && p.transform.position.y >= target;
                if (ok)
                    passed++;
                log.WriteLine($"[{Elapsed:F1}] shaft x={r.xMin} y={r.yMin}..{r.yMax} climb {(ok ? "OK" : "FAIL")} best={best:F2} target={target:F2}");
                Capture($"shaft_{rm.Current.id}_{tested}_{(ok ? "ok" : "fail")}");
                yield return new WaitForSecondsRealtime(0.3f);
            }
            log.WriteLine($"[{Elapsed:F1}] shaft test {rm.Current.id}: {passed}/{tested}");
        }

        InputFrame ScriptedClimb(PlayerController player)
        {
            var f = new InputFrame();
            if (player.Grounded && Time.time >= scriptJumpAt)
            {
                f.jumpPressed = true;
                scriptHoldUntil = Time.time + 0.75f;
                scriptJumpAt = Time.time + 0.95f;
            }
            f.jumpHeld = Time.time < scriptHoldUntil;
            return f;
        }

        /// <summary>Test hook: put the player at the entrance of this area's boss arena.</summary>
        void WarpToBoss(RunManager rm)
        {
            var data = rm.Level.data;
            foreach (var room in data.rooms)
            {
                if (room.kind == null || !room.kind.StartsWith("boss"))
                    continue;
                var p = PlayerController.Main;
                var at = new Vector3(room.rect.xMin + 3.5f, room.rect.yMin + 2.05f, 0f);
                p.Teleport(at);
                if (rm.vcam != null)
                    rm.vcam.PreviousStateIsValid = false;
                log.WriteLine($"[{Elapsed:F1}] warped to {room.kind} at {at}");
                return;
            }
        }

        /// <summary>Test hook: open the in-game screens one by one and capture them.</summary>
        System.Collections.IEnumerator UiTour()
        {
            var ui = UI.GameUI.Instance;
            yield return new WaitForSecondsRealtime(4f);
            ui.OpenPauseForTest();
            yield return new WaitForSecondsRealtime(0.8f);
            Capture("ui_pause");
            yield return null;
            yield return null;
            ui.CloseAllForTest();
            yield return new WaitForSecondsRealtime(0.3f);
            ui.OpenMapForTest();
            yield return new WaitForSecondsRealtime(0.8f);
            Capture("ui_map");
            yield return null;
            yield return null;
            ui.CloseAllForTest();
            yield return new WaitForSecondsRealtime(0.3f);
            ui.OpenCollector();
            yield return new WaitForSecondsRealtime(0.8f);
            Capture("ui_collector");
            yield return null;
            yield return null;
            ui.CloseAllForTest();
            yield return new WaitForSecondsRealtime(0.3f);
            // Teleport: reveal the map, open the statue map at the first teleporter, jump to another.
            var rmTour = RunManager.Instance;
            rmTour.CheatRevealMap();
            var teles = rmTour.Level.teleporters.FindAll(t => t != null);
            if (teles.Count > 1 && !rmTour.Transitioning)
            {
                var p0 = PlayerController.Main;
                p0.Teleport(teles[0].transform.position + new Vector3(0.8f, 0.05f, -teles[0].transform.position.z));
                yield return new WaitForSecondsRealtime(0.5f);
                ui.OpenTeleportMap(teles[0]);
                yield return new WaitForSecondsRealtime(0.8f);
                Capture("ui_teleport_map");
                yield return null;
                yield return null;
                ui.CloseAllForTest();
                var target = teles[teles.Count - 1];
                if (target != null)
                {
                    rmTour.TeleportTo(target);
                    yield return new WaitForSecondsRealtime(1.5f);
                    Capture("ui_teleported");
                    if (target != null)
                        log.WriteLine($"[{Elapsed:F1}] teleported to {PlayerController.Main.transform.position} (target {target.transform.position})");
                }
            }
            // Shop: stand at a priced pedestal with enough gold, buy it.
            ItemPickup pedestal = null;
            foreach (var pick in FindObjectsByType<ItemPickup>())
                if (pick.price > 0)
                {
                    pedestal = pick;
                    break;
                }
            if (pedestal != null && !rmTour.Transitioning)
            {
                SaveSystem.Data.run.gold += pedestal.price;
                var pp = PlayerController.Main;
                pp.Teleport(new Vector3(pedestal.transform.position.x - 0.6f, pedestal.transform.position.y + 0.05f, 0f));
                yield return new WaitForSecondsRealtime(0.8f);
                Capture("ui_shop");
                if (pedestal == null)
                    yield break;
                var before = pp.Combat.Slot(pp.Combat.SlotFor(pedestal.CardItem));
                string bought = pedestal.CardItem != null ? pedestal.CardItem.id : "?";
                pedestal.Interact(pp);
                yield return new WaitForSecondsRealtime(0.8f);
                Capture("ui_bought");
                log.WriteLine($"[{Elapsed:F1}] bought {bought}, replaced {(before != null ? before.id : "nothing")}, gold now {SaveSystem.Data.run.gold}");
            }
            ui.ShowLore("oub1");
            yield return new WaitForSecondsRealtime(0.8f);
            Capture("ui_lore");
            yield return null;
            yield return null;
            ui.CloseAllForTest();
            if (dieTest)
            {
                yield return new WaitForSecondsRealtime(1f);
                var p = PlayerController.Main;
                Cheats.SetGodMode(false);
                p.Health.InvulnerableUntil = 0f;
                p.Health.TakeDamage(new Combat.DamageInfo { amount = 99999f, source = gameObject, effect = -1 });
                yield return new WaitForSecondsRealtime(2.2f);
                Capture("ui_death");
            }
        }

        int intervalFrames, slowFrames;
        float intervalTime, worstFrame;

        void LateUpdate()
        {
            FrameTimingManager.CaptureFrameTimings();
            float frame = Time.unscaledDeltaTime;
            intervalFrames++;
            intervalTime += frame;
            worstFrame = Mathf.Max(worstFrame, frame);
            if (frame > 0.02f)
                slowFrames++;
            float t = Elapsed;
            if (t >= nextCapture)
            {
                bool burst = t >= burstWindow.x && t <= burstWindow.y;
                nextCapture = t + (burst ? burstInterval : captureInterval);
                var p = PlayerController.Main;
                string state = p != null ? $"state={p.State} hp={p.Health.Current:F0} pos={p.transform.position}" : "menu";
                Capture("t");
                FrameTimingManager.CaptureFrameTimings();
                string timing = "";
                if (FrameTimingManager.GetLatestTimings(1, frameTimings) > 0)
                    timing = $" cpu={frameTimings[0].cpuFrameTime:F1}ms main={frameTimings[0].cpuMainThreadFrameTime:F1}ms render={frameTimings[0].cpuRenderThreadFrameTime:F1}ms gpu={frameTimings[0].gpuFrameTime:F1}ms";
                float avg = intervalFrames / Mathf.Max(0.001f, intervalTime);
                log.WriteLine($"[{t:F1}]   {state} fps~{avg:F0} worst={worstFrame * 1000f:F0}ms slow={slowFrames}/{intervalFrames}{timing}");
                intervalFrames = slowFrames = 0;
                intervalTime = worstFrame = 0f;
            }
            if (t >= duration)
            {
                var run = SaveSystem.Data.run;
                log.WriteLine($"audio: {Audio.AudioManager.PlayedCount} effects played, ids: {string.Join(" ", Audio.AudioManager.PlayedIds)}; music={Audio.Music.Current}");
                log.WriteLine($"done. errors={errors} kills={run.kills} biome={run.biome} time={run.time:F0}s fps~{1f / Mathf.Max(0.0001f, Time.smoothDeltaTime):F0}");
                log.Flush();
                enabled = false;
                Application.Quit();
#if UNITY_EDITOR
                UnityEditor.EditorApplication.isPlaying = false;
#endif
            }
        }

        // ------------------------------------------------------------- bot

        public InputFrame Read()
        {
            var f = new InputFrame();
            var player = PlayerController.Main;
            var rm = RunManager.Instance;
            if (player == null || rm == null || rm.Level == null || rm.Transitioning)
                return f;
            if (overrideInput.HasValue)
                return overrideInput.Value;
            if (holdAttack || standStill)
                return new InputFrame { primaryHeld = holdAttack };
            if (scripted)
                return ScriptedClimb(player);
            float dt = Time.deltaTime;
            attackTimer -= dt;
            skillTimer -= dt;
            pathTimer -= dt;
            Vector3 pos = player.transform.position;

            // Drink when low.
            if (player.Health.Normalized < 0.35f && SaveSystem.Data.run.flaskCharges > 0)
                f.flaskPressed = true;

            var target = NearestEnemy(pos, 9f);
            if (target != null && fightStuck > 3f)
            {
                // No progress towards this target: navigate instead for a while.
                ignoreFightUntil = Time.time + 4f;
                fightStuck = 0f;
            }
            if (target != null && Mathf.Abs(target.transform.position.y - pos.y) < 2.2f && Time.time > ignoreFightUntil)
            {
                float dx = target.transform.position.x - pos.x;
                if (Mathf.Abs(dx) > 1.5f)
                    f.moveX = Mathf.Sign(dx);
                else if (Mathf.Sign(dx) != player.Facing)
                    f.moveX = Mathf.Sign(dx);
                // Hop obstacles between us and the target.
                if (f.moveX != 0f && player.Grounded && Physics2D.Raycast((Vector2)pos + Vector2.up * 0.5f, new Vector2(f.moveX, 0f), 0.9f, DCLayers.SolidMask).collider != null)
                {
                    f.jumpPressed = true;
                    jumpHoldUntil = Time.time + 0.45f;
                    jumpDir = f.moveX;
                }
                f.jumpHeld = Time.time < jumpHoldUntil;
                if (!player.Grounded && f.moveX == 0f)
                    f.moveX = jumpDir;
                fightStuck = Mathf.Abs(pos.x - lastFightX) < 0.05f && Mathf.Abs(dx) > 2.2f ? fightStuck + dt : 0f;
                lastFightX = pos.x;
                if (Mathf.Abs(dx) < 2.2f && attackTimer <= 0f)
                {
                    f.primaryPressed = true;
                    attackTimer = 0.16f;
                }
                if (skillTimer <= 0f && Mathf.Abs(dx) < 7f)
                {
                    f.skill1Pressed = true;
                    f.skill2Pressed = Random.value < 0.5f;
                    skillTimer = 1.5f;
                }
                if (Mathf.Abs(dx) < 3f && Random.value < 0.01f)
                    f.dodgePressed = true;
                return f;
            }

            // Interact with doors and teleporters on the way? Doors only (keeps the run moving).
            var it = Interactable.Current;
            if (it is ExitDoor || (it is ItemPickup pick && pick.price == 0 && rm.InPassage == false && Random.value < 0.02f))
                f.interactPressed = true;

            Navigate(player, rm, ref f);
            return f;
        }

        EnemyBase NearestEnemy(Vector3 pos, float range)
        {
            EnemyBase best = null;
            float bestD = range;
            foreach (var e in RunManager.Instance.Level.enemies)
            {
                if (e == null || e.IsDead || !e.Engaged && !e.IsBoss)
                    continue;
                float d = Mathf.Abs(e.transform.position.x - pos.x) + Mathf.Abs(e.transform.position.y - pos.y) * 1.5f;
                if (d < bestD)
                {
                    bestD = d;
                    best = e;
                }
            }
            return best;
        }

        void Navigate(PlayerController player, RunManager rm, ref InputFrame f)
        {
            var data = rm.Level.data;
            Vector3 pos = player.transform.position;
            Vector3 goal = rm.Level.exits.Count > 0 ? rm.Level.exits[rm.Level.exits.Count - 1] : new Vector3(data.width - 4, pos.y, 0f);
            // Boss arenas: fight the boss first.
            if (rm.Level.boss != null && !rm.Level.boss.IsDead)
                goal = rm.Level.boss.transform.position;

            if ((pos - lastProgressPos).sqrMagnitude > 1f)
            {
                lastProgressPos = pos;
                stuckTimer = 0f;
            }
            else
            {
                stuckTimer += Time.deltaTime;
            }

            // Path search is throttled: at most every 0.6 s (or when stuck).
            if (pathTimer <= 0f || (pathIndex >= path.Count && pathTimer < 0.4f) || stuckTimer > 2f)
            {
                pathTimer = 0.6f;
                BotPath.Find(data, Cell(pos), Cell(goal), path);
                pathIndex = 0;
                if (stuckTimer > 2f)
                {
                    f.jumpPressed = true;
                    f.jumpHeld = true;
                    f.moveX = Random.value < 0.5f ? -1f : 1f;
                    stuckTimer = 0f;
                    return;
                }
            }
            if (path.Count == 0)
            {
                f.moveX = Mathf.Sign(goal.x - pos.x);
                return;
            }
            // Advance along the path.
            Vector2Int me = Cell(pos);
            while (pathIndex < path.Count - 1 && (path[pathIndex] - me).sqrMagnitude <= 1)
                pathIndex++;
            var wp = path[Mathf.Min(pathIndex, path.Count - 1)];
            float wx = wp.x + 0.5f - pos.x;
            int wy = wp.y - me.y;
            f.moveX = Mathf.Abs(wx) > 0.25f ? Mathf.Sign(wx) : 0f;
            if (wy > 0 && player.Grounded)
            {
                f.jumpPressed = true;
                jumpHoldUntil = Time.time + 0.12f + wy * 0.1f;
                jumpDir = f.moveX != 0f ? f.moveX : Mathf.Sign(wx);
            }
            // Keep pushing towards a ledge while airborne so the mantle triggers.
            if (!player.Grounded && wy > 0 && f.moveX == 0f)
                f.moveX = jumpDir;
            f.jumpHeld = Time.time < jumpHoldUntil;
            if (wy < -1 && Mathf.Abs(wx) < 0.8f && player.Grounded && Time.time > dropUntil)
            {
                f.down = true;
                f.jumpPressed = true;
                dropUntil = Time.time + 0.5f;
            }
            if (Vector2.Distance(pos, goal) < 2.2f && Interactable.Current is ExitDoor)
                f.interactPressed = true;
        }

        static Vector2Int Cell(Vector3 p) => new Vector2Int(Mathf.FloorToInt(p.x), Mathf.FloorToInt(p.y + 0.1f));
    }

    /// <summary>
    /// BFS over standable cells with the same movement model as
    /// Tools/Rooms/validate_rooms.py (walk, fall, jump ≤3 up/≤4 across, drop
    /// through one-way platforms).
    /// </summary>
    public static class BotPath
    {
        static bool Blocks(LevelData d, int x, int y) => d.At(x, y) == Tile.Solid;
        static bool Free(LevelData d, int x, int y) => !Blocks(d, x, y) && d.At(x, y) != Tile.Liquid && d.At(x, y) != Tile.Spikes;
        static bool Floor(LevelData d, int x, int y) => d.At(x, y) == Tile.Solid || d.At(x, y) == Tile.OneWay;

        static bool Stand(LevelData d, int x, int y) => Free(d, x, y) && Free(d, x, y + 1) && Floor(d, x, y - 1);

        static bool Column(LevelData d, int x, int y0, int y1)
        {
            for (int y = Mathf.Min(y0, y1); y <= Mathf.Max(y0, y1); y++)
                if (Blocks(d, x, y))
                    return false;
            return true;
        }

        static Vector2Int Settle(LevelData d, Vector2Int c)
        {
            for (int i = 0; i < 30 && c.y > 0 && !Stand(d, c.x, c.y); i++)
                c.y--;
            return c;
        }

        static LevelData cachedLevel;
        static readonly Dictionary<Vector2Int, Vector2Int[]> Graph = new Dictionary<Vector2Int, Vector2Int[]>();

        /// <summary>Movement graph over every standable cell, built once per level.</summary>
        static void EnsureGraph(LevelData d)
        {
            if (ReferenceEquals(cachedLevel, d))
                return;
            cachedLevel = d;
            Graph.Clear();
            var buffer = new List<Vector2Int>();
            for (int x = 0; x < d.width; x++)
            for (int y = 1; y < d.height - 1; y++)
            {
                if (!Stand(d, x, y))
                    continue;
                buffer.Clear();
                buffer.AddRange(Neighbours(d, new Vector2Int(x, y)));
                Graph[new Vector2Int(x, y)] = buffer.ToArray();
            }
        }

        public static void Find(LevelData d, Vector2Int from, Vector2Int to, List<Vector2Int> result)
        {
            result.Clear();
            EnsureGraph(d);
            from = Settle(d, from);
            to = Settle(d, to);
            if (!Graph.ContainsKey(from))
                return;
            var prev = new Dictionary<Vector2Int, Vector2Int>();
            var q = new Queue<Vector2Int>();
            q.Enqueue(from);
            prev[from] = from;
            Vector2Int best = from;
            float bestD = float.MaxValue;
            while (q.Count > 0)
            {
                var c = q.Dequeue();
                float dist = Mathf.Abs(c.x - to.x) + Mathf.Abs(c.y - to.y) * 2f;
                if (dist < bestD)
                {
                    bestD = dist;
                    best = c;
                }
                if (c == to)
                    break;
                if (!Graph.TryGetValue(c, out var edges))
                    continue;
                foreach (var n in edges)
                {
                    if (prev.ContainsKey(n))
                        continue;
                    prev[n] = c;
                    q.Enqueue(n);
                }
            }
            var cur = best;
            while (cur != from)
            {
                result.Add(cur);
                cur = prev[cur];
            }
            result.Reverse();
        }

        static IEnumerable<Vector2Int> Neighbours(LevelData d, Vector2Int c)
        {
            int x = c.x, y = c.y;
            for (int dx = -1; dx <= 1; dx += 2)
            {
                int nx = x + dx;
                if (Blocks(d, nx, y) || Blocks(d, nx, y + 1))
                    continue;
                if (Stand(d, nx, y))
                {
                    yield return new Vector2Int(nx, y);
                    continue;
                }
                int fy = y;
                while (fy > 0 && !Floor(d, nx, fy - 1) && !Blocks(d, nx, fy - 1))
                    fy--;
                if (Stand(d, nx, fy))
                    yield return new Vector2Int(nx, fy);
            }
            if (d.At(x, y - 1) == Tile.OneWay)
            {
                int fy = y - 1;
                while (fy > 0 && !(Floor(d, x, fy - 1) && fy - 1 != y - 1) && !Blocks(d, x, fy - 1))
                    fy--;
                if (fy < y && Stand(d, x, fy))
                    yield return new Vector2Int(x, fy);
            }
            // Jumps and drops (same model as Tools/Rooms/validate_rooms.py).
            for (int dy = -6; dy <= 3; dy++)
            {
                for (int dx = -5; dx <= 5; dx++)
                {
                    if (dx == 0 && dy <= 0)
                        continue;
                    if (dy >= 2 && Mathf.Abs(dx) > 4)
                        continue;
                    if (dy == 3 && Mathf.Abs(dx) > 3)
                        continue;
                    int nx = x + dx, ny = y + dy;
                    if (!Stand(d, nx, ny))
                        continue;
                    int apex = Mathf.Max(y, ny);
                    if (!Column(d, x, y, apex + 1) || !Column(d, nx, ny, apex + 1))
                        continue;
                    bool ok = true;
                    int step = dx > 0 ? 1 : -1;
                    for (int cx = x; dx != 0 && cx != nx + step; cx += step)
                        if (Blocks(d, cx, apex) || Blocks(d, cx, apex + 1))
                        {
                            ok = false;
                            break;
                        }
                    if (ok)
                        yield return new Vector2Int(nx, ny);
                }
            }
            // Ledge mantle: jump beside a wall and climb its lip (up to 4 above the feet).
            for (int dx = -1; dx <= 1; dx += 2)
            {
                for (int dy = 4; dy >= 3; dy--)
                {
                    int nx = x + dx, ny = y + dy;
                    if (Stand(d, nx, ny) && Blocks(d, nx, ny - 1) && Column(d, x, y, ny + 1))
                        yield return new Vector2Int(nx, ny);
                }
            }
        }
    }
}
