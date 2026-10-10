using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Run;
using UnityEngine;

namespace DeadCells.Player
{
    public enum PlayerState
    {
        Locomotion,
        Attack,
        Dodge,
        PoundHang,
        PoundFall,
        PoundLand,
        Block,
        Hurt,
        Dead,
        Mantle,
        WakeUp,
        Frozen,
    }

    /// <summary>
    /// The Beheaded's movement: near-instant acceleration with zero slide on
    /// release, variable-height jump with coyote time and jump buffering,
    /// dodge roll / air dash with invulnerability frames, and a ground pound
    /// that cancels air velocity and deals area damage on landing.
    /// Combat lives in PlayerCombat; this class owns the state machine.
    /// </summary>
    [RequireComponent(typeof(Rigidbody2D), typeof(CapsuleCollider2D), typeof(Health))]
    public class PlayerController : MonoBehaviour
    {
        [Header("Run")]
        public float runSpeed = 8.6f;
        public float groundAcceleration = 140f;
        [Tooltip("Deceleration with no input: high enough to stop within ~2 frames (zero slide).")]
        public float groundDeceleration = 320f;
        public float airAcceleration = 85f;
        public float airDeceleration = 60f;

        [Header("Jump")]
        public float jumpHeight = 3.7f; // clears 3-tile platform steps with margin
        public float timeToApex = 0.38f;
        public float fallGravityMultiplier = 1.45f;
        public float maxFallSpeed = 24f;
        [Tooltip("Upward velocity kept when jump is released early.")]
        [Range(0f, 1f)] public float jumpCutMultiplier = 0.5f;
        [Tooltip("A tapped jump still rises this long before release can cut it (about 2.4 tiles).")]
        public float minJumpTime = 0.12f;
        float jumpStartTime;
        public float apexHangThreshold = 1.6f;
        public float apexGravityMultiplier = 0.55f;
        public float coyoteTime = 0.12f;

        [Header("Double jump")]
        [Tooltip("Jumps available in mid-air, refilled on landing.")]
        public int airJumps = 1;
        public float doubleJumpHeight = 2.7f;
        [Header("Wall jump (Spider rune)")]
        public float wallSlideSpeed = 3f;
        public float wallJumpLock = 0.16f;
        float lastWallTime = -10f, wallJumpLockUntil;
        int lastWallSide, wallJumpDir;
        public int WallJumps { get; private set; }
        public float jumpBufferTime = 0.15f;

        [Header("Dodge roll / air dash")]
        public float dodgeDuration = 20f / 60f;
        public float dodgeDistance = 4.6f;
        public Vector2 dodgeInvulnerableWindow = new Vector2(0.02f, 0.27f);
        public float dodgeCooldown = 0.12f;

        [Header("Ground pound")]
        public float poundHangTime = 0.11f;
        public float poundSpeed = 34f;
        public float poundMinHeight = 1.2f;
        public float poundRadius = 2.7f;
        public float poundDamage = 32f;
        public float poundStun = 0.9f;
        public float poundRecovery = 0.3f;

        [Header("Hurt")]
        public float hurtDuration = 0.28f;
        public float hurtInvulnerability = 0.9f;

        [Header("Ledge mantle")]
        public float mantleTime = 0.16f;
        public float mantleMaxHeight = 2.3f;

        [Header("Stats")]
        public float baseMaxHealth = 200f;

        [Header("References")]
        public CharacterAnimator anim;
        public SquashStretch squash;
        public HitFlash hitFlash;
        public Renderer flameRenderer;
        public SecondaryMotion secondaryMotion;

        public IInputSource InputSource { get; set; }
        public InputFrame Input { get; private set; }
        public PlayerState State { get; private set; } = PlayerState.Locomotion;
        public float StateTime { get; private set; }
        public bool Grounded { get; private set; }
        public int Facing => anim != null ? anim.Facing : 1;
        public Rigidbody2D Body => body;
        public Health Health => health;
        public Vector2 Velocity => body.linearVelocity;
        public Vector3 FeetPosition => transform.position;

        Rigidbody2D body;
        CapsuleCollider2D capsule;
        Health health;
        int blockSlot;
        PlayerCombat combat;
        MaterialPropertyBlock flameBlock;

        float gravity;
        float jumpVelocity;
        float lastGroundedTime = -10f;
        float lastJumpPressedTime = -10f;
        float lastDodgePressedTime = -10f;

        /// <summary>Time the last dodge roll started (for after-dodge crits).</summary>
        public float LastDodgeTime { get; private set; } = -10f;

        /// <summary>
        /// Health lost to the last hits that can still be won back by hitting
        /// enemies soon (Dead Cells' recovery); drains away after a short delay.
        /// </summary>
        public float Recoverable { get; private set; }
        float recoverDrainAt;

