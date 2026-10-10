using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Meta;
using DeadCells.Player;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>Clockmaker's Lung furnace vent: periodic burst of starlight fire.</summary>
    public class FurnaceVent : MonoBehaviour
    {
        public ParticleSystem flames;
        public Light glow;
        public float period = 3.2f;
        public float burst = 1.1f;
        public Vector2 area = new Vector2(1.6f, 3f);
        public float damage = 14f;
        float t;
        float nextHit;
        bool wasActive;

        void Start() => t = Random.value * period;

        void Update()
        {
            t += Time.deltaTime;
            float phase = t % period;
            bool warn = phase > period - burst - 0.6f && phase <= period - burst;
            bool active = phase > period - burst;
            if (flames != null)
            {
                var e = flames.emission;
                e.rateOverTime = active ? 90f : warn ? 12f : 0f;
            }
            if (glow != null)
                glow.intensity = active ? 4f : warn ? 1.5f : 0.3f;
            if (active && !wasActive)
                Audio.Sfx.Play("hazard.vent", transform.position);
            wasActive = active;
            if (!active || Time.time < nextHit)
                return;
            var c = (Vector2)transform.position + new Vector2(0f, area.y * 0.5f);
            var col = Physics2D.OverlapBox(c, area, 0f, 1 << DCLayers.Player);
            var h = col != null ? col.GetComponentInParent<Health>() : null;
            if (h == null)
                return;
            nextHit = Time.time + 0.6f;
            h.TakeDamage(new DamageInfo
            {
                amount = damage * Difficulty.EnemyDamage,
                knockback = new Vector2(0f, 8f),
                hitPoint = h.transform.position + Vector3.up,
                source = gameObject,
                effect = -1,
            });
            h.GetComponent<StatusEffects>()?.Apply(Items.SkillEffect.Fire, 2f);
        }
    }
}
