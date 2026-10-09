using System;

namespace DeadCells.Meta
{
    /// <summary>
    /// Cheat toggles. Unlocked by typing CHURN on the main menu; usable from
    /// the pause menu. Any use marks the run so it cannot earn achievements.
    /// </summary>
    public static class Cheats
    {
        public const string Code = "CHURN";

        public static bool GodMode { get; private set; }
        public static bool OneHitKills { get; private set; }
        public static bool NoCooldowns { get; private set; }

        public static event Action Changed;

        public static bool Unlocked => SaveSystem.Data.settings.cheatsUnlocked;

        public static void UnlockMenu()
        {
            SaveSystem.Data.settings.cheatsUnlocked = true;
            SaveSystem.Save();
        }

        static void MarkUsed()
        {
            SaveSystem.Data.run.cheatsUsed = true;
            Changed?.Invoke();
        }

        public static void SetGodMode(bool on)
        {
            GodMode = on;
            if (on) MarkUsed(); else Changed?.Invoke();
        }

        public static void SetOneHitKills(bool on)
        {
            OneHitKills = on;
            if (on) MarkUsed(); else Changed?.Invoke();
        }

        public static void SetNoCooldowns(bool on)
        {
            NoCooldowns = on;
            if (on) MarkUsed(); else Changed?.Invoke();
        }

        /// <summary>For one-shot cheats (gold, cells, unlocks, skips).</summary>
        public static void Use() => MarkUsed();

        public static void ResetToggles()
        {
            GodMode = OneHitKills = NoCooldowns = false;
            Changed?.Invoke();
        }
    }
}