        public float RecoverRatio => 0.6f * (1f + 0.5f * ItemForge.AmuletCount(Affix.Recovery)) * Mutations.RecoveryMultiplier;

        /// <summary>Called when the player deals damage: wins back recoverable health.</summary>
        public void Recover(float dealt)
        {
            if (Recoverable <= 0f || dealt <= 0f || State == PlayerState.Dead)
                return;
            float heal = Mathf.Min(Recoverable, dealt * 0.5f + 1f);
            Recoverable -= heal;
            health.Heal(heal);
        }
        bool jumpCutApplied;
        bool isJumping;
        bool airDashAvailable = true;
        int airJumpsLeft;
        float doubleJumpVelocity;
        float dodgeReadyTime;
        int dodgeDirection;
        float fallSpeedBeforeLanding;
        Collider2D groundCollider;
        Collider2D droppingThrough;
        float dropThroughUntil;
        float footstepTimer;
        Vector2 hurtKnockback;
        bool poundImpactDone;
        Vector2 mantleFrom, mantleTo;
        Vector3 lastSafePosition;
        float lastSafeTime;

        /// <summary>Last grounded spot away from hazards (pits and liquids send you back here).</summary>
        public Vector3 LastSafePosition => lastSafePosition;
        public bool InControl => State == PlayerState.Locomotion || State == PlayerState.Attack;
        public PlayerCombat Combat => combat;

        static readonly int LeanId = Shader.PropertyToID("_Lean");

        public event System.Action Died;

        public static PlayerController Main { get; private set; }

        void Awake()
        {
            Main = this;
            body = GetComponent<Rigidbody2D>();
            capsule = GetComponent<CapsuleCollider2D>();
            health = GetComponent<Health>();
            combat = GetComponent<PlayerCombat>();
            flameBlock = new MaterialPropertyBlock();
            Meta.Outfits.Apply(gameObject);
            gravity = 2f * jumpHeight / (timeToApex * timeToApex);
            jumpVelocity = gravity * timeToApex;
            doubleJumpVelocity = Mathf.Sqrt(2f * gravity * doubleJumpHeight);
            body.gravityScale = 0f;
            body.freezeRotation = true;
            body.interpolation = RigidbodyInterpolation2D.Interpolate;
            body.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
            health.Damaged += OnDamaged;
            health.LethalSave = () => Mutations.TryRevive(this) || AssistRevive();
            health.IncomingMultiplier = () => Difficulty.PlayerDamageTaken;
            health.Died += OnDied;
            if (InputSource == null)
                InputSource = GetComponent<IInputSource>();
        }

        // -------------------------------------------------------------- update

        void Update()
        {
            if (InputSource != null)
                Input = InputSource.Read();
            if (Cheats.GodMode && State != PlayerState.Dead)
                health.InvulnerableUntil = Mathf.Max(health.InvulnerableUntil, Time.time + 0.2f);
            if (Recoverable > 0f)
            {
                if (Time.time > recoverDrainAt)
                    Recoverable = Mathf.Max(0f, Recoverable - health.maxHealth * 0.07f * Time.deltaTime);
                Recoverable = Mathf.Min(Recoverable, health.maxHealth - health.Current);
            }
            var input = Input;
            if (input.jumpPressed)
                lastJumpPressedTime = Time.time;
            if (input.dodgePressed)
                lastDodgePressedTime = Time.time;
            combat?.BufferInput(input);

            if (Time.deltaTime <= 0f)
                return; // hit-stop: buffer input only

            StateTime += Time.deltaTime;
            switch (State)
            {
                case PlayerState.Locomotion:
                    UpdateLocomotion(input);
                    break;
                case PlayerState.Attack:
                {
                    if (TryDodge(input) || TryGroundPound(input))
                        break;
                    // The shield comes up at any moment of an attack.
                    int raised = combat.HeldShield(input);
                    if (raised >= 0)
                    {
                        combat.CancelAttack();
                        blockSlot = raised;
                        EnterState(PlayerState.Block);
                        break;
                    }
                    if (combat.CanCancel && (Grounded || airJumpsLeft > 0) && Time.time - lastJumpPressedTime <= jumpBufferTime)
                    {
                        // Recovery frames can be cancelled into a jump.
                        combat.EndEarly();
                        EnterState(PlayerState.Locomotion);
                        break;
                    }
                    if (combat.TrySwitchAction())
                        break;
                    if (combat.UpdateAttack(Time.deltaTime))
                    {
                        EnterState(PlayerState.Locomotion);
                        break;
                    }
                    // No recovery lock: walking away ends the swing.
                    if (combat.CanCancel && input.moveX != 0f && !combat.AnyAttackBuffered)
                    {
                        combat.EndEarly();
                        EnterState(PlayerState.Locomotion);
                    }
                    break;
                }
                case PlayerState.Dodge:
                    UpdateDodge();
                    break;
                case PlayerState.PoundHang:
                    if (StateTime >= poundHangTime)
                        EnterState(PlayerState.PoundFall);
                    break;
                case PlayerState.PoundFall:
                    if (Grounded)
                        EnterState(PlayerState.PoundLand);
                    break;
                case PlayerState.PoundLand:
                    if (StateTime >= poundRecovery)
                        EnterState(PlayerState.Locomotion);
                    break;
                case PlayerState.Block:
                    if (input.moveX != 0f)
                        anim.SetFacing((int)input.moveX);
                    if (combat.HeldShield(input) < 0)
                    {
                        combat.EndBlock();
                        EnterState(PlayerState.Locomotion);
                    }
                    else if (TryDodge(input))
                    {
                        combat.EndBlock();
                    }
                    break;
                case PlayerState.Hurt:
                    if (StateTime >= hurtDuration)
                        EnterState(PlayerState.Locomotion);
                    break;
                case PlayerState.Mantle:
                    if (StateTime >= mantleTime)
                        EnterState(PlayerState.Locomotion);
                    break;
                case PlayerState.WakeUp:
                    if (StateTime >= anim.Length("Wake_Up") - 0.05f)
                        EnterState(PlayerState.Locomotion);
                    break;
            }
            UpdateFlameLean();
        }

