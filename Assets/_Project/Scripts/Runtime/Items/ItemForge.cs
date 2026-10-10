using System.Collections.Generic;
using System.Linq;
using System.Text;
using DeadCells.Meta;
using UnityEngine;

namespace DeadCells.Items
{
    /// <summary>
    /// Item quality and affixes. A rolled item is a runtime copy of its base
    /// ItemDef with the modifiers written straight into its stats, so every
    /// combat code path picks them up without knowing about rolls. Rolls are
    /// saved as "quality:affix,affix" next to the item id.
    /// </summary>
    public static class ItemForge
    {
        public const int Legendary = 3;
        static readonly Dictionary<string, ItemDef> cache = new Dictionary<string, ItemDef>();

        static readonly Affix[] MeleeAffixes = { Affix.Damage, Affix.VsAfflicted, Affix.Ignite, Affix.Bleed, Affix.Poison, Affix.Freeze, Affix.HealOnKill, Affix.CritDamage, Affix.Lifesteal, Affix.KillBurst, Affix.AttackSpeed, Affix.Oil };
        static readonly Affix[] BowAffixes = { Affix.Damage, Affix.VsAfflicted, Affix.Ignite, Affix.Bleed, Affix.Poison, Affix.Freeze, Affix.HealOnKill, Affix.CritDamage, Affix.Cooldown, Affix.ExtraProjectile, Affix.Pierce, Affix.KillBurst, Affix.Oil };
        static readonly Affix[] ShieldAffixes = { Affix.Damage, Affix.Ignite, Affix.Bleed, Affix.Freeze, Affix.HealOnKill, Affix.Oil };
        static readonly Affix[] SkillAffixes = { Affix.Damage, Affix.Cooldown, Affix.Ignite, Affix.Bleed, Affix.Poison, Affix.Freeze, Affix.KillBurst, Affix.Oil };
        static readonly Affix[] AmuletAffixes = { Affix.MaxHealth, Affix.AllDamage, Affix.GoldFind, Affix.Recovery, Affix.MoveSpeed, Affix.FlaskPower };

        public static Affix[] PoolFor(ItemKind kind) => kind switch
        {
            ItemKind.Melee => MeleeAffixes,
            ItemKind.Bow => BowAffixes,
            ItemKind.Shield => ShieldAffixes,
            ItemKind.Skill => SkillAffixes,
            _ => AmuletAffixes,
        };

        /// <summary>Random quality for a drop at this depth (forge level and Boss Cells raise it).</summary>
        public static int RollQuality(int depth, System.Random rng)
        {
            float forge = SaveSystem.Data.meta.forgeLevel;
            float bc = SaveSystem.Data.run.bossCells;
            double r = rng.NextDouble();
            float legendary = 0.015f + 0.01f * bc + 0.005f * forge;
            float plusPlus = 0.04f * depth + 0.03f * forge;
            float plus = 0.2f + 0.08f * depth + 0.06f * forge;
            if (r < legendary) return Legendary;
            if (r < legendary + plusPlus) return 2;
            if (r < legendary + plusPlus + plus) return 1;
            return 0;
        }

        public static ItemDef Roll(ItemDef def, int depth, System.Random rng = null)
        {
            if (def == null)
                return null;
            rng ??= new System.Random(Random.Range(1, int.MaxValue));
            int q = def.kind == ItemKind.Amulet ? Mathf.Max(1, RollQuality(depth, rng)) : RollQuality(depth, rng);
            int n = q >= Legendary ? 3 : q;
            var pool = PoolFor(def.kind).ToList();
            var picked = new List<Affix>();
            for (int i = 0; i < n && pool.Count > 0; i++)
            {
                var a = pool[rng.Next(pool.Count)];
                pool.Remove(a);
                // One on-hit status per item keeps the effects readable.
                if (IsStatus(a))
                    pool.RemoveAll(IsStatus);
                picked.Add(a);
            }
            return Build(def, q, picked.ToArray());
        }

        static bool IsStatus(Affix a) => a == Affix.Ignite || a == Affix.Bleed || a == Affix.Poison || a == Affix.Freeze || a == Affix.Oil;

        public static string Encode(ItemDef item) =>
            item == null || (item.quality == 0 && (item.affixes == null || item.affixes.Length == 0))
                ? ""
                : item.quality + ":" + string.Join(",", item.affixes.Select(a => ((int)a).ToString()));

        /// <summary>Rebuild a saved item ("" = plain base item).</summary>
        public static ItemDef Decode(ItemDef def, string roll)
        {
            if (def == null || string.IsNullOrEmpty(roll))
                return def;
            var parts = roll.Split(':');
            int.TryParse(parts[0], out int q);
            var affixes = new List<Affix>();
            if (parts.Length > 1)
                foreach (var t in parts[1].Split(','))
                    if (int.TryParse(t, out int v) && System.Enum.IsDefined(typeof(Affix), v))
                        affixes.Add((Affix)v);
            return Build(def, q, affixes.ToArray());
        }

