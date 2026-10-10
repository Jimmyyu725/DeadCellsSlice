using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Meta;
using DeadCells.Player;
using UnityEngine;

namespace DeadCells.Enemies
{
    /// <summary>
    /// The Collector, waiting in the Observatory past the Time Keeper (2+ Boss
    /// Cells). He floats above the arena: cell volleys, a lunging dash and a
    /// rain of stolen starlight. Phase 2 (66%) summons his jars' inhabitants;
    /// phase 3 (33%) he tries to drink the flame out of you (a pull you must
    /// outrun or interrupt with damage).
    /// </summary>
    public class CollectorBoss : EnemyBase
    {
        public GameObject orbPrefab;
        public GameObject starPrefab;
        public GameObject[] minions = new GameObject[0];
        public Transform model;
        public float hoverHeight = 3.2f;
        public float hoverDistance = 5.5f;
        public float moveSpeed = 5f;

        enum State { Hover, Volley, Dash, Rain, Summon, Drain, Recover }

        State state;
        float clock;
        bool fired;
        float nextAttack, nextSummon, nextDrain;
        int phase = 1;
        int dashDir;
        float drainDamage;
        Vector3 modelBase;

        float Speed => phase == 3 ? 1.3f : phase == 2 ? 1.15f : 1f;
        float Windup(float seconds) => seconds * windupScale / Speed;

        protected override bool InSuperArmor() => true;

        protected override void Start()
        {
            base.Start();
            body.gravityScale = 0f;
            if (model != null)
                modelBase = model.localPosition;
        }

        protected override void OnEngage()
        {
            GameUIBridge.Say?.Invoke(Loc.Get("npc.collector.name"), Loc.Get("npc.collector_boss.intro"));
            nextAttack = Time.time + 1.5f;
            nextSummon = Time.time + 12f;
            nextDrain = Time.time + 8f;
        }

        protected override void OnDamaged(DamageInfo info, DamageResult result)
        {
            base.OnDamaged(info, result);
            if (state == State.Drain)
                drainDamage += info.amount;
            int newPhase = health.Normalized < 0.33f ? 3 : health.Normalized < 0.66f ? 2 : 1;
            if (newPhase > phase)
            {
                phase = newPhase;
                GameUIBridge.Say?.Invoke(Loc.Get("npc.collector.name"), Loc.Get(phase == 2 ? "npc.collector_boss.phase2" : "npc.collector_boss.phase3"));
                JuiceEngine.Instance?.Shake(Vector2.up, 0.7f);
                hitFlash?.Flash(new Color(0.8f, 2.6f, 3.4f), 1f);
                if (phase == 2)
                    Summon();
            }
        }

        protected override void Update()
        {
            base.Update();
            // Procedural life: a slow bob and a lean into the movement.
            if (model != null && !IsDead)
            {
                float bob = Mathf.Sin(Time.time * 2.2f) * 0.12f;
                model.localPosition = modelBase + new Vector3(0f, bob, 0f);
                float lean = Mathf.Clamp(-body.linearVelocity.x * 1.6f, -14f, 14f);
                model.localRotation = Quaternion.Slerp(model.localRotation, Quaternion.Euler(0f, 0f, lean), Time.deltaTime * 6f);
            }
        }

        protected override void Think(float dt)
        {
            if (!PlayerAlive)
            {
                state = State.Hover;
                return;
            }
            clock += dt;
            switch (state)
            {
                case State.Hover:
                    anim.SetFacing(DirToPlayer);
                    if (Time.time < nextAttack)
                        break;
                    if (phase >= 3 && Time.time >= nextDrain)
                        Begin(State.Drain);
                    else if (phase >= 2 && Time.time >= nextSummon)
                        Begin(State.Summon);
                    else
                    {
                        float r = Random.value;
                        Begin(r < 0.4f ? State.Volley : r < 0.7f ? State.Dash : State.Rain);
                    }
                    break;
                case State.Volley:
                    if (!fired && clock >= Windup(0.7f))
                    {
                        fired = true;
                        int n = phase == 1 ? 3 : phase == 2 ? 5 : 7;
                        Vector3 from = transform.position + new Vector3(FacingDir * 0.8f, 1.6f, 0f);
                        Vector2 aim = AimAtPlayer(from, 11f);
                        Audio.Sfx.Play("enemy.cast", from);
                        for (int i = 0; i < n; i++)
                        {
                            float a = (i - (n - 1) * 0.5f) * 11f;
                            var p = Fire(orbPrefab, from, Quaternion.Euler(0f, 0f, a) * aim, 0f, baseDamage * 0.7f);
                            if (p != null)
                            {
                                p.sparkColor = new Color(0.8f, 2.6f, 3.4f);
                                p.lifetime = 4f;
                            }
                        }
                    }
                    if (clock >= Windup(0.7f) + 0.5f)
                        Finish(0.9f);
                    break;
                case State.Dash:
                    if (clock < Windup(0.6f))
                    {
                        hitFlash?.Flash(new Color(0.8f, 2.6f, 3.4f), 0.3f + Mathf.PingPong(clock * 4f, 0.4f));
                        break;
                    }
                    if (!fired && clock < Windup(0.6f) + 0.65f)
                        fired = StrikeBox(new Vector2(0f, 1.4f), new Vector2(2.2f, 2.6f), baseDamage * 1.2f, new Vector2(10f, 6f), 0.3f);
                    if (clock >= Windup(0.6f) + 0.75f)
                        Finish(1.0f);
                    break;
                case State.Rain:
                    if (!fired && clock >= Windup(0.5f))
                    {
                        fired = true;
                        int n = phase == 1 ? 6 : 9;
                        Audio.Sfx.Play("tk.star", transform.position + Vector3.up * 3f);
                        for (int i = 0; i < n; i++)
                        {
                            Vector3 from = player.position + new Vector3((i - (n - 1) * 0.5f) * 1.9f + Random.Range(-0.4f, 0.4f), 9f + Random.Range(0f, 2f), 0f);
                            var p = Fire(starPrefab, from, new Vector2(0f, -2f), 14f, baseDamage * 0.65f);
                            if (p != null)
                            {
                                p.explodeRadius = 1f;
                                p.sparkColor = new Color(0.9f, 2.4f, 3.4f);
                                p.lifetime = 3f;
                            }
                        }
                    }
                    if (clock >= Windup(0.5f) + 0.4f)
                        Finish(1.1f);
                    break;
                case State.Summon:
                    if (!fired && clock >= Windup(0.8f))
                    {
                        fired = true;
                        Summon();
                        nextSummon = Time.time + 22f;
                    }
                    if (clock >= Windup(0.8f) + 0.3f)
                        Finish(0.8f);
                    break;
                case State.Drain:
                    hitFlash?.Flash(new Color(0.6f, 2.2f, 3.4f), 0.3f + Mathf.PingPong(Time.time * 3f, 0.4f));
                    if (drainDamage >= health.maxHealth * 0.06f)
                    {
                        JuiceEngine.Instance?.Popup(transform.position + Vector3.up * 3.4f, "STUN", new Color(1f, 0.85f, 0.3f), true);
                        nextDrain = Time.time + 18f;
                        Finish(1.8f);
                        break;
                    }
                    Drain(dt);
                    if (clock >= 3f)
                    {
                        nextDrain = Time.time + 16f;
                        Finish(0.8f);
                    }
                    break;
                case State.Recover:
                    if (clock >= 0f)
                        state = State.Hover;
                    break;
            }
        }

