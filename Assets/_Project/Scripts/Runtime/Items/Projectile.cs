using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using UnityEngine;

namespace DeadCells.Items
{
    /// <summary>
    /// Arrows, grenades, harpoons, orbs and starlight. Moves itself (no
    /// rigidbody), raycasts against the level, overlaps the opposing team.
    /// Monks can Reverse() player projectiles mid-flight.
    /// </summary>
    public class Projectile : MonoBehaviour
    {
        public Vector2 velocity;
        public float gravity;
        public float lifetime = 4f;
        public float damage = 10f;
        public float knockback = 4f;
        public bool fromPlayer = true;
        public float hitRadius = 0.25f;
        public float explodeRadius;
        public bool explodeOnGround;
        public bool pierce;
        public bool reflectable = true;
        public bool hasEffect;
        public SkillEffect effect;
        public float effectDuration = 3f;
        public Color sparkColor = new Color(2.5f, 2.2f, 1.6f);
        public string weaponId;
        public GameObject owner;
        public bool critAtLongRange;
        public float critMultiplier = 1.75f;
        public bool spin;
        [Header("Behaviours")]
        [Tooltip("Turn rate toward the nearest enemy (deg/s).")]
        public float homing;
        public int bounces;
        public bool boomerang;
        public float boomerangTime = 0.42f;
        [Tooltip("Lightning hops to this many extra enemies on hit.")]
        public int chain;
        [Tooltip("Hit targets are yanked toward the owner.")]
        public float pull;
        [Tooltip("Skill whose burst behaviour (cluster / cloud / vortex) runs when this explodes.")]
        public ItemDef burstItem;
        public bool bomblet;
        [Tooltip("Affix modifiers copied from the firing item.")]
        public float bonusVsAfflicted;
        public bool hasAffixEffect;
        public SkillEffect affixEffect;
        public float affixEffectChance;

        Vector2 origin;
        float age;
        bool dead;
        bool returning;
        Health homingTarget;
        float retargetAt;
        readonly System.Collections.Generic.HashSet<Health> hits = new System.Collections.Generic.HashSet<Health>();

        public static System.Collections.Generic.List<Projectile> Live = new System.Collections.Generic.List<Projectile>();

        void OnEnable()
        {
            origin = transform.position;
            Live.Add(this);
        }

        void OnDisable() => Live.Remove(this);

        public void Reverse(GameObject newOwner)
        {
            if (!reflectable)
                return;
            velocity = -velocity * 1.1f;
            fromPlayer = !fromPlayer;
            owner = newOwner;
            origin = transform.position;
            hits.Clear();
            JuiceEngine.Instance?.HitSparks(transform.position, velocity, new Color(1.6f, 2.8f, 1.2f), 0.4f);
            Audio.Sfx.Play("projectile.reflect", transform.position);
        }

        void FixedUpdate()
        {
            if (dead)
                return;
            float dt = Time.fixedDeltaTime;
            age += dt;
            if (age > lifetime)
            {
                Finish(false);
                return;
            }
            velocity.y -= gravity * dt;
            if (homing > 0f)
                Steer(dt);
            if (boomerang && !returning && age > boomerangTime)
            {
                returning = true;
                hits.Clear();
                gravity = 0f;
            }
            if (returning)
            {
                if (owner == null)
                {
                    Finish(false);
                    return;
                }
                Vector2 to = (Vector2)owner.transform.position + Vector2.up * 1.1f - (Vector2)transform.position;
                if (to.magnitude < 0.9f)
                {
                    Destroy(gameObject); // caught
                    dead = true;
                    return;
                }
                velocity = Vector2.MoveTowards(velocity, to.normalized * Mathf.Max(velocity.magnitude, 16f), 140f * dt);
            }
            Vector2 pos = transform.position;
            Vector2 step = velocity * dt;
            var wall = boomerang ? default : Physics2D.Raycast(pos, step.normalized, step.magnitude + hitRadius * 0.5f, DCLayers.SolidMask);
            if (wall.collider != null)
            {
                if (fromPlayer)
                    wall.collider.GetComponentInParent<DeadCells.Run.Breakable>()?.Hit(false);
                if (bounces > 0)
                {
                    bounces--;
                    velocity = Vector2.Reflect(velocity, wall.normal) * 0.92f;
                    transform.position = wall.point + wall.normal * 0.06f;
                    hits.Clear();
                    JuiceEngine.Instance?.HitSparks(wall.point, wall.normal, sparkColor, 0.25f);
                    Audio.Sfx.Play("arrow.hit", wall.point, 0.4f, 1.3f);
                    return;
                }
                transform.position = wall.point - step.normalized * 0.05f;
                Finish(true);
                return;
            }
            transform.position = pos + step;
            if (velocity.sqrMagnitude > 0.01f)
            {
                // Projectile models point along +Y.
                if (spin)
                    transform.Rotate(0f, 0f, -720f * dt, Space.Self);
                else
                    transform.rotation = Quaternion.AngleAxis(Mathf.Atan2(velocity.y, velocity.x) * Mathf.Rad2Deg - 90f, Vector3.forward);
            }

            int mask = fromPlayer ? DCLayers.EnemyMask : (1 << DCLayers.Player);
            var cols = Physics2D.OverlapCircleAll(transform.position, hitRadius, mask);
            foreach (var c in cols)
            {
                var h = c.GetComponentInParent<Health>();
                if (h == null || h.IsDead || hits.Contains(h) || (owner != null && h.gameObject == owner))
                    continue;
                hits.Add(h);
                if (explodeRadius > 0f)
                {
                    Finish(true);
                    return;
                }
                var result = DealDamage(h, transform.position);
                if (result == DamageResult.Parried && reflectable)
                {
                    // Shields send projectiles back at their owner.
                    Reverse(h.gameObject);
                    damage *= Player.PlayerCombat.Instance != null ? Player.PlayerCombat.Instance.ReflectMultiplier : 1.5f;
                    return;
                }
                if (!pierce && !boomerang || result == DamageResult.Blocked)
                {
                    Finish(true);
                    return;
                }
            }
        }

