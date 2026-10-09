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
    /// The Time Keeper, shoveling starlight to keep the timeline from snapping.
    /// Phase 1: shovel swings and starlight tosses. Phase 2 (66%): slams that
    /// raise starlight pillars under you, and Rewind (heals and drags you back
    /// three seconds unless interrupted). Phase 3 (33%): faster, calls ticks.
    /// </summary>
    public class TimeKeeperBoss : EnemyBase
    {
        public GameObject starPrefab;
        public GameObject pillarPrefab;
        public GameObject tickPrefab;
        public float walkSpeed = 3f;
        public float swingRange = 3.4f;
        public int swingFrame = 22;
        public int slamFrame = 26;
        public int tossFrame = 19;
        public float rewindInterruptFraction = 0.08f;

        enum State { Walk, Swing, Slam, Toss, Rewind, Recover }

        State state;
        float clock;
        bool fired;
        float recoverUntil;
        int phase = 1;
        float rewindDamage;
        float nextRewind;
        readonly Queue<(float time, Vector3 pos)> history = new Queue<(float, Vector3)>();

        float Frame => clock * 60f + 1f;
        float Speed => phase == 3 ? 1.3f : phase == 2 ? 1.12f : 1f;

        protected override bool InSuperArmor() => true;

        protected override void OnEngage()
        {
            GameUIBridge.Say?.Invoke(Loc.Get("npc.keeper.name"), Loc.Get("npc.keeper.intro"));
            nextRewind = Time.time + 18f;
        }

        protected override void OnDamaged(DamageInfo info, DamageResult result)
        {
            base.OnDamaged(info, result);
            if (state == State.Rewind)
                rewindDamage += info.amount;
            int newPhase = health.Normalized < 0.33f ? 3 : health.Normalized < 0.66f ? 2 : 1;
            if (newPhase > phase)
            {
                phase = newPhase;
                GameUIBridge.Say?.Invoke(Loc.Get("npc.keeper.name"), Loc.Get(phase == 2 ? "npc.keeper.phase2" : "npc.keeper.phase3"));
                JuiceEngine.Instance?.Shake(Vector2.up, 0.7f);
                hitFlash?.Flash(new Color(3f, 2.6f, 1.2f), 1f);
                if (phase == 3)
                    SummonTicks();
            }
        }

        protected override void Update()
        {
            // Remember where the player was (for Rewind).
            if (player != null)
            {
                history.Enqueue((Time.time, player.position));
                while (history.Count > 0 && Time.time - history.Peek().time > 3.2f)
                    history.Dequeue();
            }
            base.Update();
        }

        protected override void Think(float dt)
        {
            if (!PlayerAlive)
            {
                anim.Play("Idle", 0.2f);
                return;
            }
            switch (state)
            {
                case State.Walk:
                    anim.SetFacing(DirToPlayer);
                    anim.Play("Run", 0.12f);
                    anim.SetSpeed(0.85f * Speed);
                    if (phase >= 2 && Time.time >= nextRewind)
                        Begin(State.Rewind, "Rewind");
                    else if (DistX < swingRange)
                        Begin(State.Swing, "Swing");
                    else if (phase >= 2 && Random.value < 0.012f)
                        Begin(State.Slam, "Slam");
                    else if (DistX > 5f && Random.value < 0.02f)
                        Begin(State.Toss, "Toss");
                    break;
                case State.Swing:
                    Advance(dt);
                    if (!fired && Frame >= swingFrame && Frame <= swingFrame + 6)
                        fired = StrikeBox(new Vector2(2.1f, 1.3f), new Vector2(3.6f, 2.4f), baseDamage, new Vector2(9f, 5f), 0.3f);
                    if (Frame >= anim.FrameCount("Swing"))
                        Finish(0.6f);
                    break;
                case State.Slam:
                    Advance(dt);
                    if (!fired && Frame >= slamFrame)
                    {
                        fired = true;
                        JuiceEngine.Instance?.Shake(Vector2.down, 0.7f);
                        int count = phase == 3 ? 4 : 3;
                        for (int i = 0; i < count; i++)
                        {
                            float x = player.position.x + (i - (count - 1) * 0.5f) * 3.2f;
                            SpawnPillar(new Vector3(x, transform.position.y, 0f), 0.75f + i * 0.12f);
                        }
                    }
                    if (Frame >= anim.FrameCount("Slam"))
                        Finish(0.7f);
                    break;
                case State.Toss:
                    Advance(dt);
                    if (!fired && Frame >= tossFrame)
                    {
                        fired = true;
                        int n = phase == 1 ? 3 : 5;
                        Vector3 from = transform.position + new Vector3(FacingDir * 1.2f, 2.6f, 0f);
                        for (int i = 0; i < n; i++)
                        {
                            float time = 0.9f + i * 0.12f;
                            Vector2 vel = LobAtPlayer(from, 18f, time) + new Vector2((i - (n - 1) * 0.5f) * 1.4f, 0f);
                            var p = Fire(starPrefab, from, vel, 18f, baseDamage * 0.75f);
                            if (p != null)
                            {
                                p.explodeRadius = 1.2f;
                                p.sparkColor = new Color(3.2f, 2.8f, 1.6f);
                                p.lifetime = 3f;
                            }
                        }
                    }
                    if (Frame >= anim.FrameCount("Toss"))
                        Finish(0.6f);
                    break;
                case State.Rewind:
                    Advance(dt);
                    hitFlash?.Flash(new Color(1.6f, 1.8f, 3f), 0.4f + Mathf.PingPong(Time.time * 3f, 0.4f));
                    if (rewindDamage >= health.maxHealth * rewindInterruptFraction)
                    {
                        // Interrupted: staggers and the clock spins back on him.
                        JuiceEngine.Instance?.Popup(transform.position + Vector3.up * 3.6f, "STUN", new Color(1f, 0.85f, 0.3f), true);
                        nextRewind = Time.time + 20f;
                        Finish(1.6f);
                        break;
                    }
                    if (!fired && Frame >= 50)
                    {
                        fired = true;
                        GameUIBridge.Say?.Invoke(Loc.Get("npc.keeper.name"), Loc.Get("npc.keeper.rewind"));
                        health.Heal(health.maxHealth * 0.12f);
                        var pc = PlayerController.Main;
                        if (pc != null && history.Count > 0)
                        {
                            Vector3 back = history.Peek().pos;
                            JuiceEngine.Instance?.Embers(pc.transform.position + Vector3.up, 30, new Color(1.6f, 1.8f, 3.2f));
                            pc.Teleport(back + Vector3.up * 0.1f);
                            JuiceEngine.Instance?.Embers(back + Vector3.up, 30, new Color(1.6f, 1.8f, 3.2f));
                        }
                        JuiceEngine.Instance?.Shake(Vector2.left, 0.6f);
                        nextRewind = Time.time + (phase == 3 ? 16f : 22f);
                    }
                    if (Frame >= anim.FrameCount("Rewind"))
                        Finish(0.5f);
                    break;
                case State.Recover:
                    anim.Play("Idle", 0.15f);
                    if (Time.time >= recoverUntil)
                        state = State.Walk;
                    break;
            }
        }

        void Advance(float dt) => clock += dt * Speed / windupScale;

        void Begin(State s, string clip)
        {
            state = s;
            clock = 0f;
            fired = false;
            rewindDamage = 0f;
            anim.SetFacing(DirToPlayer);
            anim.Restart(clip, 0f);
            anim.SetSpeed(Speed / windupScale);
            Telegraph(s != State.Rewind);
        }

        void Finish(float rest)
        {
            anim.SetSpeed(1f);
            state = State.Recover;
            recoverUntil = Time.time + rest / Speed;
        }

        void SpawnPillar(Vector3 at, float delay)
        {
            var hit = Physics2D.Raycast((Vector2)at + Vector2.up * 3f, Vector2.down, 10f, DCLayers.GroundMask);
            if (hit.collider != null)
                at.y = hit.point.y;
            if (pillarPrefab == null)
                return;
            var go = Instantiate(pillarPrefab, at, Quaternion.identity);
            go.SetActive(true);
            var pillar = go.GetComponent<StarPillar>() ?? go.AddComponent<StarPillar>();
            pillar.delay = delay;
            pillar.damage = Damage(baseDamage * 0.9f);
            pillar.owner = gameObject;
        }

        void SummonTicks()
        {
            if (tickPrefab == null)
                return;
            foreach (int dir in new[] { -1, 1 })
            {
                var go = Instantiate(tickPrefab, transform.position + new Vector3(dir * 4f, 5f, 0f), Quaternion.identity, transform.parent);
                go.GetComponent<EnemyBase>()?.Configure(4, false);
                JuiceEngine.Instance?.Embers(go.transform.position, 20, new Color(1.6f, 1.8f, 3.2f));
            }
        }

        protected override void Move(float dt)
        {
            Vector2 v = body.linearVelocity;
            if (state == State.Walk && DistX > 2f && GroundAhead(DirToPlayer, 1.2f))
                v.x = Mathf.MoveTowards(v.x, DirToPlayer * walkSpeed * Speed, 20f * dt);
            else
                v.x = Mathf.MoveTowards(v.x, 0f, 30f * dt);
            body.linearVelocity = v;
        }
    }
}
