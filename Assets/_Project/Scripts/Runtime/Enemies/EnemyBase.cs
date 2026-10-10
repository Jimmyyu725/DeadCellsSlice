using System;
using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Player;
using UnityEngine;
using Random = UnityEngine.Random;

namespace DeadCells.Enemies
{
    /// <summary>
    /// Shared enemy plumbing: difficulty/depth scaling, elites, sensing,
    /// telegraphs, hitboxes, projectiles, hurt/stun/freeze reactions, death
    /// burst and the Killed event (drops and stats live in RunManager).
    /// Subclasses implement Think (decisions, animation) and Move (velocity).
    /// </summary>
    [RequireComponent(typeof(Rigidbody2D), typeof(Health))]
    public abstract class EnemyBase : MonoBehaviour, IStunnable, ICombatTarget
    {
        [Header("Identity")]
        public string nameKey = "enemy.zombie";
        public bool isBoss;
        public bool flying;

        [Header("Stats (scaled by depth and difficulty)")]
        public float baseHealth = 70f;
        public float baseDamage = 14f;
        public int cellReward = 3;
        public float aggroRange = 10f;
        public float verticalAggro = 3.5f;
        public float hurtTime = 0.24f;
        public bool superArmor;
        [Tooltip("Flinches allowed in a row before the enemy shrugs hits off for a moment.")]
        public int poise = 3;
        public float corpseTime = 0.65f;
        public Color ichorColor = new Color(0.3f, 0.6f, 0.15f);
        public Color burstColor = new Color(1.2f, 2.2f, 0.6f);

        [Header("References")]
        public CharacterAnimator anim;
        public HitFlash hitFlash;
        public SquashStretch squash;
        public Renderer[] tintRenderers = new Renderer[0];

        protected Rigidbody2D body;
        protected Health health;
        protected StatusEffects status;
        protected Transform player;
        protected Health playerHealth;
        protected float damageMult = 1f;
        protected float windupScale = 1f;
        protected Vector2 knock;
        protected float stunnedUntil;
        protected float hurtUntil;
        protected float gravityScale;
        int flinches;
        float lastFlinch = -10f;
        float poiseBrokenUntil;

        public bool IsDead { get; private set; }
        public bool IsElite { get; private set; }
        public bool IsBoss => isBoss;
        public bool Engaged { get; private set; }
        public Health Health => health;
        public int FacingDir => anim != null ? anim.Facing : 1;
        public bool IsDisabled => Time.time < stunnedUntil || (status != null && status.Disabled);
        public string DisplayName => IsElite ? Loc.Get("enemy.elite", Loc.Get(nameKey)) : Loc.Get(nameKey);

        public static event Action<EnemyBase, DamageInfo> Killed;

        static readonly int OutlineColorId = Shader.PropertyToID("_OutlineColor");
        static readonly int RimColorId = Shader.PropertyToID("_RimColor");

        protected virtual void Awake()
        {
            body = GetComponent<Rigidbody2D>();
            health = GetComponent<Health>();
            status = GetComponent<StatusEffects>();
            body.freezeRotation = true;
            body.interpolation = RigidbodyInterpolation2D.Interpolate;
            gravityScale = flying ? 0f : body.gravityScale;
            if (flying)
                body.gravityScale = 0f;
            health.Damaged += OnDamaged;
            health.Died += OnDied;
            if (anim == null)
                anim = GetComponent<CharacterAnimator>();
        }

        protected virtual void Start()
        {
            var p = PlayerController.Main;
            if (p != null)
            {
                player = p.transform;
                playerHealth = p.Health;
            }
            if (anim != null)
            {
                anim.SetFacing(Random.value > 0.5f ? 1 : -1);
                anim.Restart("Idle", 0f, Random.value);
            }
            if (!isBoss)
                Engaged = true;
        }

