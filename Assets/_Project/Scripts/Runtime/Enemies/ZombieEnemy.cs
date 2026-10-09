using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using UnityEngine;

namespace DeadCells.Enemies
{
    /// <summary>
    /// Prisoners' Quarters zombie: patrols, spots the player, closes in, then
    /// telegraphs (wind-up + "!" + glow) before a lunging claw strike.
    /// Has super-armour during the strike; staggers otherwise. Parries stun it.
    /// </summary>
    [RequireComponent(typeof(Rigidbody2D), typeof(Health))]
    public class ZombieEnemy : MonoBehaviour, IStunnable
    {
        enum State { Patrol, Chase, Windup, Strike, Recover, Hurt, Stunned, Dead }

        [Header("Movement")]
        public float patrolSpeed = 1.6f;
        public float chaseSpeed = 4.6f;
        public float patrolRange = 3.5f;
        public float aggroRange = 10f;
        public float verticalAggro = 3f;
        public float attackRange = 1.9f;

        [Header("Attack")]
        public float damage = 14f;
        public float windupSpeed = 0.62f;   // animator speed during the telegraph (slower = longer read)
        public float strikeSpeed = 1.25f;
        public Vector2Int strikeFrames = new Vector2Int(19, 24);
        public float lungeSpeed = 7f;
        public Vector2 hitboxOffset = new Vector2(1.0f, 1.0f);
        public Vector2 hitboxSize = new Vector2(1.6f, 1.5f);
        public float cooldown = 0.9f;

        [Header("Reactions")]
        public float hurtTime = 0.24f;
        public float corpseTime = 0.65f;
        public int cellsOnDeath = 6;

        [Header("References")]
        public CharacterAnimator anim;
        public HitFlash hitFlash;
        public SquashStretch squash;

        Rigidbody2D body;
        Health health;
        Transform player;
        Health playerHealth;
        State state = State.Patrol;
        float stateTime;
        float stateDuration;
        float attackClock;
        float nextAttackTime;
        bool strikeHit;
        Vector3 home;
        int patrolDir = 1;
        Vector2 knock;

        public bool IsDead => state == State.Dead;
        // Frame numbers match the Blender timeline (frame 1 = clip start).
        float AttackFrame => attackClock * 60f + 1f;
        public static event System.Action<ZombieEnemy> Killed;

        void Awake()
        {
            body = GetComponent<Rigidbody2D>();
            health = GetComponent<Health>();
            body.freezeRotation = true;
            body.gravityScale = 3.2f;
            body.interpolation = RigidbodyInterpolation2D.Interpolate;
            health.Damaged += OnDamaged;
            health.Died += OnDied;
            home = transform.position;
            patrolDir = Random.value > 0.5f ? 1 : -1;
        }

        void Start()
        {
            var p = FindAnyObjectByType<Player.PlayerController>();
            if (p != null)
            {
                player = p.transform;
                playerHealth = p.GetComponent<Health>();
            }
            anim.SetFacing(patrolDir);
            anim.Restart("Idle", 0f, Random.value);
        }

        void Enter(State next, float duration = 0f)
        {
            state = next;
            stateTime = 0f;
            stateDuration = duration;
            anim.SetSpeed(1f);
        }