        void Steer(float dt)
        {
            if (Time.time >= retargetAt || homingTarget == null || homingTarget.IsDead)
            {
                retargetAt = Time.time + 0.12f;
                homingTarget = null;
                float best = float.MaxValue;
                int mask = fromPlayer ? DCLayers.EnemyMask : (1 << DCLayers.Player);
                foreach (var c in Physics2D.OverlapCircleAll(transform.position, 14f, mask))
                {
                    var h = c.GetComponentInParent<Health>();
                    if (h == null || h.IsDead || hits.Contains(h))
                        continue;
                    Vector2 to = (Vector2)c.bounds.center - (Vector2)transform.position;
                    if (Vector2.Angle(velocity, to) > 110f)
                        continue;
                    float score = to.magnitude;
                    if (score < best)
                    {
                        best = score;
                        homingTarget = h;
                    }
                }
            }
            if (homingTarget == null)
                return;
            var col = homingTarget.GetComponentInChildren<Collider2D>();
            Vector2 aim = (col != null ? (Vector2)col.bounds.center : (Vector2)homingTarget.transform.position + Vector2.up) - (Vector2)transform.position;
            float speed = velocity.magnitude;
            float ang = Vector2.SignedAngle(velocity, aim);
            float turn = Mathf.Clamp(ang, -homing * dt, homing * dt);
            velocity = (Vector2)(Quaternion.Euler(0f, 0f, turn) * velocity).normalized * speed;
        }

        void ChainLightning(Health from, Vector2 point, float amount)
        {
            int mask = fromPlayer ? DCLayers.EnemyMask : (1 << DCLayers.Player);
            Vector2 at = point;
            for (int i = 0; i < chain; i++)
            {
                Health next = null;
                float best = 5.5f;
                foreach (var c in Physics2D.OverlapCircleAll(at, 5.5f, mask))
                {
                    var h = c.GetComponentInParent<Health>();
                    if (h == null || h.IsDead || h == from || hits.Contains(h))
                        continue;
                    float d = Vector2.Distance(at, c.bounds.center);
                    if (d < best)
                    {
                        best = d;
                        next = h;
                    }
                }
                if (next == null)
                    return;
                hits.Add(next);
                Vector2 to = (Vector2)next.transform.position + Vector2.up;
                var juice = JuiceEngine.Instance;
                for (int k = 1; k <= 4; k++)
                    juice?.HitSparks(Vector2.Lerp(at, to, k / 4f) + Random.insideUnitCircle * 0.2f, to - at, new Color(1.4f, 2.2f, 3.4f), 0.15f);
                var info = new DamageInfo
                {
                    amount = amount * 0.6f, knockback = (to - at).normalized * 2f, hitPoint = to, source = owner != null ? owner : gameObject,
                    stun = 0.2f, hitStop = 0.02f, shake = 0.06f, sparkColor = new Color(1.4f, 2.2f, 3.4f), weaponId = weaponId,
                    projectile = true, effect = (int)SkillEffect.Lightning, effectDuration = 0.4f,
                };
                var result = next.TakeDamage(info);
                if (result == DamageResult.Hit || result == DamageResult.Killed)
                    next.GetComponent<StatusEffects>()?.Apply(SkillEffect.Lightning, 0.4f);
                if (fromPlayer && result != DamageResult.Ignored)
                    Player.PlayerCombat.Instance?.ReportHit(next, info, result);
                Audio.Sfx.Play("lightning.zap", to, 0.7f);
                from = next;
                at = to;
            }
        }

