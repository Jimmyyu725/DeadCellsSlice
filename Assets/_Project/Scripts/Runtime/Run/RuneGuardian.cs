using DeadCells.Combat;
using DeadCells.Enemies;
using DeadCells.FX;
using DeadCells.Meta;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// An elite that carries one of the runes: tougher, wrapped in the rune's
    /// colour, and it drops the rune tablet when it dies.
    /// </summary>
    public class RuneGuardian : MonoBehaviour
    {
        public string rune;
        Health health;
        Light aura;
        float nextEmber;

        public static RuneGuardian Make(EnemyBase enemy, string rune)
        {
            var g = enemy.gameObject.AddComponent<RuneGuardian>();
            g.rune = rune;
            return g;
        }

        void Start()
        {
            health = GetComponent<Health>();
            if (health != null)
            {
                health.maxHealth *= 2.5f;
                health.SetCurrent(health.maxHealth);
                health.Died += OnDied;
            }
            var lg = new GameObject("RuneAura");
            lg.transform.SetParent(transform, false);
            lg.transform.localPosition = new Vector3(0f, 1.4f, -0.8f);
            aura = lg.AddComponent<Light>();
            aura.type = LightType.Point;
            aura.color = Runes.ColorOf(rune) / 3.4f;
            aura.intensity = 3f;
            aura.range = 4f;
        }

        void Update()
        {
            if (health == null || health.IsDead || Time.time < nextEmber)
                return;
            nextEmber = Time.time + 0.12f;
            JuiceEngine.Instance?.Embers(transform.position + new Vector3(Random.Range(-0.5f, 0.5f), Random.Range(0.3f, 2f), -0.3f), 1, Runes.ColorOf(rune));
            if (aura != null)
                aura.intensity = 2.5f + Mathf.Sin(Time.time * 4f) * 0.8f;
        }

        void OnDied(DamageInfo info)
        {
            if (!Runes.Has(rune))
                RunePickup.Spawn(rune, transform.position);
        }

        void OnDestroy()
        {
            if (health != null)
                health.Died -= OnDied;
        }
    }
}
