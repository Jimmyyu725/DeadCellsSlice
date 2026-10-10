using DeadCells.FX;
using DeadCells.Items;
using UnityEngine;

namespace DeadCells.Combat
{
    /// <summary>
    /// Burn (damage over time), Freeze (hard disable), Shock (brief stun),
    /// Poison (stacking damage over time) and Slow (the target's time runs at
    /// 45%) on a damageable.
    /// </summary>
    [RequireComponent(typeof(Health))]
    public class StatusEffects : MonoBehaviour
    {
        public float burnDps = 6f;
        public float poisonDpsPerStack = 3f;
        public const int MaxPoisonStacks = 5;
        public const float SlowFactor = 0.45f;

        Health health;
        HitFlash flash;
        float burnUntil, freezeUntil, shockUntil, poisonUntil, slowUntil;
        float tickTimer, poisonTimer;
        int poisonStacks;

        public bool Frozen => Time.time < freezeUntil;
        public bool Shocked => Time.time < shockUntil;
        public bool Burning => Time.time < burnUntil;
        public bool Disabled => Frozen || Shocked;
        public bool Poisoned => Time.time < poisonUntil && poisonStacks > 0;
        public bool Slowed => Time.time < slowUntil;
        public bool Afflicted => Burning || Frozen || Shocked || Poisoned || Slowed;
        /// <summary>Local time multiplier for AI and animation.</summary>
        public float TimeFactor => Slowed ? SlowFactor : 1f;

        void Awake()
        {
            health = GetComponent<Health>();
            flash = GetComponent<HitFlash>();
        }

        public void Apply(SkillEffect effect, float duration)
        {
            switch (effect)
            {
                case SkillEffect.Fire:
                    burnUntil = Mathf.Max(burnUntil, Time.time + duration);
                    break;
                case SkillEffect.Ice:
                    freezeUntil = Mathf.Max(freezeUntil, Time.time + duration);
                    break;
                case SkillEffect.Lightning:
                    shockUntil = Mathf.Max(shockUntil, Time.time + Mathf.Min(duration, 0.6f));
                    break;
                case SkillEffect.Poison:
                    if (!Poisoned)
                        poisonStacks = 0;
                    poisonStacks = Mathf.Min(MaxPoisonStacks, poisonStacks + 1);
                    poisonUntil = Mathf.Max(poisonUntil, Time.time + duration);
                    break;
                case SkillEffect.Slow:
                    slowUntil = Mathf.Max(slowUntil, Time.time + duration);
                    break;
            }
        }

        public void BreakFreeze() => freezeUntil = 0f;

        void Update()
        {
            if (health.IsDead)
                return;
            if (Burning)
            {
                tickTimer -= Time.deltaTime;
                if (tickTimer <= 0f)
                {
                    tickTimer = 0.5f;
                    health.TakeDamage(new DamageInfo { amount = burnDps * 0.5f, hitPoint = transform.position + Vector3.up, effect = -1 });
                    JuiceEngine.Instance?.Embers(transform.position + Vector3.up, 4, new Color(3f, 1.2f, 0.3f));
                }
            }
            if (Poisoned)
            {
                poisonTimer -= Time.deltaTime;
                if (poisonTimer <= 0f)
                {
                    poisonTimer = 0.5f;
                    health.TakeDamage(new DamageInfo { amount = poisonDpsPerStack * poisonStacks * 0.5f, hitPoint = transform.position + Vector3.up, effect = -1 });
                    JuiceEngine.Instance?.Embers(transform.position + Vector3.up, 2 + poisonStacks, new Color(0.9f, 3f, 0.6f));
                }
            }
            if (flash != null)
            {
                if (Frozen)
                    flash.Flash(new Color(0.6f, 1.6f, 2.6f), 0.55f);
                else if (Shocked)
                    flash.Flash(new Color(1.8f, 2.4f, 3f), Random.value * 0.8f);
                else if (Slowed)
                    flash.Flash(new Color(1.2f, 1.0f, 2.6f), 0.25f);
            }
        }
    }
}