        /// <summary>Scale for biome depth, difficulty and elite status (called on spawn).</summary>
        public virtual void Configure(int depth, bool elite)
        {
            if (health == null)
                Awake();
            IsElite = elite && !isBoss;
            float hp = baseHealth * Difficulty.EnemyHealth * (1f + 0.45f * depth) * (IsElite ? 3.2f : 1f);
            if (isBoss)
                hp = baseHealth * Difficulty.EnemyHealth;
            health.maxHealth = Mathf.Round(hp);
            health.ResetHealth();
            damageMult = Difficulty.EnemyDamage * (1f + 0.22f * depth) * (IsElite ? 1.3f : 1f);
            if (isBoss)
                damageMult = Difficulty.EnemyDamage;
            windupScale = Difficulty.EnemyWindupScale;
            if (IsElite)
            {
                transform.localScale = Vector3.one * 1.22f;
                var block = new MaterialPropertyBlock();
                foreach (var r in tintRenderers)
                {
                    if (r == null)
                        continue;
                    r.GetPropertyBlock(block);
                    block.SetColor(OutlineColorId, new Color(2.6f, 0.9f, 0.2f));
                    block.SetColor(RimColorId, new Color(2f, 0.9f, 0.3f));
                    r.SetPropertyBlock(block);
                }
                var glow = new GameObject("EliteGlow").AddComponent<Light>();
                glow.transform.SetParent(transform, false);
                glow.transform.localPosition = new Vector3(0f, 1.2f, -0.8f);
                glow.type = LightType.Point;
                glow.color = new Color(1f, 0.55f, 0.2f);
                glow.intensity = 2.5f;
                glow.range = 3.5f;
                glow.shadows = LightShadows.None;
            }
        }

        public void Engage()
        {
            Engaged = true;
            OnEngage();
        }

        protected virtual void OnEngage() { }

        protected float Damage(float baseValue) => baseValue * damageMult;

        // --------------------------------------------------------------- loop

        /// <summary>This enemy's own time multiplier (slow effects).</summary>
        protected float TimeFactor => status != null ? status.TimeFactor : 1f;

        protected virtual void Update()
        {
            float dt = Time.deltaTime * TimeFactor;
            if (dt <= 0f || IsDead || anim == null)
                return;
            anim.TimeScale = TimeFactor;
            if (status != null && status.Frozen)
            {
                anim.SetSpeed(0f);
                return;
            }
            if (Time.time < stunnedUntil || (status != null && status.Shocked) || Time.time < hurtUntil)
                return;
            if (anim.Speed == 0f)
                anim.SetSpeed(1f);
            if (!Engaged)
            {
                anim.Play("Idle", 0.1f);
                return;
            }
            Think(dt);
        }

        protected virtual void FixedUpdate()
        {
            float dt = Time.fixedDeltaTime;
            Vector2 v = body.linearVelocity;
            if (IsDead)
            {
                body.linearVelocity = new Vector2(Mathf.MoveTowards(v.x, 0f, 30f * dt), flying ? Mathf.MoveTowards(v.y, -6f, 20f * dt) : v.y);
                return;
            }
            if ((status != null && status.Disabled) || Time.time < stunnedUntil || Time.time < hurtUntil || !Engaged)
            {
                knock = Vector2.MoveTowards(knock, Vector2.zero, 30f * dt);
                body.linearVelocity = new Vector2(knock.x, flying ? knock.y : v.y);
                return;
            }
            Move(dt * TimeFactor);
            if (TimeFactor < 1f)
            {
                var sv = body.linearVelocity;
                body.linearVelocity = new Vector2(sv.x * TimeFactor, flying || sv.y > 0f ? sv.y * TimeFactor : sv.y);
            }
        }

        protected abstract void Think(float dt);
        protected abstract void Move(float dt);

        // ------------------------------------------------------------- sensing

        protected bool PlayerAlive => player != null && playerHealth != null && !playerHealth.IsDead;

