using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// Left behind by a bursting skill: a poison cloud (Miasma Jar) that
    /// poisons everything inside, or a vortex (Abyss Inkwell) whose small,
    /// frequent hits drag enemies toward its centre.
    /// </summary>
    public class LingeringZone : MonoBehaviour
    {
        ItemDef item;
        GameObject owner;
        float radius, tickDamage, until, nextTick;
        bool fromPlayer;

        public void Setup(ItemDef def, GameObject source, float r, float damagePerTick, bool player)
        {
            item = def;
            owner = source;
            radius = Mathf.Max(1.5f, r);
            tickDamage = damagePerTick;
            fromPlayer = player;
            until = Time.time + def.duration;
            Audio.Sfx.Play(def.burstKind == BurstKind.Vortex ? "tk.summon" : "hazard.sorrow", transform.position);
        }

        bool Vortex => item.burstKind == BurstKind.Vortex;

        void Update()
        {
            if (item == null || Time.time > until)
            {
                Destroy(gameObject);
                return;
            }
            var juice = JuiceEngine.Instance;
            Vector2 c = transform.position;
            if (juice != null)
            {
                if (Vortex)
                {
                    for (int k = 0; k < 2; k++)
                    {
                        float a = Random.value * Mathf.PI * 2f;
                        float r = radius * Random.Range(0.3f, 1f);
                        juice.Embers(c + new Vector2(Mathf.Cos(a), Mathf.Sin(a) * 0.7f) * r, 1, new Color(1.6f, 0.6f, 3.2f));
                    }
                    juice.Embers(c, 1, new Color(2.4f, 1.2f, 3.6f));
                }
                else
                {
                    juice.Dust(c + Random.insideUnitCircle * radius * 0.8f, Vector2.up, 2, new Color(0.45f, 1.1f, 0.35f, 0.8f));
                }
            }
            if (Time.time < nextTick)
                return;
            nextTick = Time.time + (Vortex ? 0.22f : item.interval);
            int mask = fromPlayer ? DCLayers.EnemyMask : (1 << DCLayers.Player);
            foreach (var col in Physics2D.OverlapCircleAll(c, radius, mask))
            {
                var h = col.GetComponentInParent<Health>();
                if (h == null || h.IsDead)
                    continue;
                Vector2 to = c - (Vector2)col.bounds.center;
                var info = new DamageInfo
                {
                    amount = Vortex ? tickDamage * 0.4f : tickDamage,
                    knockback = Vortex ? to.normalized * Mathf.Min(item.power, to.magnitude * 3f) : Vector2.zero,
                    hitPoint = col.bounds.center,
                    source = owner != null ? owner : gameObject,
                    stun = Vortex ? 0.25f : 0f,
                    sparkColor = Vortex ? new Color(1.6f, 0.6f, 3.2f) : new Color(0.9f, 3f, 0.6f),
                    weaponId = item.id,
                    projectile = true,
                    effect = -1,
                };
                var result = h.TakeDamage(info);
                if (!Vortex && (result == DamageResult.Hit || result == DamageResult.Killed))
                    h.GetComponent<StatusEffects>()?.Apply(SkillEffect.Poison, 3f);
            }
        }
    }
}