        void UpdateLocomotion(InputFrame input)
        {
            if (input.moveX != 0f)
                anim.SetFacing((int)input.moveX);

            if (TryGroundPound(input) || TryDodge(input))
                return;
            if (input.backpackPressed)
                combat.SwapBackpack();
            int shield = combat.HeldShield(input);
            if (shield >= 0)
            {
                blockSlot = shield;
                EnterState(PlayerState.Block);
                return;
            }
            if (combat.TryStartAction())
            {
                EnterState(PlayerState.Attack);
                return;
            }
            if (Grounded && combat.TryDrink())
            {
                EnterState(PlayerState.Attack);
                return;
            }
            if (input.interactPressed && Run.Interactable.Current != null)
            {
                Run.Interactable.Current.Interact(this);
                return;
            }
            if (TryMantle(input))
                return;

            if (Grounded)
            {
                bool running = Mathf.Abs(body.linearVelocity.x) > 0.6f && input.moveX != 0f;
                anim.Play(running ? "Run" : "Idle", running ? 0.05f : 0.08f);
                if (running)
                {
                    footstepTimer -= Time.deltaTime;
                    if (footstepTimer <= 0f)
                    {
                        footstepTimer = 0.2f;
                        Audio.Sfx.Play("player.step", FeetPosition);
                        JuiceEngine.Instance?.Dust(FeetPosition, new Vector2(-Facing, 0.4f), 2);
                    }
                }
            }
            else
            {
                anim.Play(body.linearVelocity.y > 0.5f ? "Jump_Rise" : "Jump_Fall", 0.08f);
            }
        }

        // -------------------------------------------------------------- physics

