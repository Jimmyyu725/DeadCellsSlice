using UnityEngine;

namespace DeadCells.Meta
{
    /// <summary>
    /// Permanent traversal runes, each carried by a rune guardian (an elite)
    /// the first time through its biome: Vine grows vines from bulbs, Ram lets
    /// the ground pound smash rune floors, Spider allows wall-jumping.
    /// </summary>
    public static class Runes
    {
        public const string Vine = "vine", Ram = "ram", Spider = "spider";
        public static readonly string[] All = { Vine, Ram, Spider };

        public static bool Has(string id) => !string.IsNullOrEmpty(id) && SaveSystem.Data.meta.runes.Contains(id);

        public static Color ColorOf(string id) => id switch
        {
            Vine => new Color(0.9f, 3f, 0.6f),
            Ram => new Color(3.4f, 1.4f, 0.3f),
            _ => new Color(2.2f, 0.9f, 3.4f),
        };

        public static void Grant(string id)
        {
            var meta = SaveSystem.Data.meta;
            if (string.IsNullOrEmpty(id) || meta.runes.Contains(id))
                return;
            meta.runes.Add(id);
            if (meta.runes.Count >= All.Length)
                Achievements.Unlock("runes_all");
            SaveSystem.Save();
        }
    }
}
