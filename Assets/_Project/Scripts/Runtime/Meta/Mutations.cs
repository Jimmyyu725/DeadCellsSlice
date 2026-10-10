using System.Collections.Generic;
using DeadCells.Combat;
using DeadCells.Items;
using UnityEngine;

namespace DeadCells.Meta
{
    /// <summary>
    /// Passive mutations (Dead Cells' Guillain): up to three per run, one picked
    /// in each passage. Some are free, the rest are unlocked at the Collector.
    /// Combat code asks this class for multipliers and reports kills / hits.
    /// </summary>
    public static class Mutations
    {
        public const int Slots = 3;

        public class Def
        {
            public string id;
            public ItemColor color;
            public int cost;     // cells at the Collector (0 = available from the start)
        }

        public static readonly Def[] All =
        {
            new Def { id = "combo", color = ItemColor.Brutality },
            new Def { id = "vengeance", color = ItemColor.Survival },
            new Def { id = "necromancy", color = ItemColor.Survival },
            new Def { id = "tranquility", color = ItemColor.Tactics },
            new Def { id = "tough", color = ItemColor.Survival },
            new Def { id = "swift", color = ItemColor.Tactics },
            new Def { id = "archer", color = ItemColor.Tactics, cost = 30 },
            new Def { id = "tactician", color = ItemColor.Tactics, cost = 40 },
            new Def { id = "second_wind", color = ItemColor.Survival, cost = 30 },
            new Def { id = "yolo", color = ItemColor.Survival, cost = 60 },
            new Def { id = "parry_master", color = ItemColor.Survival, cost = 40 },
            new Def { id = "vampire", color = ItemColor.Brutality, cost = 50 },
            new Def { id = "toxic", color = ItemColor.Tactics, cost = 35 },
            new Def { id = "pyromania", color = ItemColor.Brutality, cost = 35 },
            new Def { id = "greed", color = ItemColor.None, cost = 25 },
            new Def { id = "killer", color = ItemColor.Brutality, cost = 45 },
        };

        static SaveData D => SaveSystem.Data;
        public static List<string> Active => D.run.mutations;

        public static bool Has(string id) => D.run.mutations.Contains(id);

        public static bool IsUnlocked(Def m) => m.cost <= 0 || D.meta.mutationsUnlocked.Contains(m.id);

        public static Def Get(string id)
        {
            foreach (var m in All)
                if (m.id == id)
                    return m;
            return null;
        }

        /// <summary>Equip a mutation (replacing `replace` when all slots are full).</summary>
        public static void Take(string id, string replace = null)
        {
            var list = D.run.mutations;
            if (list.Contains(id))
                return;
            if (replace != null)
                list.Remove(replace);
            if (list.Count >= Slots)
                return;
            list.Add(id);
            D.run.mutationPicked = true;
            if (list.Count >= Slots)
                Achievements.Unlock("mutant");
            Player.PlayerController.Main?.RecalculateStats(false);
            SaveSystem.Save();
        }

        // ---------------------------------------------------------- state

        static int comboStacks;
        static float comboUntil, vengeanceUntil;

        public static void ResetRunState()
        {
            comboStacks = 0;
            comboUntil = vengeanceUntil = 0f;
        }

        public static void OnKill(Player.PlayerController p)
        {
            if (Has("combo"))
            {
                comboStacks = Time.time < comboUntil ? Mathf.Min(3, comboStacks + 1) : 1;
                comboUntil = Time.time + 4f;
            }
            if (Has("necromancy") && p != null)
                p.Health.Heal(p.Health.maxHealth * 0.025f);
        }

        public static void OnHurt()
        {
            if (Has("vengeance"))
                vengeanceUntil = Time.time + 5f;
        }

        /// <summary>Once per run: survive a killing blow with 40% health (consumes the mutation).</summary>
        public static bool TryRevive(Player.PlayerController p)
        {
            if (!Has("yolo") || p == null)
                return false;
            D.run.mutations.Remove("yolo");
            p.Health.SetCurrent(p.Health.maxHealth * 0.4f);
            p.Health.InvulnerableUntil = Time.time + 2f;
            FX.JuiceEngine.Instance?.Embers(p.transform.position + Vector3.up, 40, new Color(3f, 2.4f, 1f));
            FX.JuiceEngine.Instance?.Popup(p.transform.position + Vector3.up * 2.6f, Loc.Get("mutation.yolo.name"), new Color(1f, 0.85f, 0.4f), true);
            Audio.Sfx.Play("pickup.scroll");
            return true;
        }

        // ---------------------------------------------------------- multipliers

        public static float HealthMultiplier => Has("tough") ? 1.2f : 1f;
        public static float SpeedMultiplier => Has("swift") ? 1.15f : 1f;
        public static float RecoveryMultiplier => Has("second_wind") ? 1.6f : 1f;
        public static float GoldMultiplier => Has("greed") ? 1.4f : 1f;
        public static float CritBonus => Has("killer") ? 0.3f : 0f;
        public static float ParryWindowMultiplier => Has("parry_master") ? 1.5f : 1f;
        public static float ParryDamageMultiplier => Has("parry_master") ? 2f : 1f;
        public static float MeleeLifesteal => Has("vampire") ? 0.05f : 0f;

        public static float CooldownMultiplier(ItemDef item) =>
            item != null && item.kind == ItemKind.Skill && Has("tactician") ? 0.7f : 1f;

        public static float StatusDuration(SkillEffect e) => e switch
        {
            SkillEffect.Poison or SkillEffect.Bleed when Has("toxic") => 1.5f,
            SkillEffect.Fire when Has("pyromania") => 1.3f,
            _ => 1f,
        };

        /// <summary>Damage multiplier from mutations for a hit with `item` on `target`.</summary>
        public static float Damage(ItemDef item, Health target, Player.PlayerController p)
        {
            float m = 1f;
            if (Has("combo") && Time.time < comboUntil)
                m *= 1f + 0.15f * comboStacks;
            if (Has("vengeance") && Time.time < vengeanceUntil)
                m *= 1.4f;
            if (Has("tranquility") && p != null && p.Health.Current >= p.Health.maxHealth * 0.8f)
                m *= 1.25f;
            if (Has("archer") && item != null && item.kind == ItemKind.Bow)
                m *= 1.25f;
            if (Has("pyromania") && target != null && (target.GetComponent<StatusEffects>()?.Burning ?? false))
                m *= 1.3f;
            return m;
        }
    }
}
