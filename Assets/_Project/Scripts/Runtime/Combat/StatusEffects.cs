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
        float burnUntil, freezeUntil, shockUntil, poisonUntil, slowUntil, bleedUntil, oilUntil, rootUntil;
        float tickTimer, poisonTimer, bleedTimer;
        int poisonStacks, bleedStacks;
        public float bleedDpsPerStack = 2.5f;
        public const int MaxBleedStacks = 6;

        public bool Frozen => Time.time < freezeUntil;
        public bool Shocked => Time.time < shockUntil;
        public bool Burning => Time.time < burnUntil;
        public bool Disabled => Frozen || Shocked;
        public bool Poisoned => Time.time < poisonUntil && poisonStacks > 0;
        public bool Slowed => Time.time < slowUntil;
        public bool Bleeding => Time.time < bleedUntil && bleedStacks > 0;
        public bool Oiled => Time.time < oilUntil;
        public bool Rooted => Time.time < rootUntil;
        public bool Afflicted => Burning || Frozen || Shocked || Poisoned || Slowed || Bleeding || Oiled || Rooted;
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
                    if (Oiled)
                    {
                        // Fire meets oil: a burst that sets the neighbours alight too.
                        oilUntil = 0f;
                        OilBlaze();
                        duration *= 2f;
                    }
                    if (!Burning)
                        Audio.Sfx.Play("status.fire", transform.position + Vector3.up);
                    burnUntil = Mathf.Max(burnUntil, Time.time + duration);
                    break;
                case SkillEffect.Bleed:
                    if (!Bleeding)
                        bleedStacks = 0;
                    Audio.Sfx.Play("status.bleed", transform.position + Vector3.up);
                    bleedStacks = Mathf.Min(MaxBleedStacks, bleedStacks + 1);
                    bleedUntil = Mathf.Max(bleedUntil, Time.time + duration);
                    break;
                case SkillEffect.Oil:
                    oilUntil = Mathf.Max(oilUntil, Time.time + duration);
                    break;
                case SkillEffect.Root:
                    rootUntil = Mathf.Max(rootUntil, Time.time + duration);
                    break;
                case SkillEffect.Ice:
                    if (!Frozen)
                        Audio.Sfx.Play("status.ice", transform.position + Vector3.up);
                    freezeUntil = Mathf.Max(freezeUntil, Time.time + duration);
                    break;
                case SkillEffect.Lightning:
                    shockUntil = Mathf.Max(shockUntil, Time.time + Mathf.Min(duration, 0.6f));
                    break;
                case SkillEffect.Poison:
                    if (!Poisoned)
                        poisonStacks = 0;
                    Audio.Sfx.Play("status.poison", transform.position + Vector3.up);
                    poisonStacks = Mathf.Min(MaxPoisonStacks, poisonStacks + 1);
                    poisonUntil = Mathf.Max(poisonUntil, Time.time + duration);
                    break;
                case SkillEffect.Slow:
                    slowUntil = Mathf.Max(slowUntil, Time.time + duration);
                    break;
            }
        }

        public void BreakFreeze() => freezeUntil = 0f;

        void OilBlaze()
        {
            var at = transform.position + Vector3.up;
            JuiceEngine.Instance?.SlamWave(at, 2.6f);
            JuiceEngine.Instance?.Embers(at, 30, new Color(3.4f, 1.4f, 0.3f));
            Audio.Sfx.Play("explode.fire", at, 0.8f);
            bool player = gameObject.layer == Core.DCLayers.Player;
            int mask = player ? (1 << Core.DCLayers.Player) : Core.DCLayers.EnemyMask;
            foreach (var c in Physics2D.OverlapCircleAll(at, 2.6f, mask))
            {
                var h = c.GetComponentInParent<Health>();
                if (h == null || h.IsDead)
                    continue;
                h.TakeDamage(new DamageInfo { amount = 25f, knockback = ((Vector2)(c.bounds.center - at)).normalized * 4f, hitPoint = c.bounds.center, stun = 0.3f, effect = -1 });
                var se = h.GetComponent<StatusEffects>();
                if (se != null && se != this)
                    se.burnUntil = Mathf.Max(se.burnUntil, Time.time + 4f);
            }
        }

        float fxTimer;
        Collider2D body;

        /// <summary>Continuous particles that make each status readable at a glance.</summary>
        void StatusParticles()
        {
            fxTimer -= Time.deltaTime;
            if (fxTimer > 0f)
                return;
            fxTimer = 0.09f;
            var juice = JuiceEngine.Instance;
            if (juice == null)
                return;
            if (body == null)
                body = GetComponentInChildren<Collider2D>();
            Vector3 c = body != null ? body.bounds.center : transform.position + Vector3.up;
            float h = body != null ? body.bounds.extents.y : 0.8f;
            if (Burning)
            {
                juice.Flames(c + Vector3.down * h * 0.4f, 3);
                if (Random.value < 0.25f)
                    juice.Smoke(c + Vector3.up * h, 1, new Color(0.15f, 0.12f, 0.12f, 0.55f));
            }
            if (Poisoned && Random.value < 0.4f + 0.1f * poisonStacks)
                juice.Bubbles(c + Vector3.down * h * 0.3f, 1, new Color(0.45f, 1f, 0.3f, 0.9f));
            if (Bleeding && Random.value < 0.25f + 0.08f * bleedStacks)
                juice.Drips(c, 1, new Color(0.55f, 0.03f, 0.05f, 1f));
            if (Oiled && Random.value < 0.3f)
                juice.Drips(c, 1, new Color(0.06f, 0.05f, 0.04f, 1f));
            if (Frozen)
                juice.Frost(c, 2);
            if (Shocked && Random.value < 0.5f)
                juice.HitSparks(c + (Vector3)Random.insideUnitCircle * h * 0.6f, Random.insideUnitCircle, new Color(1.6f, 2.4f, 3.4f), 0.1f);
        }

        void Update()
        {
            if (health.IsDead)
                return;
            StatusParticles();
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
            if (Bleeding)
            {
                bleedTimer -= Time.deltaTime;
                if (bleedTimer <= 0f)
                {
                    bleedTimer = 0.5f;
                    health.TakeDamage(new DamageInfo { amount = bleedDpsPerStack * bleedStacks * 0.5f, hitPoint = transform.position + Vector3.up, effect = -1 });
                    JuiceEngine.Instance?.Ichor(transform.position + Vector3.up, Vector2.down, new Color(0.7f, 0.05f, 0.08f), 2 + bleedStacks);
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
                else if (Rooted)
                    flash.Flash(new Color(0.9f, 1.6f, 0.4f), 0.3f);
                else if (Oiled)
                    flash.Flash(new Color(0.15f, 0.12f, 0.1f), 0.35f);
            }
        }
    }
}