        void FixedUpdate()
        {
            float dt = Time.fixedDeltaTime;
            bool wasGrounded = Grounded;
            float preVy = body.linearVelocity.y;
            CheckGround();
            if (Grounded)
            {
                lastGroundedTime = Time.time;
                airDashAvailable = true;
                airJumpsLeft = airJumps;
                if (!wasGrounded)
                    OnLanded(fallSpeedBeforeLanding);
                if (groundCollider != null && groundCollider.gameObject.layer == DCLayers.Ground && Time.time - lastSafeTime > 0.25f
                    && State == PlayerState.Locomotion && Physics2D.OverlapCircle(transform.position + Vector3.up * 0.5f, 1.2f, HazardMask) == null)
                {
                    lastSafePosition = transform.position;
                    lastSafeTime = Time.time;
                }
            }
            fallSpeedBeforeLanding = Mathf.Min(preVy, 0f);

            Vector2 v = body.linearVelocity;
            switch (State)
            {
                case PlayerState.Locomotion:
                    v = Locomotion(v, dt);
                    break;
                case PlayerState.Attack:
                    v = combat.AttackVelocity(v, dt, Grounded);
                    v.y = ApplyGravity(v.y, dt, 0.65f);
                    break;
                case PlayerState.Dodge:
                    float t = Mathf.Clamp01(StateTime / dodgeDuration);
                    // Ease-out burst: fast start, controlled end.
                    float speed = dodgeDistance / dodgeDuration * 1.6f * (1f - t * t);
                    v.x = dodgeDirection * Mathf.Max(speed, runSpeed * 0.35f);
                    v.y = Grounded ? Mathf.Min(v.y, 0f) : 0f;
                    break;
                case PlayerState.PoundHang:
                    v = Vector2.zero;
                    break;
                case PlayerState.PoundFall:
                    v = new Vector2(0f, -poundSpeed);
                    break;
                case PlayerState.PoundLand:
                case PlayerState.Block:
                    v.x = Mathf.MoveTowards(v.x, 0f, groundDeceleration * dt);
                    v.y = ApplyGravity(v.y, dt, 1f);
                    break;
                case PlayerState.Hurt:
                    hurtKnockback = Vector2.MoveTowards(hurtKnockback, Vector2.zero, 40f * dt);
                    v.x = hurtKnockback.x;
                    v.y = ApplyGravity(v.y, dt, 1f);
                    break;
                case PlayerState.Dead:
                case PlayerState.WakeUp:
                case PlayerState.Frozen:
                    v.x = Mathf.MoveTowards(v.x, 0f, groundDeceleration * dt);
                    v.y = ApplyGravity(v.y, dt, 1f);
                    break;
                case PlayerState.Mantle:
                    float m = Mathf.Clamp01(StateTime / mantleTime);
                    float e = 1f - (1f - m) * (1f - m);
                    // Up first, then over the lip.
                    Vector2 target = new Vector2(Mathf.Lerp(mantleFrom.x, mantleTo.x, Mathf.Clamp01(e * 1.6f - 0.6f)),
                        Mathf.Lerp(mantleFrom.y, mantleTo.y, Mathf.Clamp01(e * 1.4f)));
                    body.MovePosition(target);
                    v = Vector2.zero;
                    break;
            }
            if (State != PlayerState.Mantle)
                body.linearVelocity = v;
            else
                body.linearVelocity = Vector2.zero;

            if (droppingThrough != null && Time.time > dropThroughUntil)
            {
                Physics2D.IgnoreCollision(capsule, droppingThrough, false);
                droppingThrough = null;
            }
        }

        Vector2 Locomotion(Vector2 v, float dt)
        {
            var input = Input;
            bool spider = !Grounded && Runes.Has(Runes.Spider);
            int wall = spider ? WallContact() : 0;
            if (wall != 0)
            {
                lastWallTime = Time.time;
                lastWallSide = wall;
            }
            float target = input.moveX * runSpeed * SpeedMultiplier;
            // Kicking off a wall pushes away for a moment whatever the stick says.
            if (Time.time < wallJumpLockUntil)
                target = wallJumpDir * runSpeed * SpeedMultiplier;
            float rate;
            if (Grounded)
                rate = Mathf.Abs(target) > 0.01f ? groundAcceleration : groundDeceleration;
            else
                rate = Mathf.Abs(target) > 0.01f ? airAcceleration : airDeceleration;
            // Turning around is instant on the ground.
            if (Grounded && target != 0f && Mathf.Sign(target) != Mathf.Sign(v.x))
                v.x = 0f;
            v.x = Mathf.MoveTowards(v.x, target, rate * dt);

            // Jump (buffered + coyote).
            bool buffered = Time.time - lastJumpPressedTime <= jumpBufferTime;
            bool coyote = Time.time - lastGroundedTime <= coyoteTime;
            if (buffered && input.down && Grounded && groundCollider != null && groundCollider.gameObject.layer == DCLayers.OneWay)
            {
                DropThrough(groundCollider);
                lastJumpPressedTime = -10f;
            }
            else if (buffered && (Grounded || coyote) && !isJumping)
            {
                v.y = jumpVelocity;
                isJumping = true;
                jumpStartTime = Time.time;
                jumpCutApplied = false;
                lastJumpPressedTime = -10f;
                lastGroundedTime = -10f;
                Grounded = false;
                squash.Punch(new Vector2(0.78f, 1.28f));
                JuiceEngine.Instance?.Dust(FeetPosition, Vector2.up, 4);
                anim.Restart("Jump_Rise", 0.02f);
                Audio.Sfx.Play("player.jump", FeetPosition);
            }
            else if (buffered && !Grounded && Runes.Has(Runes.Spider) && Time.time - lastWallTime <= 0.12f)
            {
                // Wall jump: up and away from the wall; the double jump comes back.
                v.y = jumpVelocity * 0.92f;
                jumpStartTime = Time.time;
                v.x = -lastWallSide * runSpeed * 1.1f;
                wallJumpDir = -lastWallSide;
                wallJumpLockUntil = Time.time + wallJumpLock;
                lastWallTime = -10f;
                airJumpsLeft = airJumps;
                isJumping = true;
                jumpCutApplied = false;
                lastJumpPressedTime = -10f;
                WallJumps++;
                anim.SetFacing(wallJumpDir);
                squash.Punch(new Vector2(0.8f, 1.25f));
                JuiceEngine.Instance?.Dust(transform.position + new Vector3(lastWallSide * 0.4f, 0.8f, 0f), new Vector2(wallJumpDir, 0.3f), 5);
                JuiceEngine.Instance?.Embers(transform.position + Vector3.up * 0.8f, 6, Runes.ColorOf(Runes.Spider));
                anim.Restart("Jump_Rise", 0.02f);
                Audio.Sfx.Play("player.jump", FeetPosition);
            }
            else if (buffered && !Grounded && airJumpsLeft > 0 && !input.down)
            {
                // Double jump: a fresh, slightly lower jump with a forward flip.
                airJumpsLeft--;
                v.y = doubleJumpVelocity;
                isJumping = true;
                jumpStartTime = Time.time;
                jumpCutApplied = false;
                lastJumpPressedTime = -10f;
                squash.Punch(new Vector2(0.85f, 1.2f));
                squash.Spin(-360f, 0.32f); // inside the mirrored facing pivot: always a forward flip
                JuiceEngine.Instance?.Embers(FeetPosition + Vector3.up * 0.2f, 10, new Color(1.6f, 2.6f, 3.2f));
                JuiceEngine.Instance?.Ring(FeetPosition + Vector3.up * 0.2f, new Color(1f, 1.8f, 2.4f) * 0.7f, 1.6f);
                JuiceEngine.Instance?.Dust(FeetPosition, Vector2.down, 3);
                anim.Restart("Jump_Rise", 0.02f);
                Audio.Sfx.Play("player.double_jump", FeetPosition);
            }

            // Variable height: releasing early cuts the ascent.
            if (isJumping && !input.jumpHeld && v.y > 0f && !jumpCutApplied && Time.time - jumpStartTime >= minJumpTime)
            {
                v.y *= jumpCutMultiplier;
                jumpCutApplied = true;
            }
            v.y = ApplyGravity(v.y, dt, 1f);
            // Wall slide: holding into a wall while falling (Spider rune).
            if (wall != 0 && v.y < -wallSlideSpeed && input.moveX == wall)
            {
                v.y = -wallSlideSpeed;
                if (Random.value < dt * 12f)
                    JuiceEngine.Instance?.Dust(transform.position + new Vector3(wall * 0.4f, 1.2f, 0f), Vector2.up, 1);
            }
            return v;
        }

