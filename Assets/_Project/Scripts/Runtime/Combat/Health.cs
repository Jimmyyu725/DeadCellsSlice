using System;
using UnityEngine;

namespace DeadCells.Combat
{
    public enum DamageResult
    {
        Ignored,
        Hit,
        Blocked,
        Parried,
        Killed,
    }

    public struct DamageInfo
    {
        public float amount;
        public Vector2 knockback;     // world-space impulse direction * strength
        public Vector2 hitPoint;
        public GameObject source;
        public bool critical;
        public float stun;            // seconds of hit-stun applied to the victim
        public float hitStop;         // global freeze on connection
        public float shake;           // camera trauma added on connection
        public Color sparkColor;
    }

    /// <summary>Anything that can be damaged; owners may veto or convert hits (shield).</summary>
    public class Health : MonoBehaviour
    {
        public float maxHealth = 100f;
        [SerializeField] float current = -1f;

        public float Current => current;
        public float Normalized => maxHealth > 0f ? current / maxHealth : 0f;
        public bool IsDead => current <= 0f;
        public float InvulnerableUntil { get; set; }
        public bool IsInvulnerable => Time.time < InvulnerableUntil;

        /// <summary>Optional interceptor (shield/parry). Return a non-Hit result to modify the outcome.</summary>
        public Func<DamageInfo, DamageResult> Interceptor;

        public event Action<DamageInfo, DamageResult> Damaged;
        public event Action<DamageInfo> Died;
        public event Action<float> Healed;

        void Awake()
        {
            if (current < 0f)
                current = maxHealth;
        }

        public void ResetHealth()
        {
            current = maxHealth;
        }

        public DamageResult TakeDamage(DamageInfo info)
        {
            if (IsDead || IsInvulnerable)
                return DamageResult.Ignored;

            var result = DamageResult.Hit;
            if (Interceptor != null)
            {
                result = Interceptor(info);
                if (result == DamageResult.Ignored)
                    return result;
                if (result == DamageResult.Parried)
                {
                    Damaged?.Invoke(info, result);
                    return result;
                }
                if (result == DamageResult.Blocked)
                    info.amount *= 0.2f;
            }

            current = Mathf.Max(0f, current - info.amount);
            if (current <= 0f)
            {
                Damaged?.Invoke(info, DamageResult.Killed);
                Died?.Invoke(info);
                return DamageResult.Killed;
            }
            Damaged?.Invoke(info, result);
            return result;
        }

        public void Heal(float amount)
        {
            if (IsDead)
                return;
            current = Mathf.Min(maxHealth, current + amount);
            Healed?.Invoke(amount);
        }
    }
}
