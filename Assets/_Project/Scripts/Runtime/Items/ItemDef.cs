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
    }

    public enum SkillEffect
    {
        Fire,
        Ice,
        Lightning,
    }

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

        public bool IsWeapon => kind != ItemKind.Skill;

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
                    default:
                        return Loc.Get("hud.damage_label", Mathf.RoundToInt(damage)) + "   " + Loc.Get("hud.dps_label", cooldown.ToString("0.#"));
                }
            }
        }

        public string DisplayName => Loc.Get($"item.{id}.name");
        public string Description => Loc.Get($"item.{id}.desc");

        public bool IsUnlocked => unlockCost <= 0 || SaveSystem.Data.meta.unlockedItems.Contains(id);

        public int PriceFor(int biome) => Mathf.RoundToInt(basePrice * (1f + 0.6f * biome) * (0.8f + 0.2f * tier));
    }
}
