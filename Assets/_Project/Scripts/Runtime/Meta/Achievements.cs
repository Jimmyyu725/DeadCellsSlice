using System;
using System.Collections.Generic;
using UnityEngine;

namespace DeadCells.Meta
{
    /// <summary>
    /// Achievement definitions and unlocking. Names and descriptions live in
    /// the string tables as `ach.&lt;id&gt;.name` / `ach.&lt;id&gt;.desc`.
    /// Runs that used cheats cannot unlock anything.
    /// </summary>
    public static class Achievements
    {
        public static readonly string[] All =
        {
            "awaken", "first_blood", "parry_10", "slam_kill", "promenade", "ossuary", "stilt", "lung",
            "guardian", "timekeeper", "bc1", "bc4", "hard_win", "no_hit_biome", "speedrun", "collector",
            "big_spender", "lore_all", "teleport_10", "deaths_10", "arsenal",
        };

        public static event Action<string> Unlocked;

        public static bool Has(string id) => SaveSystem.Data.achievements.Contains(id);

        public static int Count => SaveSystem.Data.achievements.Count;

        public static void Unlock(string id)
        {
            var data = SaveSystem.Data;
            if (data.achievements.Contains(id) || Array.IndexOf(All, id) < 0)
                return;
            if (data.run.active && data.run.cheatsUsed)
                return;
            data.achievements.Add(id);
            SaveSystem.Save();
            Debug.Log("[DC] achievement: " + id);
            Unlocked?.Invoke(id);
        }

        /// <summary>Check counters that cross a threshold.</summary>
        public static void CheckThresholds()
        {
            var d = SaveSystem.Data;
            if (d.stats.parries >= 10) Unlock("parry_10");
            if (d.stats.teleports >= 10) Unlock("teleport_10");
            if (d.stats.deaths >= 10) Unlock("deaths_10");
            if (d.stats.goldSpent >= 2000) Unlock("big_spender");
            if (d.meta.unlockedItems.Count >= 5) Unlock("collector");
            if (d.run.weaponsKilledWith.Count >= 6) Unlock("arsenal");
        }

        public static IEnumerable<string> Locked()
        {
            foreach (var id in All)
                if (!Has(id))
                    yield return id;
        }
    }
}