        /// <summary>Assist mode: once per area a killing blow leaves half health instead.</summary>
        bool AssistRevive()
        {
            var settings = SaveSystem.Data.settings;
            var run = SaveSystem.Data.run;
            if (!settings.assist || !settings.assistRevive || run.assistReviveUsed)
                return false;
            run.assistReviveUsed = true;
            health.SetCurrent(health.maxHealth * 0.5f);
            health.InvulnerableUntil = Time.time + 2f;
            JuiceEngine.Instance?.Embers(transform.position + Vector3.up, 40, new Color(0.8f, 2.6f, 3.2f));
            UI.GameHUD.Instance?.Toast(Loc.Get("hud.assist_revive"), new Color(0.6f, 0.9f, 1f));
            return true;
        }

        /// <summary>Solid wall touching the body's side: +1 right, -1 left, 0 none.</summary>
        int WallContact()
        {
            var b = capsule.bounds;
            for (int side = 1; side >= -1; side -= 2)
            {
                var c = new Vector2(side > 0 ? b.max.x + 0.06f : b.min.x - 0.06f, b.center.y + 0.1f);
                var col = Physics2D.OverlapBox(c, new Vector2(0.1f, b.size.y * 0.5f), 0f, DCLayers.SolidMask);
                if (col != null && col.GetComponentInParent<DeadCells.Run.Breakable>() == null)
                    return side;
            }
            return 0;
        }

        float ApplyGravity(float vy, float dt, float scale)
        {
            float g = gravity * scale;
            if (vy < 0f)
                g *= fallGravityMultiplier;
            else if (Mathf.Abs(vy) < apexHangThreshold && Input.jumpHeld && isJumping)
                g *= apexGravityMultiplier;
            vy -= g * dt;
            return Mathf.Max(vy, -maxFallSpeed);
        }

        void CheckGround()
        {
            Bounds b = capsule.bounds;
            Vector2 origin = new Vector2(b.center.x, b.min.y + 0.12f);
            Vector2 size = new Vector2(b.size.x * 0.82f, 0.1f);
            Grounded = false;
            groundCollider = null;
            if (body.linearVelocity.y > 0.5f && State != PlayerState.PoundFall)
                return;
            var hits = Physics2D.BoxCastAll(origin, size, 0f, Vector2.down, 0.14f, DCLayers.GroundMask);
            foreach (var hit in hits)
            {
                if (hit.collider == droppingThrough || hit.normal.y < 0.55f)
                    continue;
                // One-way platforms only count from above.
                if (hit.collider.gameObject.layer == DCLayers.OneWay && hit.point.y > b.min.y + 0.08f)
                    continue;
                Grounded = true;
                groundCollider = hit.collider;
                isJumping = false;
                return;
            }
        }

