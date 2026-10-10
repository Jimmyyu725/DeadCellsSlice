using DeadCells.Meta;
using UnityEngine;

namespace DeadCells.Items
{
    public enum ItemKind
    {
        Melee,
        Shield,
        Bow,
        Skill,
        Amulet,     // passive slot: stat affixes only
    }

    /// <summary>Scroll colours an item scales with (Dead Cells' Brutality / Tactics / Survival).</summary>
    [System.Flags]
    public enum ItemColor
    {
        None = 0,
        Brutality = 1,
        Tactics = 2,
        Survival = 4,
    }

    /// <summary>Random modifiers rolled onto dropped items (count grows with quality).</summary>
    public enum Affix
    {
        Damage,         // +20% damage
        VsAfflicted,    // +50% damage against targets with a status
        Ignite,         // 30% chance to burn
        Bleed,          // 40% chance to bleed
        Poison,         // 35% chance to poison
        Freeze,         // 15% chance to freeze
        HealOnKill,     // kills heal 3% max health
        CritDamage,     // +40% critical damage
        Cooldown,       // -25% cooldown
        Lifesteal,      // 6% of damage healed
        ExtraProjectile,
        Pierce,
        KillBurst,      // kills explode
        AttackSpeed,    // +15% attack speed
        Oil,            // 40% chance to coat in oil
        // Amulet affixes
        MaxHealth,      // +15% max health
        AllDamage,      // +10% damage with everything
        GoldFind,       // +30% gold
        Recovery,       // recover 50% more of damage taken
        MoveSpeed,      // +10% move speed
        FlaskPower,     // flasks heal 30% more
    }

    public enum CritRule
    {
        None,
        Finisher,     // last hit of the combo
        Behind,       // target is facing away
        Disabled,     // target stunned or frozen
        LongRange,    // projectile travelled > 6 m
        AfterDodge,   // within 1.5 s of a dodge roll
        LowHealth,    // target below 35% health
        Burning,      // target is on fire
        Airborne,     // the player is in the air
        Afflicted,    // target carries any status effect
    }

    public enum SkillEffect
    {
        Fire,
        Ice,
        Lightning,
        Poison,     // stacking damage over time
        Slow,       // enemy time runs at 45%
        Bleed,      // stacking damage over time (blades)
        Oil,        // fire on an oiled target bursts and burns hotter
        Root,       // cannot move (can still attack)
    }

    /// <summary>What a skill does when used.</summary>
    public enum SkillKind
    {
        Throw,      // launch the projectile (grenades, discs, jars)
        Rain,       // projectiles fall from the sky around the nearest enemy
        Deploy,     // place a turret / totem / trap / healer on the floor
        Nova,       // instant burst around the player
        Dash,       // blink forward, hurting everything on the way
        Buff,       // temporary boost to the player
    }

    public enum DeployKind { Turret, Totem, Trap, Healer }

    /// <summary>Extra behaviour when a thrown skill bursts.</summary>
    public enum BurstKind { None, Cluster, Cloud, Vortex }

    public enum MountPoint
    {
        Weapon,     // right hand, blade forward
        Offhand,    // left hand, blade forward (second dagger)
        Shield,     // left forearm
        Bow,        // left hand, limbs vertical
    }

    [System.Serializable]
    public class AttackStep
    {
        public string clip = "Slash_Combo_1";
        [Tooltip("Clip length in 60 fps frames.")]
        public int totalFrames = 18;
        [Tooltip("First/last frame the hitbox is live (Blender frame numbers).")]
        public Vector2Int activeFrames = new Vector2Int(4, 7);
        [Tooltip("From this frame the next combo step (or a jump) may cancel the recovery.")]
        public int cancelFrame = 8;
        public Vector2Int lungeFrames = new Vector2Int(3, 6);
        public float lungeSpeed = 4f;
        public float damage = 12f;
        public Vector2 hitboxOffset = new Vector2(1.2f, 1.0f);
        public Vector2 hitboxSize = new Vector2(2.2f, 1.7f);
        public float knockback = 4f;
        public float stun = 0.2f;
        [Range(0f, 1f)] public float hitStopWeight = 0.3f;
        public float shake = 0.18f;
        public bool finisher;
    }

    /// <summary>Everything about one equippable item. Built by the editor into Resources/ItemDatabase.</summary>
    [CreateAssetMenu(menuName = "Dead Cells/Item")]
    public class ItemDef : ScriptableObject
    {
        public string id;
        public ItemKind kind;
        public GameObject visual;
        [Tooltip("Second visual for dual-wield weapons (left hand).")]
        public GameObject offhandVisual;
        public MountPoint mount;
        public Sprite icon;
        [Tooltip("Cells to unlock at the Collector (0 = available from the start).")]
        public int unlockCost;
        public int basePrice = 120;
        [Range(1, 3)] public int tier = 1;
        public CritRule crit;
        public float critMultiplier = 1.75f;

        [Header("Melee")]
        public float animSpeed = 1f;
        [ColorUsage(true, true)] public Color arcColor = new Color(1.2f, 2.6f, 3.2f);
        [ColorUsage(true, true)] public Color arcCore = new Color(6f, 6f, 6f);
        [ColorUsage(true, true)] public Color sparkColor = new Color(2.5f, 2.2f, 1.6f);
        public bool dualWield;
        [Header("Sound")]
        [Tooltip("Sound event when a melee swing starts (Tools/Audio/sfx.py ids).")]
        public string swingSound = "swing.light";
        [Tooltip("Sound event when a melee hit lands (crits and kills add their own).")]
        public string hitSound = "hit.flesh";
        [Tooltip("Sound event when a bow shot / skill is released.")]
        public string fireSound = "";
        public float bladeLength = 0.78f;
        public AttackStep[] combo = new AttackStep[0];

