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

        Vector2 origin;
        float age;
        bool dead;
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
            Vector2 pos = transform.position;
            Vector2 step = velocity * dt;
            var wall = Physics2D.Raycast(pos, step.normalized, step.magnitude + hitRadius * 0.5f, DCLayers.SolidMask);
            if (wall.collider != null)
            {
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
                    damage *= 1.5f;
                    return;
                }
                if (!pierce || result == DamageResult.Blocked)
                {
                    Finish(true);
                    return;
                }
            }
        }

        DamageResult DealDamage(Health h, Vector2 point)
        {
            float amount = damage;
            bool crit = critAtLongRange && Vector2.Distance(origin, point) > 6f;
            if (crit)
                amount *= critMultiplier;
            var info = new DamageInfo
            {
                amount = amount,
                knockback = velocity.normalized * knockback,
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
                h.GetComponent<StatusEffects>()?.Apply(effect, effectDuration);
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
                Audio.Sfx.Play(hasEffect && effect == SkillEffect.Ice ? "explode.ice" : "explode.fire", transform.position);
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
    }
}
