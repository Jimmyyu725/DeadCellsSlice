using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Meta;
using DeadCells.Player;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// Area hazard checked by overlap each physics step (hazards sit on a
    /// layer that does not collide with bodies). Spikes bounce you up; deep
    /// liquids and pits send you back to the last safe ledge.
    /// </summary>
    public class Hazard : MonoBehaviour
    {
        public enum Kind { Spikes, Liquid, Pit, Fire }

        public Kind kind;
        public Vector2 size = Vector2.one;
        [Tooltip("Fraction of the player's max health per contact.")]
        public float damageFraction = 0.12f;
        public float flatDamage = 6f;
        public bool returnToSafety;
        public bool harmless;
        public float cooldown = 0.8f;
        public Color splashColor = new Color(0.6f, 0.3f, 1f);

        float nextHit;

        void FixedUpdate()
        {
            if (harmless && !returnToSafety)
                return;
            Vector2 c = (Vector2)transform.position;
            var col = Physics2D.OverlapBox(c, size, 0f, DCLayers.PlayerMask);
            if (col == null)
                return;
            var player = col.GetComponentInParent<PlayerController>();
            if (player == null || player.State == PlayerState.Dead || Time.time < nextHit)
                return;
            nextHit = Time.time + cooldown;
            var juice = JuiceEngine.Instance;
            if (!harmless && !Cheats.GodMode)
            {
                float dmg = (player.Health.maxHealth * damageFraction + flatDamage) * Difficulty.EnemyDamage;
                bool wasInv = player.Health.IsInvulnerable;
                if (kind != Kind.Spikes)
                    player.Health.InvulnerableUntil = 0f;
                player.Health.TakeDamage(new DamageInfo
                {
                    amount = dmg,
                    knockback = new Vector2(-player.Facing * 3f, 9f),
                    hitPoint = player.transform.position,
                    source = gameObject,
                    effect = -1,
                });
                if (wasInv && kind == Kind.Spikes)
                    return;
            }
            juice?.Ichor(player.transform.position, Vector2.up, splashColor, 16);
            if (returnToSafety && !player.Health.IsDead)
            {
                player.Teleport(player.LastSafePosition + Vector3.up * 0.1f);
                juice?.Embers(player.transform.position + Vector3.up, 20, new Color(1.6f, 0.8f, 3f));
            }
            else if (kind == Kind.Spikes)
            {
                var v = player.Body.linearVelocity;
                player.Body.linearVelocity = new Vector2(v.x, 11f);
            }
        }

        void OnDrawGizmos()
        {
            Gizmos.color = new Color(1f, 0.2f, 0.4f, 0.35f);
            Gizmos.DrawCube(transform.position, size);
        }
    }
}