        void Begin(State s)
        {
            state = s;
            clock = 0f;
            fired = false;
            drainDamage = 0f;
            anim.SetFacing(DirToPlayer);
            dashDir = DirToPlayer;
            Telegraph(s != State.Summon);
            if (s == State.Drain)
            {
                GameUIBridge.Say?.Invoke(Loc.Get("npc.collector.name"), Loc.Get("npc.collector_boss.drain"));
                Audio.Sfx.Play("tk.rewind");
            }
        }

        void Finish(float rest)
        {
            state = State.Recover;
            clock = -rest / Speed;
            nextAttack = Time.time + rest / Speed + Random.Range(0.3f, 0.9f) / Speed;
        }

        void Summon()
        {
            if (minions == null || minions.Length == 0)
                return;
            Audio.Sfx.Play("tk.summon", transform.position + Vector3.up * 2f);
            foreach (int dir in new[] { -1, 1 })
            {
                var prefab = minions[Random.Range(0, minions.Length)];
                if (prefab == null)
                    continue;
                Vector3 at = transform.position + new Vector3(dir * 3f, 0.5f, 0f);
                var hit = Physics2D.Raycast(at, Vector2.down, 12f, DCLayers.GroundMask);
                if (hit.collider != null)
                    at.y = hit.point.y + 0.05f;
                var go = Instantiate(prefab, at, Quaternion.identity, transform.parent);
                go.GetComponent<EnemyBase>()?.Configure(4, false);
                JuiceEngine.Instance?.Embers(at + Vector3.up, 24, new Color(0.8f, 2.6f, 3.4f));
            }
        }

        /// <summary>Pull the player in; close enough, the flame drains into his jars.</summary>
        void Drain(float dt)
        {
            var pc = PlayerController.Main;
            if (pc == null)
                return;
            Vector2 to = (Vector2)(transform.position + Vector3.up * 1.2f) - (Vector2)pc.transform.position;
            float d = to.magnitude;
            if (d < 10f && d > 0.5f && pc.Body != null)
                pc.Body.position += to.normalized * Mathf.Lerp(4.5f, 1.5f, d / 10f) * dt;
            if (Random.value < dt * 20f)
                JuiceEngine.Instance?.Embers(pc.transform.position + Vector3.up, 1, new Color(1.6f, 1f, 3.2f));
            if (d < 2.6f && Random.value < dt * 4f)
            {
                var h = pc.Health;
                var result = h.TakeDamage(new DamageInfo { amount = Damage(baseDamage * 0.35f), source = gameObject, hitPoint = pc.transform.position + Vector3.up, effect = -1 });
                if (result == DamageResult.Hit)
                    health.Heal(health.maxHealth * 0.01f);
            }
        }

        protected override void Move(float dt)
        {
            Vector2 v = body.linearVelocity;
            if (player == null)
            {
                body.linearVelocity = Vector2.MoveTowards(v, Vector2.zero, 20f * dt);
                return;
            }
            Vector2 target;
            float speed = moveSpeed * Speed;
            if (state == State.Dash && clock >= Windup(0.6f))
            {
                // A straight lunge through where the player stood.
                body.linearVelocity = new Vector2(dashDir * 17f * Speed, 0f);
                return;
            }
            if (state == State.Drain)
                target = transform.position;
            else
            {
                int side = transform.position.x > player.position.x ? 1 : -1;
                target = new Vector2(player.position.x + side * hoverDistance, player.position.y + hoverHeight);
            }
            Vector2 to = target - (Vector2)transform.position;
            Vector2 want = to.magnitude > 0.3f ? to.normalized * Mathf.Min(speed, to.magnitude * 3f) : Vector2.zero;
            body.linearVelocity = Vector2.MoveTowards(v, want, 25f * dt);
        }
    }
}