        static int HazardMask => 1 << DCLayers.Fx | 1 << DCLayers.Pickup;

        /// <summary>Dead Cells-style automatic ledge climb when jumping into a wall top.</summary>
        bool TryMantle(InputFrame input)
        {
            if (Grounded || input.moveX == 0f || body.linearVelocity.y > 7f)
                return false;
            int dir = (int)input.moveX;
            Bounds b = capsule.bounds;
            Vector2 chest = new Vector2(b.center.x, b.min.y + 0.9f);
            if (Physics2D.Raycast(chest, Vector2.right * dir, b.extents.x + 0.3f, DCLayers.SolidMask).collider == null)
                return false;
            Vector2 probe = new Vector2(b.center.x + dir * (b.extents.x + 0.4f), b.min.y + mantleMaxHeight + 0.15f);
            if (Physics2D.OverlapPoint(probe, DCLayers.SolidMask) != null)
                return false;
            var hit = Physics2D.Raycast(probe, Vector2.down, mantleMaxHeight - 0.35f, DCLayers.SolidMask);
            if (hit.collider == null || hit.normal.y < 0.7f)
                return false;
            float rise = hit.point.y - b.min.y;
            if (rise < 0.45f || rise > mantleMaxHeight)
                return false;
            Vector2 standAt = new Vector2(probe.x + dir * 0.15f, hit.point.y + 0.02f);
            if (Physics2D.OverlapBox(standAt + new Vector2(0f, 0.95f), new Vector2(0.5f, 1.6f), 0f, DCLayers.SolidMask) != null)
                return false;
            mantleFrom = transform.position;
            mantleTo = standAt;
            anim.SetFacing(dir);
            EnterState(PlayerState.Mantle);
            Audio.Sfx.Play("player.mantle", transform.position);
            return true;
        }

        void DropThrough(Collider2D platform)
        {
            droppingThrough = platform;
            dropThroughUntil = Time.time + 0.35f;
            Physics2D.IgnoreCollision(capsule, platform, true);
            Grounded = false;
        }

        void OnLanded(float impactVy)
        {
            float strength = Mathf.InverseLerp(4f, maxFallSpeed, -impactVy);
            if (State == PlayerState.PoundFall)
                return;
            squash.Punch(new Vector2(1f + 0.32f * strength + 0.08f, 1f - 0.3f * strength - 0.06f));
            Audio.Sfx.Play("player.land", FeetPosition, 0.35f + 0.65f * strength);
            if (strength > 0.15f)
                JuiceEngine.Instance?.Dust(FeetPosition, Vector2.up, Mathf.RoundToInt(3 + 8 * strength));
        }

        // ------------------------------------------------------------- actions

        bool TryDodge(InputFrame input)
        {
            if (Time.time - lastDodgePressedTime > 0.12f || Time.time < dodgeReadyTime)
                return false;
            if (!Grounded && !airDashAvailable)
                return false;
            lastDodgePressedTime = -10f;
            if (input.moveX != 0f)
                anim.SetFacing((int)input.moveX);
            dodgeDirection = Facing;
            if (!Grounded)
                airDashAvailable = false;
            combat.CancelAttack();
            LastDodgeTime = Time.time;
            EnterState(PlayerState.Dodge);
            Audio.Sfx.Play("player.roll", FeetPosition);
            return true;
        }

        bool TryGroundPound(InputFrame input)
        {
            if (Grounded || !input.down || Time.time - lastJumpPressedTime > jumpBufferTime)
                return false;
            var hit = Physics2D.Raycast(FeetPosition + Vector3.up * 0.1f, Vector2.down, poundMinHeight, DCLayers.GroundMask);
            if (hit.collider != null)
                return false;
            lastJumpPressedTime = -10f;
            combat.CancelAttack();
            EnterState(PlayerState.PoundHang);
            Audio.Sfx.Play("player.pound_start", transform.position);
            return true;
        }

        void UpdateDodge()
        {
            float t = StateTime;
            bool invulnerable = t >= dodgeInvulnerableWindow.x && t <= dodgeInvulnerableWindow.y;
            if (invulnerable)
                health.InvulnerableUntil = Mathf.Max(health.InvulnerableUntil, Time.time + 0.02f);
            if (t >= dodgeDuration)
            {
                // Stay ghosted while still overlapping an enemy so we never pop inside one,
                // but only briefly: an enemy that stays on top of us must not trap the roll.
                bool overlapping = Physics2D.OverlapCapsule(capsule.bounds.center, capsule.size * 0.9f, capsule.direction, 0f, DCLayers.EnemyMask) != null;
                if (!overlapping || t >= dodgeDuration + 0.35f)
                {
                    gameObject.layer = DCLayers.Player;
                    dodgeReadyTime = Time.time + dodgeCooldown;
                    EnterState(PlayerState.Locomotion);
                }
            }
        }