        protected bool CanSeePlayer(float rangeScale = 1f)
        {
            if (!PlayerAlive)
                return false;
            Vector2 d = player.position - transform.position;
            if (Mathf.Abs(d.x) > aggroRange * rangeScale || Mathf.Abs(d.y) > verticalAggro * rangeScale)
                return false;
            Vector2 eye = (Vector2)transform.position + Vector2.up * 1.2f;
            Vector2 target = (Vector2)player.position + Vector2.up * 1.0f;
            return Physics2D.Linecast(eye, target, DCLayers.SolidMask).collider == null;
        }

        protected int DirToPlayer => player != null && player.position.x > transform.position.x ? 1 : -1;
        protected float DistX => player != null ? Mathf.Abs(player.position.x - transform.position.x) : 999f;
        protected float DistY => player != null ? player.position.y - transform.position.y : 0f;

        protected bool GroundAhead(int dir, float ahead = 0.55f)
        {
            Vector2 origin = (Vector2)transform.position + new Vector2(dir * ahead * transform.localScale.x, 0.3f);
            return Physics2D.Raycast(origin, Vector2.down, 1.1f, DCLayers.GroundMask).collider != null;
        }

        protected bool WallAhead(int dir, float dist = 0.6f)
        {
            Vector2 origin = (Vector2)transform.position + new Vector2(0f, 0.8f);
            return Physics2D.Raycast(origin, new Vector2(dir, 0f), dist * transform.localScale.x, DCLayers.SolidMask).collider != null;
        }

        protected bool Grounded => Physics2D.Raycast((Vector2)transform.position + Vector2.up * 0.1f, Vector2.down, 0.2f, DCLayers.GroundMask).collider != null;

        // -------------------------------------------------------------- attacks

        protected void Telegraph(bool big = true)
        {
            hitFlash?.Flash(new Color(2.6f, 0.5f, 0.2f), 0.6f);
            squash?.Punch(new Vector2(0.9f, 1.12f));
            JuiceEngine.Instance?.Popup(transform.position + Vector3.up * (2.4f * transform.localScale.y), "!", new Color(1f, 0.25f, 0.2f), big);
            Audio.Sfx.Play("enemy.alert", transform.position + Vector3.up * 2f, big ? 1f : 0.75f);
        }

        protected bool StrikeBox(Vector2 offset, Vector2 size, float damage, Vector2 knockback, float stun = 0.25f)
        {
            int f = FacingDir;
            Vector2 s = transform.localScale;
            Vector2 center = (Vector2)transform.position + new Vector2(offset.x * f * s.x, offset.y * s.y);
            var col = Physics2D.OverlapBox(center, size * s, 0f, 1 << DCLayers.Player);
            if (col == null)
                return false;
            var target = col.GetComponentInParent<Health>();
            if (target == null)
                return false;
            target.TakeDamage(new DamageInfo
            {
                amount = Damage(damage),
                knockback = new Vector2(knockback.x * f, knockback.y),
                hitPoint = col.bounds.center,
                source = gameObject,
                stun = stun,
                effect = -1,
            });
            return true;
        }

        protected Projectile Fire(GameObject prefab, Vector3 from, Vector2 velocity, float gravity, float damage, bool reflectable = true)
        {
            if (prefab == null)
                return null;
            var go = Instantiate(prefab, from, Quaternion.identity);
            go.SetActive(true);
            var p = go.GetComponent<Projectile>() ?? go.AddComponent<Projectile>();
            p.velocity = velocity;
            p.gravity = gravity;
            p.damage = Damage(damage);
            p.fromPlayer = false;
            p.owner = gameObject;
            p.reflectable = reflectable;
            return p;
        }

        protected Vector2 AimAtPlayer(Vector3 from, float speed)
        {
            if (player == null)
                return new Vector2(FacingDir * speed, 0f);
            Vector2 to = (Vector2)(player.position + Vector3.up * 1.0f) - (Vector2)from;
            return to.normalized * speed;
        }

        /// <summary>Velocity for a ballistic arc landing on the player after `time` seconds.</summary>
        protected Vector2 LobAtPlayer(Vector3 from, float gravity, float time)
        {
            Vector2 target = player != null ? (Vector2)player.position + Vector2.up * 0.5f : (Vector2)from + new Vector2(FacingDir * 6f, 0f);
            Vector2 d = target - (Vector2)from;
            return new Vector2(d.x / time, d.y / time + 0.5f * gravity * time);
        }

