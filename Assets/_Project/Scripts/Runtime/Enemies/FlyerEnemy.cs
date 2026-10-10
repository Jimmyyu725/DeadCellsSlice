using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using UnityEngine;

namespace DeadCells.Enemies
{
    /// <summary>Gossamer-winged tick: hovers above, telegraphs, then dives in a line.</summary>
    public class FlyerEnemy : EnemyBase
    {
        public float flySpeed = 3.6f;
        public float diveSpeed = 15f;
        public float hoverAbove = 3.2f;
        public float diveCooldown = 2.2f;
        public string flyClip = "Run";
        public string diveClip = "Attack";

        enum State { Hover, Windup, Dive, Recover }

        State state;
        float t;
        Vector2 diveDir;
        float nextDive;
        bool hit;
        Vector3 home;

        protected override void Start()
        {
            base.Start();
            home = transform.position;
        }

        protected override bool InSuperArmor() => state == State.Dive;

        protected override void OnInterrupted()
        {
            state = State.Recover;
            t = 0f;
        }

        protected override void Think(float dt)
        {
            t += dt;
            switch (state)
            {
                case State.Hover:
                    anim.Play(flyClip, 0.1f);
                    if (CanSeePlayer(1.2f))
                    {
                        anim.SetFacing(DirToPlayer);
                        if (Time.time >= nextDive && DistX < 6f)
                        {
                            state = State.Windup;
                            t = 0f;
                            Telegraph(false);
                            anim.Restart(anim.Has(diveClip) ? diveClip : flyClip, 0f);
                        }
                    }
                    break;
                case State.Windup:
                    if (t >= 0.65f * windupScale)
                    {
                        state = State.Dive;
                        t = 0f;
                        hit = false;
                        diveDir = player != null ? ((Vector2)(player.position + Vector3.up * 0.9f) - (Vector2)transform.position).normalized : Vector2.down;
                    }
                    break;
                case State.Dive:
                    if (!hit)
                        hit = StrikeBox(new Vector2(0f, 0.4f), new Vector2(1.2f, 1.2f), baseDamage, new Vector2(5f, 4f));
                    if (t > 0.6f || hit || Physics2D.Raycast(transform.position, diveDir, 0.6f, DCLayers.SolidMask).collider != null)
                    {
                        state = State.Recover;
                        t = 0f;
                    }
                    break;
                case State.Recover:
                    anim.Play(flyClip, 0.1f);
                    if (t > 0.7f)
                    {
                        state = State.Hover;
                        nextDive = Time.time + diveCooldown * Random.Range(0.8f, 1.3f);
                    }
                    break;
            }
        }

        protected override void Move(float dt)
        {
            Vector2 v = body.linearVelocity;
            Vector2 target;
            switch (state)
            {
                case State.Dive:
                    body.linearVelocity = diveDir * diveSpeed;
                    return;
                case State.Windup:
                    body.linearVelocity = Vector2.MoveTowards(v, -diveDir * 1.5f, 20f * dt);
                    return;
                default:
                    if (PlayerAlive && CanSeePlayer(1.4f))
                        target = (Vector2)player.position + new Vector2(-DirToPlayer * 2.5f, hoverAbove + Mathf.Sin(Time.time * 2f) * 0.4f);
                    else
                        target = (Vector2)home + new Vector2(Mathf.Sin(Time.time * 0.5f) * 2f, Mathf.Sin(Time.time * 1.3f) * 0.4f);
                    break;
            }
            Vector2 to = target - (Vector2)transform.position;
            Vector2 desired = to.magnitude > 0.3f ? to.normalized * flySpeed : Vector2.zero;
            if (Physics2D.Raycast(transform.position, desired.normalized, 0.8f, DCLayers.SolidMask).collider != null)
                desired = new Vector2(0f, Mathf.Sign(desired.y) * flySpeed * 0.5f);
            body.linearVelocity = Vector2.MoveTowards(v, desired, 14f * dt);
        }
    }
}