        // -------------------------------------------------------------- states

        public void EnterState(PlayerState next)
        {
            var prev = State;
            State = next;
            StateTime = 0f;
            if (prev == PlayerState.Dodge && next != PlayerState.Dodge)
                gameObject.layer = DCLayers.Player;
            if (anim != null)
                anim.SetSpeed(1f);

            switch (next)
            {
                case PlayerState.Dodge:
                    gameObject.layer = DCLayers.PlayerDodge;
                    anim.Restart("Dodge_Roll", 0f);
                    squash.Punch(new Vector2(1.25f, 0.8f));
                    JuiceEngine.Instance?.Dust(FeetPosition, new Vector2(-dodgeDirection, 0.3f), 6);
                    break;
                case PlayerState.PoundHang:
                    anim.Restart("Ground_Pound_Slam", 0f);
                    squash.Punch(new Vector2(0.85f, 1.18f));
                    health.InvulnerableUntil = Time.time + 2f;
                    poundImpactDone = false;
                    break;
                case PlayerState.PoundFall:
                    anim.SeekFrame("Ground_Pound_Slam", 7f);
                    anim.SetSpeed(0f);
                    squash.Punch(new Vector2(0.72f, 1.35f));
                    break;
                case PlayerState.PoundLand:
                    PoundImpact();
                    Audio.Sfx.Play("player.pound_land", FeetPosition);
                    break;
                case PlayerState.Block:
                    combat.BeginBlock(blockSlot);
                    break;
                case PlayerState.Mantle:
                    anim.Restart("Jump_Rise", 0f);
                    squash.Punch(new Vector2(0.85f, 1.15f));
                    isJumping = false;
                    break;
                case PlayerState.WakeUp:
                    anim.Restart("Wake_Up", 0f);
                    break;
                case PlayerState.Frozen:
                    combat.CancelAttack();
                    combat.EndBlock();
                    anim.Play("Idle", 0.1f);
                    break;
                case PlayerState.Locomotion:
                    if (prev == PlayerState.PoundLand)
                        health.InvulnerableUntil = Time.time + 0.1f;
                    break;
            }
        }

        void PoundImpact()
        {
            if (poundImpactDone)
                return;
            poundImpactDone = true;
            anim.SeekFrame("Ground_Pound_Slam", 8f);
            anim.SetSpeed(1f);
            squash.Punch(new Vector2(1.38f, 0.66f));
            var juice = JuiceEngine.Instance;
            if (juice != null)
            {
                juice.SlamWave(FeetPosition, poundRadius);
                juice.Ring(FeetPosition + Vector3.up * 0.3f, new Color(1.6f, 1.4f, 1.1f), poundRadius * 2.2f);
                juice.Debris(FeetPosition, Vector2.up, 10, new Color(0.35f, 0.36f, 0.4f));
                juice.Shake(Vector2.down, 0.9f);
                juice.HitStop(0.07f);
            }
            DeadCells.Run.Breakable.HitArea(FeetPosition + Vector3.down * 0.5f, new Vector2(1.4f, 0.8f), true);
            var hits = Physics2D.OverlapCircleAll(FeetPosition + Vector3.up * 0.5f, poundRadius, DCLayers.EnemyMask);
            foreach (var h in hits)
            {
                var target = h.GetComponentInParent<Health>();
                if (target == null || target.IsDead)
                    continue;
                Vector2 dir = ((Vector2)(target.transform.position - transform.position)).normalized;
                dir.y = Mathf.Max(dir.y, 0.45f);
                var info = new DamageInfo
                {
                    amount = poundDamage * combat.DamageMultiplier * (Cheats.OneHitKills ? 9999f : 1f),
                    weaponId = "slam",
                    effect = -1,
                    knockback = dir.normalized * 9f,
                    hitPoint = target.transform.position + Vector3.up,
                    source = gameObject,
                    critical = false,
                    stun = poundStun,
                    sparkColor = new Color(1.6f, 1.3f, 0.7f),
                };
                var result = target.TakeDamage(info);
                if (result != DamageResult.Ignored)
                    combat.ReportHit(target, info, result);
            }
            health.InvulnerableUntil = Time.time + poundRecovery + 0.1f;
        }

