using System.Collections;
using System.Linq;
using DeadCells.CameraRig;
using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.Enemies;
using DeadCells.Environment;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.UI;
using Unity.Cinemachine;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// Run flow in the story order: Oubliette → passage → Promenade → passage →
    /// Ossuary (Royal Guardian) → passage → Stilt Village → passage →
    /// Clockmaker's Lung (Time Keeper). Generates each area, saves at every
    /// entrance (Continue resumes there), handles death, the ending, currency,
    /// kills, teleports and in-run cheats.
    /// </summary>
    public class RunManager : MonoBehaviour
    {
        public BiomeDef[] biomes = new BiomeDef[0];
        public BiomeDef passage;
        public PlayerController player;
        public Transform levelRoot;
        public Camera cam;
        public CinemachineCamera vcam;
        public CameraBounds cameraBounds;
        public Light keyLight;
        public Light rimLight;
        public DCAtmosphere atmosphere;
        public AmbientParticles ambient;
        public MapSystem map;

        public static RunManager Instance { get; private set; }

        BuiltLevel level;
        BiomeDef current;
        string entrySnapshot;
        bool transitioning;
        bool ended;

        public BuiltLevel Level => level;

        /// <summary>Seed of the current level: LevelGenerator.Generate(Current, LevelSeed) rebuilds it exactly.</summary>
        public int LevelSeed { get; private set; }

        /// <summary>Tile cell of a world position (x right, y up; the level grid / map coordinates).</summary>
        public static Vector2Int Cell(Vector3 world) => new Vector2Int(Mathf.FloorToInt(world.x), Mathf.FloorToInt(world.y + 0.05f));

        public RoomInfo RoomAt(Vector2Int cell)
        {
            if (level == null)
                return null;
            foreach (var r in level.data.rooms)
                if (r.rect.Contains(cell))
                    return r;
            return null;
        }

        /// <summary>Hit taken by the player (after damage): a cursed run dies on any hit.</summary>
        public void OnPlayerHurt()
        {
            if (Run.curse <= 0 || Cheats.GodMode || player == null || player.Health.IsDead)
                return;
            Run.curse = 0;
            GameHUD.Instance?.Toast(Loc.Get("hud.curse_killed"), new Color(1f, 0.35f, 0.4f));
            player.Health.InvulnerableUntil = 0f;
            player.Health.TakeDamage(new DamageInfo { amount = 999999f, hitPoint = player.transform.position + Vector3.up, effect = -1 });
        }

        /// <summary>One line that pins down a spot for a bug report.</summary>
        public string LocationReport(Vector2Int cell)
        {
            var room = RoomAt(cell);
            string roomText = room != null ? $"{room.template} ({room.kind}) @{room.rect.xMin},{room.rect.yMin}" : "-";
            return $"v{Meta.Changelog.Latest} | {(current != null ? current.id : "?")} | seed {LevelSeed} | X {cell.x} Y {cell.y} | room {roomText}";
        }
        public BiomeDef Current => current;
        public bool InPassage => Run.inPassage;
        public Transform EntityParent => level != null ? level.root.transform.Find("Entities") : null;
        public int BiomeDepth => current != null ? current.depth : 0;
        public bool Transitioning => transitioning;

        static RunState Run => SaveSystem.Data.run;

        public static int MaxFlaskCharges => 1 + SaveSystem.Data.meta.flaskLevel + Difficulty.ExtraStartFlasks;

        public static int TotalLore => Instance != null ? Instance.biomes.Sum(b => b != null ? b.lore.Length : 0) : 15;

        // ------------------------------------------------------------ lifecycle

        void Awake()
        {
            Instance = this;
        }

        void OnDestroy()
        {
            if (Instance == this)
                Instance = null;
            EnemyBase.Killed -= OnEnemyKilled;
        }

        /// <summary>Set by the main menu's New Game so the next run opens with the prologue.</summary>
        public static bool PrologueRequested;

        public static void NewRun(BaseDifficulty difficulty, int bossCells)
        {
            var d = SaveSystem.Data;
            d.run = new RunState
            {
                active = true,
                difficulty = difficulty,
                bossCells = Mathf.Clamp(bossCells, 0, Mathf.Min(d.meta.bossCellsUnlocked, Difficulty.MaxBossCells)),
                seed = Random.Range(1, int.MaxValue),
                primary = "melee_cleaver",
                secondary = "",
                skill1 = "",
                skill2 = "",
            };
            d.run.flaskCharges = MaxFlaskCharges;
            d.run.gold = d.meta.keptGold;
            d.meta.keptGold = 0;
            d.stats.runs++;
            Cheats.ResetToggles();
            Mutations.ResetRunState();
            SaveSystem.Save();
        }

        void Start()
        {
            if (!Run.active)
                NewRun(BaseDifficulty.Normal, 0);
            EnemyBase.Killed += OnEnemyKilled;
            player.Died += OnPlayerDied;
            player.Health.Damaged += (info, result) =>
            {
                if (result == DamageResult.Hit || result == DamageResult.Killed)
                    Run.tookDamageThisBiome = true;
            };
            StartCoroutine(Begin());
        }

        IEnumerator Begin()
        {
            bool fresh = Run.time <= 0.01f && Run.biome == 0 && !Run.inPassage;
            var ui = GameUI.Instance;
            bool autoplaySkips = AutoplayDirector.Active && !AutoplayDirector.Instance.allowPrologue;
            // The prologue plays on the very first run, and again only when the
            // player starts a New Game from the menu with "skip intro" off; never on Retry.
            bool wantPrologue = !SaveSystem.Data.meta.introSeen || PrologueRequested;
            PrologueRequested = false;
            if (fresh && ui != null && !autoplaySkips && wantPrologue)
            {
                player.Freeze(true);
                Audio.Music.Play("music.menu");
                yield return ui.PlayPrologue();
                SaveSystem.Data.meta.introSeen = true;
                SaveSystem.Save();
            }
            yield return Enter(Run.inPassage ? passage : biomes[Mathf.Clamp(Run.biome, 0, biomes.Length - 1)], fresh);
        }

        void Update()
        {
            if (!transitioning && !ended && !GamePause.Paused)
            {
                Run.time += Time.unscaledDeltaTime;
                SaveSystem.Data.stats.playTime += Time.unscaledDeltaTime;
            }
            Interactable.Scan(player);
        }

        void OnApplicationQuit()
        {
            // Quitting mid-area keeps the run, resumed from this area's entrance.
            if (Run.active && entrySnapshot != null)
                RestoreEntry();
            SaveSystem.Save();
        }

        void RestoreEntry()
        {
            var restored = JsonUtility.FromJson<RunState>(entrySnapshot);
            restored.cheatsUsed |= Run.cheatsUsed;
            SaveSystem.Data.run = restored;
        }

        /// <summary>Pause menu "save and quit".</summary>
        public void SaveAndQuit()
        {
            if (Run.active && entrySnapshot != null)
                RestoreEntry();
            SaveSystem.Save();
            SceneFlow.LoadMenu();
        }

        public void AbandonRun()
        {
            Run.active = false;
            SaveSystem.Save();
            SceneFlow.LoadMenu();
        }

        // --------------------------------------------------------------- areas

        IEnumerator Enter(BiomeDef def, bool wake)
        {
            transitioning = true;
            var ui = GameUI.Instance;
            var hud = GameHUD.Instance;
            player.Freeze(true);
            hud?.Fade(true);
            yield return new WaitForSecondsRealtime(0.45f);

            if (level != null)
                Destroy(level.root);
            foreach (var p in Projectile.Live.ToArray())
                if (p != null)
                    Destroy(p.gameObject);
            current = def;
            if (def.isPassage)
                Run.mutationPicked = false; // a fresh mutation choice in every passage
            int index = def.isPassage ? 100 + Run.biome : Run.biome;
            int seed = Run.seed + index * 7919;
            LevelSeed = seed;
            var data = LevelGenerator.Generate(def, seed);
            level = LevelBuilder.Build(data, def, levelRoot, seed);
            ApplyAtmosphere(def);
            Audio.Music.ForBiome(def.id);
            if (map != null)
                map.Setup(data, def.liquidMaterial != null && def.liquidMaterial.HasProperty("_Color") ? def.liquidMaterial.GetColor("_Color") : new Color(0.5f, 0.3f, 0.8f));
            if (cameraBounds != null)
                cameraBounds.levelBounds = level.bounds;

            player.RecalculateStats(false);
            if (Run.health > 0f)
                player.Health.SetCurrent(Run.health);
            else
                player.Health.ResetHealth();
            player.Combat.LoadFromRun();
            player.Teleport(level.playerStart + Vector3.up * 0.05f);
            if (vcam != null)
                vcam.PreviousStateIsValid = false;
            // The statue at the entrance is known from the start.
            var first = level.teleporters.OrderBy(t => (t.transform.position - level.playerStart).sqrMagnitude).FirstOrDefault();
            first?.Discover(false);

            Run.tookDamageThisBiome = false;
            Run.biomeStartTime = Run.time;
            Run.biomeKills = 0;
            Run.health = player.Health.Current;
            entrySnapshot = JsonUtility.ToJson(Run);
            SaveSystem.Save();

            yield return null;
            hud?.Fade(false);
            if (!def.isPassage)
            {
                if (def.depth == 1) Achievements.Unlock("promenade");
                if (def.depth == 2) Achievements.Unlock("ossuary");
                if (def.depth == 3) Achievements.Unlock("stilt");
                if (def.depth == 4) Achievements.Unlock("lung");
            }
            ui?.ShowTitle(def);
            Audio.Sfx.Play("area.enter", def.isPassage ? 0.6f : 1f);
            if (wake)
            {
                player.Freeze(false);
                player.PlayWakeUp();
                Achievements.Unlock("awaken");
                if (ui != null && !AutoplayDirector.Active)
                    ui.Subtitles(new[] { "story.wake.1", "story.wake.2", "story.wake.3", "story.wake.4" });
            }
            else
            {
                player.Freeze(false);
            }
            transitioning = false;
        }

        void ApplyAtmosphere(BiomeDef def)
        {
            if (atmosphere != null)
            {
                atmosphere.fogColor = def.fogColor;
                atmosphere.fogDensity = def.fogDensity;
                atmosphere.ambientFill = def.ambient;
            }
            if (cam != null)
                cam.backgroundColor = def.fogColor.gamma;
            RenderSettings.ambientLight = def.ambientLight;
            if (keyLight != null)
            {
                keyLight.color = def.keyColor;
                keyLight.intensity = def.keyIntensity;
                keyLight.transform.rotation = Quaternion.Euler(def.keyEuler);
            }
            if (rimLight != null)
            {
                rimLight.color = def.rimColor;
                rimLight.intensity = def.rimIntensity;
            }
            ambient?.Apply(def.motesA, def.motesB, def.embersA, def.embersB, def.rainUp);
        }

        /// <summary>Exit door used.</summary>
        public void ExitReached()
        {
            if (transitioning || ended)
                return;
            if (current != null && current.isPassage)
            {
                Run.inPassage = false;
                Run.health = player.Health.Current;
                StartCoroutine(Enter(biomes[Mathf.Clamp(Run.biome, 0, biomes.Length - 1)], false));
                return;
            }
            if (!Run.tookDamageThisBiome)
                Achievements.Unlock("no_hit_biome");
            if (Run.biome >= biomes.Length - 1)
            {
                StartCoroutine(Ending());
                return;
            }
            Run.biome++;
            Run.inPassage = true;
            Run.health = player.Health.Current;
            StartCoroutine(Enter(passage, false));
        }

        // ------------------------------------------------------------ teleport

        /// <summary>Safety net: back to the nearest discovered teleporter (or the area entrance).</summary>
        public void TeleportToNearest()
        {
            if (transitioning || level == null)
                return;
            Vector3 p = player.transform.position;
            Teleporter best = null;
            float bestD = float.MaxValue;
            foreach (var t in level.teleporters)
            {
                if (t == null || !t.Discovered)
                    continue;
                float d = (t.transform.position - p).sqrMagnitude;
                if (d < bestD)
                {
                    bestD = d;
                    best = t;
                }
            }
            if (best != null)
                TeleportTo(best);
            else
                player.Teleport(level.playerStart + Vector3.up * 0.05f);
        }

        public void TeleportTo(Teleporter target)
        {
            if (transitioning || target == null)
                return;
            StartCoroutine(TeleportRoutine(target));
        }

        IEnumerator TeleportRoutine(Teleporter target)
        {
            transitioning = true;
            var juice = JuiceEngine.Instance;
            player.Freeze(true);
            juice?.Embers(player.transform.position + Vector3.up, 30, new Color(1.6f, 0.8f, 3.2f));
            player.squash.Punch(new Vector2(0.6f, 1.5f));
            Audio.Sfx.Play("teleport.warp");
            GameHUD.Instance?.Fade(true);
            yield return new WaitForSecondsRealtime(0.35f);
            player.Teleport(target.transform.position + new Vector3(1.2f, 0.05f, -target.transform.position.z));
            if (vcam != null)
                vcam.PreviousStateIsValid = false;
            SaveSystem.Data.stats.teleports++;
            Achievements.CheckThresholds();
            yield return new WaitForSecondsRealtime(0.1f);
            GameHUD.Instance?.Fade(false);
            juice?.Embers(player.transform.position + Vector3.up, 30, new Color(1.6f, 0.8f, 3.2f));
            player.squash.Punch(new Vector2(1.4f, 0.7f));
            player.Freeze(false);
            transitioning = false;
        }

        // ---------------------------------------------------------- currency

        public void AddGold(int amount)
        {
            amount = Mathf.RoundToInt(amount * Difficulty.RewardMultiplier * Mutations.GoldMultiplier
                                      * (1f + 0.3f * ItemForge.AmuletCount(Affix.GoldFind)));
            Run.gold += amount;
            Run.goldEarned += amount;
            GameHUD.Instance?.PulseGold();
        }

        public void AddCells(int amount)
        {
            Run.cells += amount;
            GameHUD.Instance?.PulseCells();
        }

        public void SpendGold(int amount) => Run.gold = Mathf.Max(0, Run.gold - amount);

        // --------------------------------------------------------------- kills

        void OnEnemyKilled(EnemyBase enemy, DamageInfo info)
        {
            var d = SaveSystem.Data;
            Run.kills++;
            Run.biomeKills++;
            d.stats.kills++;
            Achievements.Unlock("first_blood");
            if (info.weaponId == "slam")
                Achievements.Unlock("slam_kill");
            else if (!string.IsNullOrEmpty(info.weaponId) && !Run.weaponsKilledWith.Contains(info.weaponId))
                Run.weaponsKilledWith.Add(info.weaponId);
            Achievements.CheckThresholds();

            Vector3 at = enemy.transform.position + Vector3.up * 0.8f;
            float reward = Difficulty.RewardMultiplier;
            int cells = Mathf.RoundToInt(enemy.cellReward * reward * (enemy.IsElite ? 3f : 1f));
            if (Random.value < 0.6f + 0.3f * (enemy.IsElite ? 1f : 0f))
                Loot.DropCells(at, Mathf.Max(1, cells));
            if (Random.value < 0.45f || enemy.IsElite)
                Loot.DropGold(at, Mathf.RoundToInt(Random.Range(6, 14) * (1f + 0.6f * BiomeDepth) * (enemy.IsElite ? 5f : 1f)));
            if (enemy.IsElite || enemy.IsBoss)
                Loot.DropBlueprint(at + Vector3.right);
            else if (Random.value < 0.012f)
                Loot.DropBlueprint(at);
            if (enemy.IsElite && Random.value < 0.5f)
                Loot.DropRandomItem(at + Vector3.left, BiomeDepth + 1);
            if (enemy.IsElite && Random.value < 0.12f)
                Loot.DropAmulet(at + Vector3.left * 1.6f, BiomeDepth + 1);
            if (Run.curse > 0)
            {
                Run.curse--;
                GameHUD.Instance?.Toast(Run.curse > 0 ? Loc.Get("hud.curse_left", Run.curse) : Loc.Get("hud.curse_lifted"),
                    Run.curse > 0 ? new Color(0.9f, 0.5f, 1f) : new Color(0.6f, 1f, 0.7f));
            }

            if (enemy.IsBoss)
                OnBossKilled(enemy);
        }

        void OnBossKilled(EnemyBase boss)
        {
            JuiceEngine.Instance?.HitStop(0.25f);
            if (current != null && current.depth == 2)
                Achievements.Unlock("guardian");
            if (current != null && current.depth == biomes.Length - 1)
                Achievements.Unlock("timekeeper");
            Loot.DropCells(boss.transform.position + Vector3.up * 2f, Mathf.RoundToInt(40 * Difficulty.RewardMultiplier));
            Loot.DropScroll(boss.transform.position + Vector3.up * 1.5f + Vector3.left * 2f);
        }

        IEnumerator Ending()
        {
            ended = true;
            transitioning = true;
            player.Freeze(true);
            var d = SaveSystem.Data;
            Achievements.Unlock("timekeeper");
            if (Run.bossCells >= 1) Achievements.Unlock("bc1");
            if (Run.bossCells >= 4) Achievements.Unlock("bc4");
            if (Run.bossCells >= 1) Outfits.Grant("bc1");
            if (Run.bossCells >= 3) Outfits.Grant("bc3");
            if (Run.difficulty == BaseDifficulty.Hard) Achievements.Unlock("hard_win");
            if (Run.time < 3600f) Achievements.Unlock("speedrun");
            // Beating the highest unlocked level unlocks the next Boss Cell.
            bool newCell = false;
            int next = Mathf.Min(Difficulty.MaxBossCells, Run.bossCells + 1);
            if (Run.bossCells >= d.meta.bossCellsUnlocked && next > d.meta.bossCellsUnlocked)
            {
                d.meta.bossCellsUnlocked = next;
                newCell = true;
            }
            d.stats.wins++;
            if (d.stats.bestTime <= 0f || Run.time < d.stats.bestTime)
                d.stats.bestTime = Run.time;
            var summary = (time: Run.time, kills: Run.kills, gold: Run.goldEarned, diff: Run.difficulty, cells: Run.bossCells);
            Run.active = false;
            SaveSystem.Save();
            var ui = GameUI.Instance;
            Audio.Music.Play("music.menu", 2f);
            Audio.Music.Ambience(null, 2f);
            if (ui != null)
                yield return ui.PlayEnding(newCell, summary.time, summary.kills, summary.gold, summary.diff, summary.cells);
            SceneFlow.LoadMenu();
        }

        // --------------------------------------------------------------- death

        void OnPlayerDied()
        {
            if (ended)
                return;
            ended = true;
            var d = SaveSystem.Data;
            d.stats.deaths++;
            int lostCells = Run.cells, lostGold = Run.gold;
            var summary = (time: Run.time, kills: Run.kills, biome: current != null ? current.DisplayName : "");
            var difficulty = Run.difficulty;
            int bossCells = Run.bossCells;
            Run.active = false;
            d.meta.keptGold = Mathf.RoundToInt(lostGold * 0.1f * d.meta.goldKeep);
            Achievements.CheckThresholds();
            SaveSystem.Save();
            StartCoroutine(DeathRoutine(lostCells, lostGold, summary.time, summary.kills, summary.biome, difficulty, bossCells));
        }

        IEnumerator DeathRoutine(int cells, int gold, float time, int kills, string biome, BaseDifficulty difficulty, int bossCells)
        {
            Audio.Music.Play("music.death", 0.6f);
            Audio.Music.Ambience(null, 2f);
            yield return new WaitForSecondsRealtime(1.2f);
            var ui = GameUI.Instance;
            if (ui == null)
            {
                SceneFlow.LoadMenu();
                yield break;
            }
            yield return ui.ShowDeath(cells, gold, time, kills, biome, retry =>
            {
                if (retry)
                {
                    NewRun(difficulty, bossCells);
                    SceneFlow.LoadGame();
                }
                else
                {
                    SceneFlow.LoadMenu();
                }
            });
        }

        // -------------------------------------------------------------- cheats

        public void CheatSkipBiome()
        {
            Cheats.Use();
            if (current != null && !current.isPassage && level.boss != null && !level.boss.IsDead)
                level.boss.GetComponent<Health>().TakeDamage(new DamageInfo { amount = 999999f, source = player.gameObject, effect = -1 });
            else
                ExitReached();
        }

        public void CheatRevealMap()
        {
            Cheats.Use();
            map?.RevealAll();
            foreach (var t in level.teleporters)
                t.Discover(false);
        }

        public void CheatFullHeal()
        {
            Cheats.Use();
            player.Health.ResetHealth();
            Run.flaskCharges = MaxFlaskCharges;
        }
    }
}