        // ----------------------------------------------------------- reactions

        protected virtual void OnDamaged(DamageInfo info, DamageResult result)
        {
            if (result == DamageResult.Killed || IsDead)
                return;
            hitFlash?.Flash(new Color(2.4f, 2.4f, 2.4f));
            squash?.Punch(new Vector2(1.18f, 0.86f));
            if (!Engaged && isBoss)
                return;
            if (superArmor || isBoss || InSuperArmor() || Time.time < poiseBrokenUntil)
                return;
            // Poise: after a few flinches in a row the enemy ignores hit-stun briefly.
            flinches = Time.time - lastFlinch < 1.2f ? flinches + 1 : 1;
            lastFlinch = Time.time;
            if (flinches > poise)
            {
                flinches = 0;
                poiseBrokenUntil = Time.time + 1.4f;
                hitFlash?.Flash(new Color(2.6f, 1.6f, 0.4f), 0.7f);
                return;
            }
            knock = info.knockback;
            body.linearVelocity = new Vector2(info.knockback.x, flying ? info.knockback.y * 0.5f : Mathf.Max(body.linearVelocity.y, info.knockback.y * 0.35f));
            hurtUntil = Time.time + hurtTime + info.stun;
            anim.Restart("Hurt", 0f);
            OnInterrupted();
        }

        /// <summary>True while an attack's active frames give armour (strikes cannot be interrupted).</summary>
        protected virtual bool InSuperArmor() => false;

        /// <summary>Called when a hit interrupts the current action.</summary>
        protected virtual void OnInterrupted() { }

        public virtual void Stun(float seconds, Vector2 knockback)
        {
            if (IsDead)
                return;
            if (isBoss)
                seconds *= 0.4f;
            knock = knockback * (isBoss ? 0.2f : 1f);
            body.linearVelocity = knock;
            stunnedUntil = Time.time + seconds;
            anim.Restart("Hurt", 0f);
            anim.SetSpeed(0.25f);
            hitFlash?.Flash(new Color(2.4f, 2.0f, 0.6f), 0.9f);
            JuiceEngine.Instance?.Popup(transform.position + Vector3.up * 2.4f, "STUN", new Color(1f, 0.85f, 0.3f), false);
            OnInterrupted();
        }

        protected virtual void OnDied(DamageInfo info)
        {
            IsDead = true;
            OnInterrupted();
            anim.SetSpeed(1f);
            anim.Restart("Death", 0f);
            body.gravityScale = flying ? 1.5f : gravityScale;
            body.linearVelocity = new Vector2(info.knockback.x * 1.2f, Mathf.Max(3f, info.knockback.y));
            gameObject.layer = DCLayers.Fx;
            foreach (var c in GetComponentsInChildren<Collider2D>())
                if (!c.isTrigger)
                    c.gameObject.layer = DCLayers.Fx;
            Killed?.Invoke(this, info);
            Audio.Sfx.Play(isBoss ? "boss.death" : "enemy.death", transform.position + Vector3.up);
            Invoke(nameof(Burst), isBoss ? 1.6f : corpseTime);
        }

        void Burst()
        {
            var juice = JuiceEngine.Instance;
            Vector3 c = transform.position + Vector3.up * 0.6f * transform.localScale.y;
            if (juice != null)
            {
                juice.CellBurst(c, isBoss ? 30 : 6);
                juice.Ichor(c, Vector2.up, ichorColor, isBoss ? 60 : 22);
                juice.Embers(c, isBoss ? 60 : 18, burstColor);
                juice.Dust(transform.position, Vector2.up, 10, new Color(0.35f, 0.45f, 0.3f, 0.6f));
                juice.Shake(Vector2.up, isBoss ? 0.8f : 0.15f);
            }
            Destroy(gameObject);
        }
    }
}