        void OnDamaged(DamageInfo info, DamageResult result)
        {
            if (result == DamageResult.Parried || result == DamageResult.Blocked || State == PlayerState.Dead)
                return;
            combat.CancelAttack();
            combat.EndBlock();
            hurtKnockback = info.knockback;
            body.linearVelocity = new Vector2(info.knockback.x, Mathf.Max(body.linearVelocity.y, info.knockback.y * 0.5f));
            health.InvulnerableUntil = Time.time + hurtInvulnerability;
            hitFlash?.Flash(new Color(2.4f, 0.35f, 0.3f));
            squash.Punch(new Vector2(0.82f, 1.15f));
            Recoverable = Mathf.Min(health.maxHealth - health.Current, Recoverable + info.amount * RecoverRatio);
            Mutations.OnHurt();
            RunManager.Instance?.OnPlayerHurt();
            recoverDrainAt = Time.time + 1.4f;
            Audio.Sfx.Play("player.hurt", transform.position + Vector3.up);
            var juice = JuiceEngine.Instance;
            if (juice != null)
            {
                // No hit-stop when hurt: freezing the whole frame reads as a dropped frame.
                juice.Shake(info.knockback, 0.55f);
                juice.HitSparks(transform.position + Vector3.up * 1.1f, info.knockback, new Color(2.2f, 0.4f, 0.4f), 0.6f);
                juice.ImpactStreaks(transform.position + Vector3.up * 1.1f, new Color(2.6f, 0.4f, 0.35f), 7);
                juice.DamagePopup(transform.position + Vector3.up * 2.1f, info.amount, false, new Color(1f, 0.35f, 0.3f));
            }
            if (result != DamageResult.Killed)
            {
                anim.Restart("Hurt", 0f);
                EnterState(PlayerState.Hurt);
            }
        }

        void OnDied(DamageInfo info)
        {
            combat.CancelAttack();
            combat.EndBlock();
            EnterState(PlayerState.Dead);
            Recoverable = 0f;
            anim.Restart("Death", 0f);
            Audio.Sfx.Play("player.death");
            Died?.Invoke();
        }

        /// <summary>Max health from meta upgrades (Collector) and this run's vitality scrolls.</summary>
        /// <summary>Movement multiplier from the amulet (and mutations).</summary>
        public float SpeedMultiplier { get; set; } = 1f;

        public void RecalculateStats(bool refill)
        {
            var d = SaveSystem.Data;
            var r = d.run;
            // Every scroll adds health; Survival adds the most (Dead Cells' colour stats).
            float max = baseMaxHealth * (1f + 0.1f * d.meta.vitalityLevel) * (1f + 0.08f * (r.brutality + r.tactics) + 0.25f * r.survival)
                        * (1f + 0.15f * ItemForge.AmuletCount(Affix.MaxHealth)) * Mutations.HealthMultiplier;
            SpeedMultiplier = (1f + 0.1f * ItemForge.AmuletCount(Affix.MoveSpeed)) * Mutations.SpeedMultiplier;
            float ratio = health.maxHealth > 0f ? health.Current / health.maxHealth : 1f;
            health.maxHealth = Mathf.Round(max);
            if (refill)
                health.ResetHealth();
            else
                health.SetCurrent(health.maxHealth * ratio);
        }

        public void Freeze(bool frozen)
        {
            if (frozen)
            {
                if (State != PlayerState.Dead)
                    EnterState(PlayerState.Frozen);
            }
            else if (State == PlayerState.Frozen)
            {
                EnterState(PlayerState.Locomotion);
            }
        }

        public void Teleport(Vector3 position)
        {
            transform.position = position;
            body.position = position;
            body.linearVelocity = Vector2.zero;
            lastSafePosition = position;
            secondaryMotion?.ResetPose();
        }

        public void PlayWakeUp() => EnterState(PlayerState.WakeUp);

        public void Respawn(Vector3 position)
        {
            Teleport(position);
            health.ResetHealth();
            health.InvulnerableUntil = Time.time + 1.5f;
            gameObject.layer = DCLayers.Player;
            secondaryMotion?.ResetPose();
            EnterState(PlayerState.Locomotion);
            anim.Restart("Idle", 0f);
        }

        void UpdateFlameLean()
        {
            if (flameRenderer == null)
                return;
            Vector2 v = body.linearVelocity;
            // Flames trail opposite to motion and stretch upward when falling.
            Vector3 lean = new Vector3(Mathf.Clamp(-v.x * 0.016f, -0.16f, 0.16f), Mathf.Clamp(-v.y * 0.006f, -0.06f, 0.14f), 0f);
            flameRenderer.GetPropertyBlock(flameBlock);
            flameBlock.SetVector(LeanId, lean);
            flameRenderer.SetPropertyBlock(flameBlock);
        }

        void OnDestroy()
        {
            if (Main == this)
                Main = null;
        }

        void OnDrawGizmosSelected()
        {
            Gizmos.color = new Color(1f, 0.6f, 0.2f, 0.5f);
            Gizmos.DrawWireSphere(transform.position + Vector3.up * 0.5f, poundRadius);
        }
    }
}