        [Header("Shield")]
        public float parryWindow = 0.18f;
        [Range(0f, 1f)] public float blockReduction = 0.8f;
        public float parryDamage = 18f;

        [Header("Bow / Skill")]
        public GameObject projectile;
        public float projectileSpeed = 26f;
        public float projectileGravity;
        [Tooltip("Launch angle above horizontal (degrees).")]
        public float launchAngle;
        public float damage = 14f;
        public float cooldown = 0.45f;
        public bool hasEffect;
        public SkillEffect effect;
        public float effectDuration = 3f;
        [Tooltip("Explosion radius (0 = single target).")]
        public float radius;
        public bool pierce;
        public bool spin;
        [ColorUsage(true, true)] public Color effectColor = new Color(3f, 1.3f, 0.3f);

        [Header("Melee extras")]
        [Tooltip("Chance per hit to apply `effect` for `effectDuration` (melee).")]
        [Range(0f, 1f)] public float onHitChance;
        [Tooltip("Fraction of damage dealt returned as health.")]
        public float lifesteal;
        [Tooltip("Finisher drags the target toward the player instead of knocking it away.")]
        public float pull;
        [Tooltip("Extra damage per consecutive hit of a chain (0.08 = +8% each).")]
        public float comboRamp;
        [Tooltip("Damage multiplier against elites and bosses.")]
        public float eliteBonus = 1f;
        [Tooltip("Projectile launched forward when the finisher lands.")]
        public GameObject finisherWave;
        public float finisherWaveDamage;

        [Header("Ranged extras")]
        public int projectileCount = 1;
        [Tooltip("Degrees between projectiles of one shot.")]
        public float spread;
        public int burst = 1;
        public float burstInterval = 0.09f;
        [Tooltip("Turn rate toward the nearest enemy (deg/s).")]
        public float homing;
        public int bounces;
        public bool boomerang;
        [Tooltip("Lightning hops to this many extra enemies on hit.")]
        public int chain;
        [Tooltip("Hit enemies are yanked toward the shooter.")]
        public float pullOnHit;
        public float knockbackScale = 1f;
        public float projectileScale = 1f;
        public float projectileLifetime = 3f;

        [Header("Shield extras")]
        [Tooltip("A parry also stuns every enemy within this radius.")]
        public float parryRadius;
        [Tooltip("A parry applies `effect` to the attacker (and parryRadius victims).")]
        public bool parryApplies;
        [Tooltip("Damage returned to melee attackers on every block.")]
        public float thorns;
        public float reflectMultiplier = 1.5f;

        [Header("Skill behaviour")]
        public SkillKind skillKind;
        public DeployKind deployKind;
        public BurstKind burstKind;
        [Tooltip("Lifetime of deployables, clouds, vortices and buffs.")]
        public float duration = 6f;
        [Tooltip("Seconds between deployable actions / cloud ticks.")]
        public float interval = 0.8f;
        [Tooltip("Rain: projectiles; Cluster: bomblets.")]
        public int count = 4;
        [Tooltip("Vortex pull strength / dash distance / buff damage bonus.")]
        public float power = 1f;

        [Header("Scroll colours and rolls")]
        public ItemColor colors = ItemColor.Brutality;
        [Tooltip("0 normal, 1 '+', 2 '++', 3 legendary. Set on runtime copies by ItemForge.")]
        public int quality;
        public Affix[] affixes = new Affix[0];
        [Tooltip("Extra on-hit status from an affix (in addition to `effect`).")]
        public bool hasAffixEffect;
        public SkillEffect affixEffect;
        public float affixEffectChance;
        [Tooltip("Damage bonus against targets carrying any status (affix).")]
        public float bonusVsAfflicted;
        [Tooltip("Fraction of max health healed per kill (affix).")]
        public float healOnKill;
        [Tooltip("Kills explode for this fraction of the killing blow (affix).")]
        public float killBurst;

        public bool IsWeapon => kind != ItemKind.Skill && kind != ItemKind.Amulet;

        public string StatLine
        {
            get
            {
                switch (kind)
                {
                    case ItemKind.Melee:
                        float total = 0f;
                        foreach (var s in combo)
                            total += s.damage;
                        return Loc.Get("hud.damage_label", Mathf.RoundToInt(total / Mathf.Max(1, combo.Length)));
                    case ItemKind.Shield:
                        return Loc.Get("hud.damage_label", Mathf.RoundToInt(parryDamage));
                    case ItemKind.Amulet:
                        return "";
                    default:
                        string cd = Loc.Get("hud.dps_label", cooldown.ToString("0.#"));
                        return damage > 0f ? Loc.Get("hud.damage_label", Mathf.RoundToInt(damage)) + "   " + cd : cd;
                }
            }
        }

        public string DisplayName => Loc.Get($"item.{id}.name");
        public string Description => Loc.Get($"item.{id}.desc");

        public bool IsUnlocked => unlockCost <= 0 || SaveSystem.Data.meta.unlockedItems.Contains(id);

        public int PriceFor(int biome) => Mathf.RoundToInt(basePrice * (1f + 0.6f * biome) * (0.8f + 0.2f * tier));
    }
}