        DamageResult DealDamage(Health h, Vector2 point)
        {
            float amount = damage;
            var targetStatus = h.GetComponent<StatusEffects>();
            if (bonusVsAfflicted > 0f && targetStatus != null && targetStatus.Afflicted)
                amount *= 1f + bonusVsAfflicted;
            bool crit = critAtLongRange && Vector2.Distance(origin, point) > 6f;
            if (crit)
                amount *= critMultiplier;
            Vector2 push = velocity.normalized * knockback;
            if (pull > 0f && owner != null)
                push = ((Vector2)owner.transform.position - point).normalized * pull + Vector2.up * 2f;
            var info = new DamageInfo
            {
                amount = amount,
                knockback = push,
                hitPoint = point,
                source = owner != null ? owner : gameObject,
                critical = crit,
                stun = 0.15f,
                hitStop = 0.035f,
                shake = 0.12f,
                sparkColor = sparkColor,
                weaponId = weaponId,
                projectile = true,
                effect = hasEffect ? (int)effect : -1,
                effectDuration = effectDuration,
            };
            var result = h.TakeDamage(info);
            if ((result == DamageResult.Hit || result == DamageResult.Killed) && hasEffect)
                h.GetComponent<StatusEffects>()?.Apply(effect, effectDuration * (fromPlayer ? Meta.Mutations.StatusDuration(effect) : 1f));
            if ((result == DamageResult.Hit || result == DamageResult.Killed) && hasAffixEffect && Random.value < affixEffectChance)
                h.GetComponent<StatusEffects>()?.Apply(affixEffect, effectDuration);
            if ((result == DamageResult.Hit || result == DamageResult.Killed) && chain > 0)
                ChainLightning(h, point, amount);
            if ((result == DamageResult.Hit || result == DamageResult.Killed) && explodeRadius <= 0f)
            {
                if (hasEffect && effect == SkillEffect.Lightning)
                    Audio.Sfx.Play("lightning.zap", point);
                else if (fromPlayer)
                    Audio.Sfx.Play("arrow.hit", point);
            }
            if (fromPlayer && result != DamageResult.Ignored && result != DamageResult.Parried)
                Player.PlayerCombat.Instance?.ReportHit(h, info, result);
            return result;
        }

        void Finish(bool impact)
        {
            dead = true;
            var juice = JuiceEngine.Instance;
            if (impact && explodeRadius > 0f)
            {
                int mask = fromPlayer ? DCLayers.EnemyMask : (1 << DCLayers.Player);
                foreach (var c in Physics2D.OverlapCircleAll(transform.position, explodeRadius, mask))
                {
                    var h = c.GetComponentInParent<Health>();
                    if (h == null || h.IsDead || (owner != null && h.gameObject == owner))
                        continue;
                    DealDamage(h, h.transform.position + Vector3.up);
                }
                Audio.Sfx.Play(hasEffect && effect == SkillEffect.Ice ? "explode.ice" : "explode.fire", transform.position, bomblet ? 0.6f : 1f);
                if (burstItem != null)
                    Burst();
                if (juice != null)
                {
                    juice.SlamWave(transform.position, explodeRadius);
                    juice.Embers(transform.position, 24, sparkColor);
                    juice.Shake(Vector2.up, 0.35f);
                }
            }
            else if (impact && juice != null)
            {
                juice.HitSparks(transform.position, -velocity, sparkColor, 0.3f);
                if (fromPlayer)
                    Audio.Sfx.Play("arrow.hit", transform.position, 0.6f);
            }
            Destroy(gameObject);
        }

        /// <summary>Cluster bomblets, a lingering poison cloud or a vortex.</summary>
        void Burst()
        {
            var item = burstItem;
            switch (item.burstKind)
            {
                case BurstKind.Cluster:
                    if (bomblet || item.projectile == null)
                        break;
                    for (int i = 0; i < item.count; i++)
                    {
                        var go = Instantiate(item.projectile, transform.position + Vector3.up * 0.3f, Quaternion.identity);
                        go.SetActive(true);
                        go.transform.localScale *= 0.6f;
                        var p = go.GetComponent<Projectile>();
                        p.velocity = new Vector2(Random.Range(-7f, 7f), Random.Range(6f, 11f));
                        p.gravity = 28f;
                        p.damage = damage * 0.45f;
                        p.explodeRadius = explodeRadius * 0.6f;
                        p.fromPlayer = fromPlayer;
                        p.owner = owner;
                        p.hasEffect = hasEffect;
                        p.effect = effect;
                        p.effectDuration = effectDuration;
                        p.sparkColor = sparkColor;
                        p.weaponId = weaponId;
                        p.spin = true;
                        p.lifetime = 2f;
                        p.burstItem = item;
                        p.bomblet = true;
                        p.hitRadius = hitRadius * 0.7f;
                    }
                    break;
                case BurstKind.Cloud:
                case BurstKind.Vortex:
                    var zone = new GameObject(item.burstKind == BurstKind.Cloud ? "MiasmaCloud" : "Vortex").AddComponent<Run.LingeringZone>();
                    zone.transform.position = transform.position;
                    zone.Setup(item, owner, explodeRadius, damage * 0.25f, fromPlayer);
                    break;
            }
        }
    }
}
