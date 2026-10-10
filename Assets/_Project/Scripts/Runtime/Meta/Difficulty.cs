using UnityEngine;

namespace DeadCells.Meta
{
    /// <summary>
    /// Base difficulty (chosen at New Game) stacked with Boss Cells (0-5,
    /// unlocked one at a time by winning at the highest unlocked level, as in
    /// Dead Cells). From 2 Boss Cells the run continues past the Time Keeper
    /// to the Observatory and the Collector; from 4 the Malaise sets in.
    /// </summary>
    public static class Difficulty
    {
        public const int MaxBossCells = 5;
        public const int TrueEndBossCells = 2;
        public const int MalaiseBossCells = 4;
        public const float MalaiseMax = 10f;

        static RunState Run => SaveSystem.Data.run;

        static float Base(float easy, float normal, float hard) => Run.difficulty switch
        {
            BaseDifficulty.Easy => easy,
            BaseDifficulty.Hard => hard,
            _ => normal,
        };

        public static float EnemyHealth => Base(0.7f, 1f, 1.3f) * (1f + 0.15f * Run.bossCells)
                                           * (Run.mode == RunMode.Custom ? SaveSystem.Data.settings.customEnemyHealth : 1f);
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
        public static float EnemyWindupScale => Base(1.6f, 1.25f, 1f) * Mathf.Max(0.7f, 1f - 0.05f * Run.bossCells);

        // ------------------------------------------------------------ malaise

        public static bool MalaiseActive => Run.bossCells >= MalaiseBossCells && Run.mode != RunMode.BossRush;

        /// <summary>Seconds in a biome for one Malaise stack.</summary>
        public static float MalaiseInterval => Run.bossCells >= 5 ? 32f : 45f;

        public static int MalaiseStacks => MalaiseActive ? Mathf.FloorToInt(Run.malaise) : 0;

        /// <summary>Damage the player takes: assist mode and Malaise.</summary>
        public static float PlayerDamageTaken =>
            (SaveSystem.Data.settings.assist ? SaveSystem.Data.settings.assistDamage : 1f) * (1f + 0.06f * MalaiseStacks);

                public static string Label(BaseDifficulty d) => Loc.Get("difficulty." + d.ToString().ToLowerInvariant());
    }
}
