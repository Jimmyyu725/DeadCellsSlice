using DeadCells.FX;
using DeadCells.Items;
using UnityEngine;

namespace DeadCells.Combat
{
    /// <summary>Burn (damage over time), Freeze (hard disable) and Shock (brief stun) on a damageable.</summary>
    [RequireComponent(typeof(Health))]
    public class StatusEffects : MonoBehaviour
    {
        public float burnDps = 6f;

        Health health;
        HitFlash flash;
        float burnUntil, freezeUntil, shockUntil;
        float tickTimer;

        public bool Frozen => Time.time < freezeUntil;
        public bool Shocked => Time.time < shockUntil;
        public bool Burning => Time.time < burnUntil;
        public bool Disabled => Frozen || Shocked;

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
            if (flash != null)
            {
                if (Frozen)
                    flash.Flash(new Color(0.6f, 1.6f, 2.6f), 0.55f);
                else if (Shocked)
                    flash.Flash(new Color(1.8f, 2.4f, 3f), Random.value * 0.8f);
            }
        }
    }
}
