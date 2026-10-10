using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace DeadCells.Meta
{
    /// <summary>Normal story run, the date-seeded Daily Challenge, a Custom run or the Boss Rush.</summary>
    public enum RunMode
    {
        Normal,
        Daily,
        Custom,
        BossRush,
    }

    public enum BaseDifficulty
    {
        Easy,
        Normal,
        Hard,
    }

    [Serializable]
    public class Settings
    {
        public Language language = Language.Chinese;
        [Range(0f, 1f)] public float screenShake = 1f;
        public int flameIndex;
        public bool cheatsUnlocked;
        public bool fullscreen;
        public bool skipIntro;
        [Range(0f, 1f)] public float musicVolume = 0.7f;
        [Range(0f, 1f)] public float sfxVolume = 0.85f;
        [Tooltip("Show area / seed / room / tile X-Y on the HUD and under the map cursor (bug reports).")]
        public bool showCoords;
        // Assist mode (disables achievements while on).
        public bool assist;
        [Range(0.25f, 1f)] public float assistDamage = 0.5f;
        public bool assistRevive = true;
        // Custom mode options.
        public int customStartBiome;
        public bool customAllItems = true;
        public float customEnemyHealth = 1f;
        public int customStartGold = 500;
        public bool customScrolls;
    }

    /// <summary>Survives death: unlocks bought from the Collector and boss-cell progress.</summary>
    [Serializable]
    public class MetaProgress
    {
        public List<string> unlockedItems = new List<string>();
        public List<string> blueprints = new List<string>();      // found, not yet unlocked
        public int flaskLevel;            // extra flask charges bought (0..3)
        public int forgeLevel;            // better drop quality (0..3)
        public bool backpackUnlocked;
        public List<string> mutationsUnlocked = new List<string>();
        public int goldKeep;              // gold kept through death, 10% per level (0..3)
        public int keptGold;              // gold carried into the next run
        public List<string> runes = new List<string>();            // vine, ram, spider (permanent)
        public string outfit = "prisoner";
        public List<string> outfitsUnlocked = new List<string>();
        public int vitalityLevel;         // +10% max HP per level (0..5)
        public int bossCellsUnlocked;     // highest boss-cell level selectable (0..5)
        public List<string> dailyResults = new List<string>();   // "yyyyMMdd:seconds" best per day
        public bool trueEndSeen;
        public bool introSeen;
        public List<string> loreRead = new List<string>();
    }

    /// <summary>The run in progress (saved at every biome entrance for Continue).</summary>
    [Serializable]
    public class RunState
    {
        public bool active;
        public BaseDifficulty difficulty = BaseDifficulty.Normal;
        public int bossCells;
        public int biome;                 // index into the story biome order
        public bool inPassage;            // between biomes (Collector room)
        public bool variantRoute;         // the current biome is the branch (variant) route
        public RunMode mode;
        public bool trueEndRoute;         // past the Time Keeper with enough Boss Cells: the Observatory
        public float malaise;             // 0..10 stacks (4+ Boss Cells)
        public string dailyDate = "";
        public bool assistReviveUsed;     // once per area
        public int seed;
        public float health = -1f;
        public int gold;
        public int cells;
        public int scrollsVitality;       // legacy (pre-0.6): migrated into survival
        public int scrollsPower;          // legacy (pre-0.6): migrated into brutality
        public int brutality;
        public int tactics;
        public int survival;
        public int flaskCharges;
        public string primary = "melee_cleaver";
        public string secondary = "shield_frontline";
        public string skill1 = "";
        public string skill2 = "";
        // Item rolls ("quality:affix,affix", see ItemForge) for the slots above.
        public string primaryRoll = "";
        public string secondaryRoll = "";
        public string skill1Roll = "";
        public string skill2Roll = "";
        public string amulet = "";
        public string amuletRoll = "";
        public string backpack = "";
        public string backpackRoll = "";
        public List<string> mutations = new List<string>();
        public bool mutationPicked;       // one mutation per passage
        public int curse;                 // kills left before a cursed chest's curse lifts (any hit kills meanwhile)
        public int biomeKills;
        public int goldEarned;
        public float time;
        public int kills;
        public bool cheatsUsed;
        public bool tookDamageThisBiome;
        public float biomeStartTime;
        public List<string> weaponsKilledWith = new List<string>();
    }

    [Serializable]
    public class Stats
    {
        public int runs;
        public int deaths;
        public int wins;
        public int kills;
        public int parries;
        public int teleports;
        public int goldSpent;
        public int cellsSpent;
        public float bestTime;
        public float playTime;
    }

    [Serializable]
    public class SaveData
    {
        public int version = 1;
        public Settings settings = new Settings();
        public MetaProgress meta = new MetaProgress();
        public RunState run = new RunState();
        public Stats stats = new Stats();
        public List<string> achievements = new List<string>();
    }

    /// <summary>JSON save file in the persistent data folder, written atomically.</summary>
    public static class SaveSystem
    {
        static SaveData data;

        // Test-bot runs keep their own file so they never touch the player's progress.
        static readonly bool autoplay = System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-autoplay") >= 0;

        public static string FilePath => Path.Combine(Application.persistentDataPath, autoplay ? "save_autoplay.json" : "save.json");

        public static SaveData Data
        {
            get
            {
                if (data == null)
                    Load();
                return data;
            }
        }

        public static event Action Saved;

        public static void Load()
        {
            data = null;
            try
            {
                if (File.Exists(FilePath))
                    data = JsonUtility.FromJson<SaveData>(File.ReadAllText(FilePath));
            }
            catch (Exception e)
            {
                Debug.LogWarning("[DC] save unreadable, starting fresh: " + e.Message);
                // Keep the damaged file for inspection instead of overwriting it silently.
                try
                {
                    File.Copy(FilePath, FilePath + ".corrupt", true);
                }
                catch (Exception)
                {
                    // Nothing else to do; a fresh save follows.
                }
            }
            data ??= new SaveData();
            // 0.6: power/vitality scrolls became Brutality/Survival.
            if (data.run.scrollsPower > 0 || data.run.scrollsVitality > 0)
            {
                data.run.brutality += data.run.scrollsPower;
                data.run.survival += data.run.scrollsVitality;
                data.run.scrollsPower = data.run.scrollsVitality = 0;
            }
            Loc.Current = data.settings.language;
        }

        public static void Save()
        {
            if (data == null)
                return;
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(FilePath));
                string tmp = FilePath + ".tmp";
                File.WriteAllText(tmp, JsonUtility.ToJson(data, true));
                if (File.Exists(FilePath))
                    File.Delete(FilePath);
                File.Move(tmp, FilePath);
                Saved?.Invoke();
            }
            catch (Exception e)
            {
                Debug.LogError("[DC] save failed: " + e.Message);
            }
        }

        /// <summary>Erase everything (Options → Reset progress).</summary>
        public static void Reset()
        {
            var keepSettings = Data.settings;
            data = new SaveData { settings = keepSettings };
            Save();
        }
    }
}