        void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f || state == State.Dead)
                return;
            stateTime += dt;
            switch (state)
            {
                case State.Patrol:
                    if (CanSeePlayer())
                    {
                        Enter(State.Chase);
                        JuiceEngine.Instance?.Popup(transform.position + Vector3.up * 2.3f, "?", new Color(1f, 0.9f, 0.5f), false);
                    }
                    break;
                case State.Chase:
                    if (!CanSeePlayer(1.5f))
                        Enter(State.Patrol);
                    else if (Mathf.Abs(player.position.x - transform.position.x) <= attackRange && Time.time >= nextAttackTime
                             && !playerHealth.IsDead)
                        BeginWindup();
                    break;
                case State.Windup:
                    attackClock += dt * windupSpeed;
                    if (AttackFrame >= strikeFrames.x - 1)
                    {
                        Enter(State.Strike);
                        anim.SetSpeed(strikeSpeed);
                        strikeHit = false;
                        squash?.Punch(new Vector2(1.2f, 0.85f));
                    }
                    break;
                case State.Strike:
                    attackClock += dt * strikeSpeed;
                    if (!strikeHit && AttackFrame >= strikeFrames.x && AttackFrame <= strikeFrames.y)
                        TryHitPlayer();
                    if (AttackFrame > strikeFrames.y)
                        Enter(State.Recover);
                    break;
                case State.Recover:
                    attackClock += dt * strikeSpeed;
                    anim.SetSpeed(strikeSpeed);
                    if (AttackFrame >= anim.FrameCount("Attack") + 1)
                    {
                        nextAttackTime = Time.time + cooldown;
                        Enter(State.Chase);
                    }
                    break;
                case State.Hurt:
                case State.Stunned:
                    if (stateTime >= stateDuration)
                        Enter(CanSeePlayer() ? State.Chase : State.Patrol);
                    break;
            }
            Animate();
        }

        void FixedUpdate()
        {
            if (state == State.Dead)
            {
                body.linearVelocity = new Vector2(Mathf.MoveTowards(body.linearVelocity.x, 0f, 30f * Time.fixedDeltaTime), body.linearVelocity.y);
                return;
            }
            Vector2 v = body.linearVelocity;
            float dt = Time.fixedDeltaTime;
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
                    int dir = player.position.x > transform.position.x ? 1 : -1;
                    anim.SetFacing(dir);
                    bool canMove = GroundAhead(dir) && !WallAhead(dir) && Mathf.Abs(player.position.x - transform.position.x) > attackRange * 0.7f;
                    v.x = Mathf.MoveTowards(v.x, canMove ? dir * chaseSpeed : 0f, 40f * dt);
                    break;
                case State.Windup:
                    v.x = Mathf.MoveTowards(v.x, 0f, 40f * dt);
                    break;
                case State.Strike:
                    float f = AttackFrame;
                    v.x = f <= strikeFrames.y && GroundAhead(anim.Facing) ? anim.Facing * lungeSpeed : Mathf.MoveTowards(v.x, 0f, 60f * dt);
                    break;
                case State.Recover:
                    v.x = Mathf.MoveTowards(v.x, 0f, 50f * dt);
                    break;
                case State.Hurt:
                case State.Stunned:
                    knock = Vector2.MoveTowards(knock, Vector2.zero, 30f * dt);
                    v.x = knock.x;
                    break;
            }
            body.linearVelocity = v;
        }

        void Animate()
        {
            switch (state)
            {
                case State.Patrol:
                    anim.Play(Mathf.Abs(body.linearVelocity.x) > 0.2f ? "Run" : "Idle", 0.12f);
                    if (anim.Current == "Run")
                        anim.SetSpeed(0.55f);
                    break;
                case State.Chase:
                    anim.Play(Mathf.Abs(body.linearVelocity.x) > 0.3f ? "Run" : "Idle", 0.08f);
                    break;
            }
        }

        bool CanSeePlayer(float rangeScale = 1f)
        {
            if (player == null || playerHealth == null || playerHealth.IsDead)
                return false;
            Vector2 d = player.position - transform.position;
            return Mathf.Abs(d.x) <= aggroRange * rangeScale && Mathf.Abs(d.y) <= verticalAggro * rangeScale;
        }

        bool GroundAhead(int dir)
        {
            Vector2 origin = (Vector2)transform.position + new Vector2(dir * 0.55f, 0.3f);
            return Physics2D.Raycast(origin, Vector2.down, 1.1f, DCLayers.GroundMask).collider != null;
        }

        bool WallAhead(int dir)
        {
            Vector2 origin = (Vector2)transform.position + new Vector2(0f, 0.8f);
            return Physics2D.Raycast(origin, new Vector2(dir, 0f), 0.6f, DCLayers.SolidMask).collider != null;
        }

        void BeginWindup()
        {
            int dir = player.position.x > transform.position.x ? 1 : -1;
            anim.SetFacing(dir);
            Enter(State.Windup);
            attackClock = 0f;
            anim.Restart("Attack", 0f);
            anim.SetSpeed(windupSpeed);
            hitFlash?.Flash(new Color(2.6f, 0.5f, 0.2f), 0.55f);
            squash?.Punch(new Vector2(0.9f, 1.12f));
            JuiceEngine.Instance?.Popup(transform.position + Vector3.up * 2.4f, "!", new Color(1f, 0.25f, 0.2f), true);
        }

        void TryHitPlayer()
        {
            Vector2 center = (Vector2)transform.position + new Vector2(hitboxOffset.x * anim.Facing, hitboxOffset.y);
            var col = Physics2D.OverlapBox(center, hitboxSize, 0f, 1 << DCLayers.Player);
            if (col == null)
                return;
            var target = col.GetComponentInParent<Health>();
            if (target == null)
                return;
            strikeHit = true;
            target.TakeDamage(new DamageInfo
            {
                amount = damage,
                knockback = new Vector2(anim.Facing * 7.5f, 4f),
                hitPoint = col.bounds.center,
                source = gameObject,
                stun = 0.25f,
            });
        }

        // ------------------------------------------------------------ reactions

        void OnDamaged(DamageInfo info, DamageResult result)
        {
            if (result == DamageResult.Killed)
                return;
            hitFlash?.Flash(new Color(2.4f, 2.4f, 2.4f));
            squash?.Punch(new Vector2(1.18f, 0.86f));
            if (state == State.Strike)
                return; // super-armour while lunging
            knock = info.knockback;
            body.linearVelocity = new Vector2(info.knockback.x, Mathf.Max(body.linearVelocity.y, info.knockback.y * 0.35f));
            Enter(State.Hurt, hurtTime + info.stun);
            anim.Restart("Hurt", 0f);
            nextAttackTime = Mathf.Max(nextAttackTime, Time.time + 0.35f);
        }

        public void Stun(float seconds, Vector2 knockback)
        {
            if (state == State.Dead)
                return;
            knock = knockback;
            body.linearVelocity = knockback;
            Enter(State.Stunned, seconds);
            anim.Restart("Hurt", 0f);
            anim.SetSpeed(0.25f);
            hitFlash?.Flash(new Color(2.4f, 2.0f, 0.6f), 0.9f);
            JuiceEngine.Instance?.Popup(transform.position + Vector3.up * 2.4f, "STUN", new Color(1f, 0.85f, 0.3f), false);
        }

        void OnDied(DamageInfo info)
        {
            Enter(State.Dead);
            anim.Restart("Death", 0f);
            body.linearVelocity = new Vector2(info.knockback.x * 1.2f, Mathf.Max(3f, info.knockback.y));
            gameObject.layer = DCLayers.Fx;
            foreach (var c in GetComponentsInChildren<Collider2D>())
                if (!c.isTrigger)
                    c.gameObject.layer = DCLayers.Fx;
            Killed?.Invoke(this);
            Invoke(nameof(Burst), corpseTime);
        }

        void Burst()
        {
            var juice = JuiceEngine.Instance;
            Vector3 c = transform.position + Vector3.up * 0.6f;
            if (juice != null)
            {
                juice.CellBurst(c, cellsOnDeath);
                juice.Ichor(c, Vector2.up, new Color(0.3f, 0.6f, 0.15f), 22);
                juice.Embers(c, 18, new Color(1.2f, 2.2f, 0.6f));
                juice.Dust(transform.position, Vector2.up, 10, new Color(0.35f, 0.45f, 0.3f, 0.6f));
                juice.Shake(Vector2.up, 0.15f);
            }
            gameObject.SetActive(false);
        }

        void OnDrawGizmosSelected()
        {
            Gizmos.color = new Color(1f, 0.3f, 0.1f, 0.4f);
            int f = anim != null && Application.isPlaying ? anim.Facing : 1;
            Gizmos.DrawWireCube(transform.position + new Vector3(hitboxOffset.x * f, hitboxOffset.y), hitboxSize);
            Gizmos.color = new Color(1f, 1f, 0.2f, 0.25f);
            Gizmos.DrawWireCube(transform.position, new Vector3(aggroRange * 2f, verticalAggro * 2f, 0.1f));
        }
    }
}
