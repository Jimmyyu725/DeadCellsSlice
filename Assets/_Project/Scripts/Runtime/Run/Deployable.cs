using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Player;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// A skill placed on the floor (its own item model): a sentry that shoots
    /// the nearest enemy, a totem that zaps it, a jaw trap that bites the first
    /// enemies to step in, or a lantern that heals the player nearby.
    /// </summary>
    public class Deployable : MonoBehaviour
    {
        ItemDef item;
        GameObject owner;
        float until, next;
        int bites = 3;

        public static Deployable Spawn(ItemDef def, Vector3 at, GameObject source)
        {
            if (def == null || def.visual == null)
                return null;
            var hit = Physics2D.Raycast((Vector2)at + Vector2.up * 0.6f, Vector2.down, 6f, DCLayers.GroundMask);
            if (hit.collider != null)
                at.y = hit.point.y;
            at.z = 0.3f;
            var go = Instantiate(def.visual, at, Quaternion.identity, RunManager.Instance != null ? RunManager.Instance.EntityParent : null);
            go.SetActive(true);
            // The models are hand-sized; on the floor they need to read at gameplay distance.
            go.transform.localScale *= def.deployKind == DeployKind.Trap ? 1.6f : 1.8f;
            var d = go.AddComponent<Deployable>();
            d.item = def;
            d.owner = source;
            d.until = Time.time + def.duration;
            d.next = Time.time + 0.4f;
            JuiceEngine.Instance?.Dust(at, Vector2.up, 8);
            Audio.Sfx.Play("player.land", at, 0.8f, 0.8f);
            return d;
        }

        void Update()
        {
            if (item == null)
                return;
            if (Time.time > until)
            {
                JuiceEngine.Instance?.Embers(transform.position + Vector3.up * 0.3f, 12, item.effectColor);
                Destroy(gameObject);
                return;
            }
            switch (item.deployKind)
            {
                case DeployKind.Trap:
                    Trap();
                    return;
                case DeployKind.Healer:
                    if (Time.time >= next)
                    {
                        next = Time.time + item.interval;
                        var p = PlayerController.Main;
                        if (p != null && Vector2.Distance(p.transform.position, transform.position) < item.radius)
                        {
                            p.Health.Heal(p.Health.maxHealth * item.power);
                            JuiceEngine.Instance?.Embers(p.transform.position + Vector3.up, 6, new Color(0.9f, 3f, 0.6f));
                        }
                    }
                    return;
            }
            if (Time.time < next)
                return;
            var target = Nearest(item.deployKind == DeployKind.Turret ? 13f : 7f);
            if (target == null)
                return;
            next = Time.time + item.interval;
            Vector3 from = transform.position + Vector3.up * (item.deployKind == DeployKind.Turret ? 0.4f : 0.6f);
            Vector3 to = target.bounds.center;
            if (item.deployKind == DeployKind.Turret)
            {
                // The sentry's bow points along its local -Z: yaw it toward the target's side.
                transform.rotation = Quaternion.Euler(0f, to.x < transform.position.x ? 90f : -90f, 0f);
                if (item.projectile == null)
                    return;
                var go = Instantiate(item.projectile, from, Quaternion.identity);
                go.SetActive(true);
                var p = go.GetComponent<Projectile>();
                p.velocity = ((Vector2)(to - from)).normalized * item.projectileSpeed;
                p.damage = item.damage * (PlayerCombat.Instance != null ? PlayerCombat.Instance.DamageMultiplier : 1f);
                p.fromPlayer = true;
                p.owner = owner;
                p.weaponId = item.id;
                p.sparkColor = item.effectColor;
                p.lifetime = 2f;
                Audio.Sfx.Play("crossbow.shoot", from, 0.6f, 1.2f);
            }
            else
            {
                var h = target.GetComponentInParent<Health>();
                var juice = JuiceEngine.Instance;
                for (int k = 1; k <= 5; k++)
                    juice?.HitSparks(Vector3.Lerp(from, to, k / 5f) + (Vector3)Random.insideUnitCircle * 0.25f, to - from, item.effectColor, 0.15f);
                var info = new DamageInfo
                {
                    amount = item.damage * (PlayerCombat.Instance != null ? PlayerCombat.Instance.DamageMultiplier : 1f),
                    knockback = ((Vector2)(to - from)).normalized * 2f, hitPoint = to, source = owner != null ? owner : gameObject,
                    stun = 0.3f, hitStop = 0.02f, shake = 0.08f, sparkColor = item.effectColor, weaponId = item.id,
                    projectile = true, effect = (int)SkillEffect.Lightning, effectDuration = 0.5f,
                };
                var result = h.TakeDamage(info);
                if (result == DamageResult.Hit || result == DamageResult.Killed)
                    h.GetComponent<StatusEffects>()?.Apply(SkillEffect.Lightning, 0.5f);
                if (result != DamageResult.Ignored)
                    PlayerCombat.Instance?.ReportHit(h, info, result);
                Audio.Sfx.Play("lightning.zap", to);
            }
        }

        void Trap()
        {
            foreach (var c in Physics2D.OverlapCircleAll(transform.position + Vector3.up * 0.3f, 0.8f, DCLayers.EnemyMask))
            {
                var h = c.GetComponentInParent<Health>();
                if (h == null || h.IsDead || Time.time < next)
                    continue;
                next = Time.time + 0.6f;
                var info = new DamageInfo
                {
                    amount = item.damage * (PlayerCombat.Instance != null ? PlayerCombat.Instance.DamageMultiplier : 1f),
                    knockback = Vector2.up * 2f, hitPoint = c.bounds.center, source = owner != null ? owner : gameObject,
                    stun = 1.2f, hitStop = 0.05f, shake = 0.2f, sparkColor = new Color(3f, 0.8f, 0.6f), weaponId = item.id,
                    projectile = true, effect = -1,
                };
                var result = h.TakeDamage(info);
                if (result == DamageResult.Hit || result == DamageResult.Killed)
                    h.GetComponent<StatusEffects>()?.Apply(item.effect, item.effectDuration);
                if (result != DamageResult.Ignored)
                    PlayerCombat.Instance?.ReportHit(h, info, result);
                Audio.Sfx.Play("hazard.spikes", transform.position);
                if (--bites <= 0)
                    until = Time.time + 0.4f;
                return;
            }
        }

        Collider2D Nearest(float range)
        {
            Collider2D best = null;
            float bestD = range;
            Vector2 from = transform.position + Vector3.up * 0.5f;
            foreach (var c in Physics2D.OverlapCircleAll(from, range, DCLayers.EnemyMask))
            {
                var h = c.GetComponentInParent<Health>();
                if (h == null || h.IsDead)
                    continue;
                Vector2 to = c.bounds.center;
                float d = Vector2.Distance(from, to);
                if (d >= bestD || Physics2D.Linecast(from, to, DCLayers.SolidMask).collider != null)
                    continue;
                bestD = d;
                best = c;
            }
            return best;
        }
    }
}
