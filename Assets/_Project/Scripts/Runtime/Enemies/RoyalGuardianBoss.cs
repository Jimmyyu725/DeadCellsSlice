using System.Collections.Generic;
using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Player;
using UnityEngine;

namespace DeadCells.Enemies
{
    /// <summary>
    /// The Royal Guardian: a towering knight with a greatsword the size of a
    /// church door. Overhead slam (ground shockwaves both ways) and a wide
    /// sweep; below half health it chains attacks and the waves get bigger.
    /// </summary>
    public class RoyalGuardianBoss : EnemyBase
    {
        public GameObject shockwavePrefab;
        public float walkSpeed = 2.6f;
        public float slamRange = 3.4f;
        public float sweepRange = 4.6f;
        public int slamFrame = 27;
        public int sweepFrame = 21;
        public float waveSpeed = 9f;

        enum State { Walk, Slam, Sweep, Recover }

        State state;
        float clock;
        bool struck;
        float recoverUntil;
        int chain;

        float Frame => clock * 60f + 1f;
        bool Enraged => health.Normalized < 0.5f;

        protected override bool InSuperArmor() => true;

        protected override void Think(float dt)
        {
            if (!PlayerAlive)
            {
                anim.Play("Idle", 0.2f);
                return;
            }
            float speed = Enraged ? 1.25f : 1f;
            switch (state)
            {
                case State.Walk:
                    anim.SetFacing(DirToPlayer);
                    anim.Play("Run", 0.12f);
                    anim.SetSpeed(0.8f * speed);
                    if (DistX < slamRange && Random.value < 0.6f)
                        Begin(State.Slam, "Attack");
                    else if (DistX < sweepRange)
                        Begin(State.Sweep, "Sweep");
                    break;
                case State.Slam:
                    clock += dt * speed / windupScale;
                    if (!struck && Frame >= slamFrame)
                    {
                        struck = true;
                        StrikeBox(new Vector2(2.2f, 1.2f), new Vector2(3.4f, 2.6f), baseDamage * 1.3f, new Vector2(9f, 7f), 0.4f);
                        Audio.Sfx.Play("boss.slam", transform.position);
                        Audio.Sfx.Play("boss.shockwave", transform.position);
                        var juice = JuiceEngine.Instance;
                        Vector3 tip = transform.position + new Vector3(FacingDir * 3f * transform.localScale.x, 0.2f, 0f);
                        juice?.SlamWave(tip, 3f);
                        juice?.Shake(Vector2.down, 0.8f);
                        juice?.Dust(tip, Vector2.up, 18);
                        foreach (int dir in new[] { -1, 1 })
                        {
                            var p = Fire(shockwavePrefab, tip + new Vector3(dir * 0.6f, 0.4f, 0f), new Vector2(dir * waveSpeed * (Enraged ? 1.3f : 1f), 0f), 0f, baseDamage * 0.7f, false);
                            if (p != null)
                            {
                                p.lifetime = 2.2f;
                                p.pierce = true;
                                p.hitRadius = Enraged ? 0.75f : 0.55f;
                                p.sparkColor = new Color(3f, 2.2f, 0.9f);
                            }
                        }
                    }
                    if (Frame >= anim.FrameCount("Attack"))
                        Finish();
                    break;
                case State.Sweep:
                    clock += dt * speed / windupScale;
                    if (!struck && Frame >= sweepFrame && Frame <= sweepFrame + 6)
                        struck = StrikeBox(new Vector2(2.4f, 1.3f), new Vector2(5f, 2.4f), baseDamage, new Vector2(10f, 4f), 0.3f);
                    if (Frame >= anim.FrameCount("Sweep"))
                        Finish();
                    break;
                case State.Recover:
                    anim.Play("Idle", 0.15f);
                    if (Time.time >= recoverUntil)
                        state = State.Walk;
                    break;
            }
        }

        void Begin(State s, string clip)
        {
            state = s;
            clock = 0f;
            struck = false;
            anim.SetFacing(DirToPlayer);
            anim.Restart(clip, 0f);
            anim.SetSpeed((Enraged ? 1.25f : 1f) / windupScale);
            Telegraph();
            if (s == State.Sweep)
                Invoke(nameof(SweepSound), Mathf.Max(0f, (sweepFrame - 8) / 60f * windupScale / (Enraged ? 1.25f : 1f)));
        }

        void SweepSound() => Audio.Sfx.Play("boss.sweep", transform.position + Vector3.up);

        void Finish()
        {
            anim.SetSpeed(1f);
            if (Enraged && chain < 1)
            {
                chain++;
                Begin(DistX < slamRange ? State.Slam : State.Sweep, DistX < slamRange ? "Attack" : "Sweep");
                return;
            }
            chain = 0;
            state = State.Recover;
            recoverUntil = Time.time + (Enraged ? 0.55f : 0.95f);
        }

        public override void Stun(float seconds, Vector2 knockback)
        {
            base.Stun(seconds, knockback);
            state = State.Recover;
            recoverUntil = Time.time + seconds * 0.4f;
        }

        protected override void Move(float dt)
        {
            Vector2 v = body.linearVelocity;
            if (state == State.Walk && DistX > 2.2f && GroundAhead(DirToPlayer, 1.2f))
                v.x = Mathf.MoveTowards(v.x, DirToPlayer * walkSpeed * (Enraged ? 1.3f : 1f), 20f * dt);
            else if (state == State.Slam && Frame < slamFrame)
                v.x = Mathf.MoveTowards(v.x, FacingDir * 1.2f, 20f * dt);
            else
                v.x = Mathf.MoveTowards(v.x, 0f, 30f * dt);
            body.linearVelocity = v;
        }
    }
}
