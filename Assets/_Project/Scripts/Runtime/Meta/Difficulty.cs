using UnityEngine;

namespace DeadCells.Meta
{
    /// <summary>
    /// Base difficulty (chosen at New Game) stacked with Boss Cells (0-4,
    /// unlocked one at a time by beating the Time Keeper at the highest
    /// unlocked level, as in Dead Cells).
    /// </summary>
    public static class Difficulty
    {
        public const int MaxBossCells = 4;

        static RunState Run => SaveSystem.Data.run;

        static float Base(float easy, float normal, float hard) => Run.difficulty switch
        {
            BaseDifficulty.Easy => easy,
            BaseDifficulty.Hard => hard,
            _ => normal,
        };

        public static float EnemyHealth => Base(0.7f, 1f, 1.3f) * (1f + 0.15f * Run.bossCells);
        public static float EnemyDamage => Base(0.6f, 1f, 1.35f) * (1f + 0.2f * Run.bossCells);
        public static float EnemyCount => Base(0.85f, 1f, 1.15f) + 0.06f * Run.bossCells;
        public static float EliteChance => Base(0.04f, 0.08f, 0.14f) + 0.04f * Run.bossCells;
        public static float RewardMultiplier => Base(0.9f, 1f, 1.15f) + 0.1f * Run.bossCells;
        public static int ExtraStartFlasks => Run.difficulty == BaseDifficulty.Easy ? 1 : 0;

        /// <summary>How much of the flask the passage fountain refills (Boss Cells take it away).</summary>
        public static float FountainRefill => Run.bossCells switch
        {
            0 => 1f,
            1 => Run.difficulty == BaseDifficulty.Hard ? 0.5f : 1f,
            2 => 0.5f,
            _ => 0f,
        };

        /// <summary>Telegraph slow-down: lower difficulty gives longer wind-ups.</summary>
        public static float EnemyWindupScale => Base(1.35f, 1f, 0.85f) * Mathf.Max(0.7f, 1f - 0.05f * Run.bossCells);

        public static string Label(BaseDifficulty d) => Loc.Get("difficulty." + d.ToString().ToLowerInvariant());
    }
}
