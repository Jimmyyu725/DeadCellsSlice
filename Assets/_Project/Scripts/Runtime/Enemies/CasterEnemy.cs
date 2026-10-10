using DeadCells.FX;
using DeadCells.Items;
using UnityEngine;

namespace DeadCells.Enemies
{
    /// <summary>
    /// Orchid-lantern monk: floats above the floor at a distance, casts slow
    /// orbs, and chants backwards to reverse the player's projectiles.
    /// </summary>
    public class CasterEnemy : EnemyBase
    {
        public GameObject orbPrefab;
        public float hoverHeight = 0.6f;
        public float keepDistance = 7f;
        public float moveSpeed = 2.4f;
        public float castCooldown = 2.6f;
        public int castReleaseFrame = 24;
        public float orbSpeed = 7f;
        public float reverseRadius = 4.5f;
        public float reverseCooldown = 2.2f;
        public Light lantern;

        bool casting;
        bool released;
        float clock;
        float nextCast;
        float nextReverse;
        float bob;

        float Frame => clock * 60f + 1f;

        protected override void OnInterrupted() => casting = false;

        protected override void Think(float dt)
        {
            bob += dt;
            if (lantern != null)
                lantern.intensity = 1.6f + Mathf.Sin(bob * 3f) * 0.3f + (Time.time < nextReverse - reverseCooldown + 0.4f ? 3f : 0f);
            TryReverse();
            if (!CanSeePlayer(1.3f))
            {
                anim.Play("Idle", 0.15f);
                return;
            }
            anim.SetFacing(DirToPlayer);
            if (casting)
            {
                clock += dt / windupScale;
                if (!released && Frame >= castReleaseFrame)
                {
                    released = true;
                    Vector3 from = transform.position + new Vector3(FacingDir * 0.7f, 1.8f, 0f);
                    var p = Fire(orbPrefab, from, AimAtPlayer(from, orbSpeed), 0f, baseDamage);
                    Audio.Sfx.Play("enemy.orb", from);
                    if (p != null)
                    {
                        p.lifetime = 5f;
                        p.sparkColor = new Color(1.4f, 3f, 1.2f);
                    }
                }
                if (Frame >= anim.FrameCount("Cast"))
                {
                    casting = false;
                    nextCast = Time.time + castCooldown * Random.Range(0.85f, 1.2f);
                }
                return;
            }
            anim.Play(Mathf.Abs(body.linearVelocity.x) > 0.4f ? "Run" : "Idle", 0.12f);
            if (Time.time >= nextCast)
            {
                casting = true;
                released = false;
                clock = 0f;
                anim.Restart("Cast", 0f);
                anim.SetSpeed(1f / windupScale);
                hitFlash?.Flash(new Color(1.2f, 2.6f, 0.8f), 0.5f);
                Audio.Sfx.Play("enemy.cast", transform.position + Vector3.up * 1.8f);
            }
        }

        void TryReverse()
        {
            if (Time.time < nextReverse)
                return;
            foreach (var p in Projectile.Live)
            {
                // A shot the player parried back stays the player's: no ping-pong.
                if (p == null || !p.fromPlayer || !p.reflectable || p.ShieldReflected)
                    continue;
                if (Vector2.Distance(p.transform.position, transform.position + Vector3.up * 1.2f) > reverseRadius)
                    continue;
                p.Reverse(gameObject);
                nextReverse = Time.time + reverseCooldown;
                JuiceEngine.Instance?.Popup(transform.position + Vector3.up * 2.6f, "<<", new Color(0.7f, 1f, 0.5f), false);
                hitFlash?.Flash(new Color(1.2f, 2.8f, 0.8f), 0.8f);
                break;
            }
        }

        protected override void Move(float dt)
        {
            // Hover: hold a fixed height over the floor below, drift to keep distance.
            Vector2 v = body.linearVelocity;
            var hit = Physics2D.Raycast((Vector2)transform.position + Vector2.up * 0.5f, Vector2.down, 6f, Core.DCLayers.GroundMask);
            float targetY = hit.collider != null ? hit.point.y + hoverHeight + Mathf.Sin(bob * 1.8f) * 0.15f : transform.position.y;
            v.y = Mathf.Clamp((targetY - transform.position.y) * 6f, -4f, 4f);
            float desired = 0f;
            if (PlayerAlive && CanSeePlayer(1.3f) && !casting)
            {
                float d = DistX;
                int dir = DirToPlayer;
                if (d < keepDistance - 1.5f) desired = -dir * moveSpeed;
                else if (d > keepDistance + 2f) desired = dir * moveSpeed;
                if (WallAhead(desired > 0 ? 1 : -1, 0.8f))
                    desired = 0f;
            }
            v.x = Mathf.MoveTowards(v.x, desired, 12f * dt);
            body.linearVelocity = v;
        }
    }
}