        /// <summary>Base item of a (possibly rolled) item.</summary>
        public static ItemDef BaseOf(ItemDef item) => item == null ? null : ItemDatabase.Instance.Get(item.id) ?? item;

        public static ItemDef Build(ItemDef baseDef, int quality, Affix[] affixes)
        {
            if (quality <= 0 && (affixes == null || affixes.Length == 0))
                return baseDef;
            string key = baseDef.id + "|" + quality + "|" + string.Join(",", affixes);
            if (cache.TryGetValue(key, out var hit) && hit != null)
                return hit;
            var d = Object.Instantiate(baseDef);
            d.name = baseDef.name + "_" + key;
            d.quality = quality;
            d.affixes = affixes;
            float scale = quality >= Legendary ? 1.6f : 1f + 0.15f * quality;
            if (d.combo != null)
                foreach (var s in d.combo)
                    s.damage *= scale;
            d.damage *= scale;
            d.parryDamage *= scale;
            d.finisherWaveDamage *= scale;
            foreach (var a in affixes)
                Apply(d, a);
            cache[key] = d;
            return d;
        }

        static void Apply(ItemDef d, Affix a)
        {
            switch (a)
            {
                case Affix.Damage:
                    if (d.combo != null)
                        foreach (var s in d.combo)
                            s.damage *= 1.2f;
                    d.damage *= 1.2f;
                    d.parryDamage *= 1.2f;
                    break;
                case Affix.VsAfflicted: d.bonusVsAfflicted += 0.5f; break;
                case Affix.Ignite: StatusAffix(d, SkillEffect.Fire, 0.3f, 3f); break;
                case Affix.Bleed: StatusAffix(d, SkillEffect.Bleed, 0.4f, 4f); break;
                case Affix.Poison: StatusAffix(d, SkillEffect.Poison, 0.35f, 4f); break;
                case Affix.Freeze: StatusAffix(d, SkillEffect.Ice, 0.15f, 1.5f); break;
                case Affix.Oil: StatusAffix(d, SkillEffect.Oil, 0.4f, 8f); break;
                case Affix.HealOnKill: d.healOnKill += 0.03f; break;
                case Affix.CritDamage: d.critMultiplier += 0.4f; break;
                case Affix.Cooldown: d.cooldown *= 0.75f; break;
                case Affix.Lifesteal: d.lifesteal += 0.06f; break;
                case Affix.ExtraProjectile:
                    d.projectileCount += 1;
                    if (d.spread <= 0f)
                        d.spread = 7f;
                    break;
                case Affix.Pierce: d.pierce = true; break;
                case Affix.KillBurst: d.killBurst += 0.5f; break;
                case Affix.AttackSpeed: d.animSpeed *= 1.15f; break;
            }
        }

        static void StatusAffix(ItemDef d, SkillEffect e, float chance, float duration)
        {
            d.hasAffixEffect = true;
            d.affixEffect = e;
            d.affixEffectChance = chance;
            d.effectDuration = d.hasEffect ? d.effectDuration : duration;
        }

        // ------------------------------------------------------------ display

        public static Color QualityColor(int q) => q switch
        {
            1 => new Color(0.55f, 0.9f, 1f),
            2 => new Color(0.75f, 0.55f, 1f),
            >= Legendary => new Color(1f, 0.78f, 0.25f),
            _ => Color.white,
        };

        public static string FullName(ItemDef item)
        {
            if (item == null)
                return "";
            string n = item.DisplayName;
            return item.quality switch
            {
                1 => n + " +",
                2 => n + " ++",
                >= Legendary => Loc.Get("quality.legendary") + " " + n,
                _ => n,
            };
        }

        /// <summary>Affix lines for the item card.</summary>
        public static string AffixLines(ItemDef item)
        {
            if (item?.affixes == null || item.affixes.Length == 0)
                return "";
            var sb = new StringBuilder();
            foreach (var a in item.affixes)
                sb.Append("\n· ").Append(Loc.Get("affix." + a.ToString().ToLowerInvariant()));
            return sb.ToString();
        }

        public static string ColorTags(ItemDef item)
        {
            if (item == null || item.colors == ItemColor.None)
                return "";
            var tags = new List<string>();
            if ((item.colors & ItemColor.Brutality) != 0) tags.Add(Loc.Get("color.brutality"));
            if ((item.colors & ItemColor.Tactics) != 0) tags.Add(Loc.Get("color.tactics"));
            if ((item.colors & ItemColor.Survival) != 0) tags.Add(Loc.Get("color.survival"));
            return string.Join(" / ", tags);
        }

        /// <summary>Sum of an amulet affix on the equipped amulet (0 if none).</summary>
        public static int AmuletCount(Affix a)
        {
            var amulet = Player.PlayerCombat.Instance != null ? Player.PlayerCombat.Instance.Amulet : null;
            if (amulet?.affixes == null)
                return 0;
            int n = 0;
            foreach (var x in amulet.affixes)
                if (x == a)
                    n++;
            return n;
        }
    }
}
