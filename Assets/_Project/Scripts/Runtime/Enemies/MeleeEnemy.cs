using DeadCells.FX;
using UnityEngine;

namespace DeadCells.Enemies
{
    /// <summary>
    /// Patrol → chase → telegraphed lunge. Drowned prisoners (zombies) and
    /// clock-hand sentinels. Super-armour during the strike; parries stun.
    /// </summary>
    public class MeleeEnemy : EnemyBase
    {
        enum State { Patrol, Chase, Windup, Strike, Recover }

        [Header("Movement")]
        public float patrolSpeed = 1.6f;
        public float chaseSpeed = 4.6f;
        public float patrolRange = 3.5f;
        public float attackRange = 1.9f;

        [Header("Attack")]
        public string attackClip = "Attack";
        public float windupSpeed = 0.62f;
        public float strikeSpeed = 1.25f;
        public Vector2Int strikeFrames = new Vector2Int(19, 24);
        [Tooltip("Seconds the anticipation pose is held before the strike (scaled by difficulty).")]
        public float windupHold = 0.16f;
        [Tooltip("Delay after first spotting the player before the first attack may start.")]
        public float reactionDelay = 0.4f;
        public float lungeSpeed = 7f;
        public Vector2 hitboxOffset = new Vector2(1.0f, 1.0f);
        public Vector2 hitboxSize = new Vector2(1.6f, 1.5f);
        public Vector2 knockback = new Vector2(7.5f, 4f);
        public float cooldown = 0.9f;

        State state = State.Patrol;
        float clock;
        float held;
        float nextAttack;
        bool hit;
        Vector3 home;
        int patrolDir = 1;

        float Frame => clock * 60f + 1f;

        protected override void Start()
        {
            base.Start();
            home = transform.position;
            patrolDir = anim.Facing;
        }

        void Enter(State s)
        {
            state = s;
            anim.SetSpeed(1f);
        }

        [Tooltip("Telegraphed attacks cannot be interrupted by ordinary hits (parries and stuns still work).")]
        public bool armoredWindup = true;

        protected override bool InSuperArmor() => state == State.Strike || (armoredWindup && state == State.Windup);

        protected override void OnInterrupted()
        {
            if (state == State.Windup || state == State.Strike || state == State.Recover)
            {
                nextAttack = Mathf.Max(nextAttack, Time.time + 0.35f);
                Enter(State.Chase);
            }
        }

        protected override void Think(float dt)
        {
            switch (state)
            {
                case State.Patrol:
                    if (CanSeePlayer())
                    {
                        Enter(State.Chase);
                        nextAttack = Mathf.Max(nextAttack, Time.time + reactionDelay * windupScale);
                        JuiceEngine.Instance?.Popup(transform.position + Vector3.up * 2.3f, "?", new Color(1f, 0.9f, 0.5f), false);
                    }
                    anim.Play(Mathf.Abs(body.linearVelocity.x) > 0.2f ? "Run" : "Idle", 0.12f);
                    if (anim.Current == "Run")
                        anim.SetSpeed(0.55f);
                    break;
                case State.Chase:
                    if (!CanSeePlayer(1.5f))
                        Enter(State.Patrol);
                    else if (DistX <= attackRange && Mathf.Abs(DistY) < 1.6f && Time.time >= nextAttack)
                        BeginWindup();
                    else
                        anim.Play(Mathf.Abs(body.linearVelocity.x) > 0.3f ? "Run" : "Idle", 0.08f);
                    break;
                case State.Windup:
                    if (Frame < strikeFrames.x - 1)
                        clock += dt * windupSpeed / windupScale;
                    else
                    {
                        // Hold the anticipation pose so the "!" gives time to react.
                        anim.SetSpeed(0f);
                        held += dt;
                    }
                    if (Frame >= strikeFrames.x - 1 && held >= windupHold * windupScale)
                    {
                        Enter(State.Strike);
                        anim.SetSpeed(strikeSpeed);
                        hit = false;
                        squash?.Punch(new Vector2(1.2f, 0.85f));
                    }
                    break;
                case State.Strike:
                    clock += dt * strikeSpeed;
                    if (!hit && Frame >= strikeFrames.x && Frame <= strikeFrames.y)
                        hit = StrikeBox(hitboxOffset, hitboxSize, baseDamage, knockback);
                    if (Frame > strikeFrames.y)
                        Enter(State.Recover);
                    break;
                case State.Recover:
                    clock += dt * strikeSpeed;
                    anim.SetSpeed(strikeSpeed);
                    if (Frame >= anim.FrameCount(attackClip) + 1)
                    {
                        nextAttack = Time.time + cooldown;
                        Enter(State.Chase);
                    }
                    break;
            }
        }

        void BeginWindup()
        {
            anim.SetFacing(DirToPlayer);
            Enter(State.Windup);
            clock = 0f;
            held = 0f;
            anim.Restart(attackClip, 0f);
            anim.SetSpeed(windupSpeed / windupScale);
            Telegraph();
        }

        protected override void Move(float dt)
        {
            Vector2 v = body.linearVelocity;
            switch (state)
            {
                case State.Patrol:
                    if (Mathf.Abs(transform.position.x - home.x) > patrolRange && Mathf.Sign(transform.position.x - home.x) == patrolDir)
                        patrolDir = -patrolDir;
                    if (!GroundAhead(patrolDir) || WallAhead(patrolDir))
                        patrolDir = -patrolDir;
                    anim.SetFacing(patrolDir);
                    v.x = Mathf.MoveTowards(v.x, patrolDir * patrolSpeed, 30f * dt);
                    break;
                case State.Chase:
                    int dir = DirToPlayer;
                    anim.SetFacing(dir);
                    bool canMove = GroundAhead(dir) && !WallAhead(dir) && DistX > attackRange * 0.7f;
                    v.x = Mathf.MoveTowards(v.x, canMove ? dir * chaseSpeed : 0f, 40f * dt);
                    break;
                case State.Windup:
                case State.Recover:
                    v.x = Mathf.MoveTowards(v.x, 0f, 45f * dt);
                    break;
                case State.Strike:
                    v.x = Frame <= strikeFrames.y && GroundAhead(anim.Facing) ? anim.Facing * lungeSpeed : Mathf.MoveTowards(v.x, 0f, 60f * dt);
                    break;
            }
            body.linearVelocity = v;
        }
    }
}
