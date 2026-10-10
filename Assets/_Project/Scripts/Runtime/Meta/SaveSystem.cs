using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace DeadCells.Meta
{
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
    }

    /// <summary>Survives death: unlocks bought from the Collector and boss-cell progress.</summary>
    [Serializable]
    public class MetaProgress
    {
        public List<string> unlockedItems = new List<string>();
        public List<string> blueprints = new List<string>();      // found, not yet unlocked
        public int flaskLevel;            // extra flask charges bought (0..3)
        public int vitalityLevel;         // +10% max HP per level (0..5)
        public int bossCellsUnlocked;     // highest boss-cell level selectable (0..4)
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
        public int seed;
        public float health = -1f;
        public int gold;
        public int cells;
        public int scrollsVitality;
        public int scrollsPower;
        public int flaskCharges;
        public string primary = "melee_cleaver";
        public string secondary = "shield_frontline";
        public string skill1 = "";
        public string skill2 = "";
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
