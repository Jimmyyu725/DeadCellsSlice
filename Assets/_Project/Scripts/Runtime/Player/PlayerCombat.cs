using System.Collections.Generic;
using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using UnityEngine;

namespace DeadCells.Player
{
    [System.Serializable]
    public class AttackStep
    {
        public string clip = "Slash_Combo_1";
        [Tooltip("Clip length in 60 fps frames.")]
        public int totalFrames = 18;
        [Tooltip("First/last frame the hitbox is live.")]
        public Vector2Int activeFrames = new Vector2Int(4, 7);
        [Tooltip("From this frame the next combo step (or a jump) may cancel the recovery.")]
        public int cancelFrame = 8;
        public Vector2Int lungeFrames = new Vector2Int(3, 6);
        public float lungeSpeed = 4f;
        public float damage = 12f;
        public Vector2 hitboxOffset = new Vector2(1.2f, 1.0f);
        public Vector2 hitboxSize = new Vector2(2.2f, 1.7f);
        public float knockback = 4f;
        public float stun = 0.2f;
        [Range(0f, 1f)] public float hitStopWeight = 0.3f;
        public float shake = 0.18f;
        public bool critical;
    }

    [System.Serializable]
    public class WeaponProfile
    {
        public string displayName = "Rusty Sword";
        public GameObject visual;
        public Transform bladeBase;
        public Transform bladeTip;
        public float animSpeed = 1f;
        [ColorUsage(true, true)] public Color arcColor = new Color(1.2f, 2.6f, 3.2f);
        [ColorUsage(true, true)] public Color arcCore = new Color(6f, 6f, 6f);
        [ColorUsage(true, true)] public Color sparkColor = new Color(2.5f, 2.2f, 1.6f);
        public AttackStep[] combo = new AttackStep[0];
    }

    /// <summary>Melee combos, hit detection and the shield (block + parry).</summary>
    [RequireComponent(typeof(PlayerController))]
    public class PlayerCombat : MonoBehaviour
    {
        public WeaponProfile[] weapons = new WeaponProfile[0];
        public int weaponIndex;
        public SlashArc slashArc;
        public GameObject shieldVisual;

        [Header("Timing")]
        public float attackBufferTime = 0.22f;
        public float comboResetTime = 0.5f;
        public float parryWindow = 0.18f;

        [Header("Victim FX")]
        public Color ichorColor = new Color(0.32f, 0.62f, 0.18f, 1f);

        PlayerController player;
        Health health;
        AttackStep step;
        int comboIndex;
        float attackClock;
        float lastAttackPressed = -10f;
        float lastComboEnd = -10f;
        bool arcStarted;
        bool arcEnded;
        bool blocking;
        float blockStart;
        float shieldScale;
        readonly HashSet<Health> hitThisSwing = new HashSet<Health>();

        public WeaponProfile Weapon => weapons.Length > 0 ? weapons[Mathf.Clamp(weaponIndex, 0, weapons.Length - 1)] : null;
        public bool CanBlock => shieldVisual != null;
        public bool CanCancel => step != null && Frame >= step.cancelFrame;
        public bool Attacking => step != null;
        // Frame numbers match the Blender timeline (frame 1 = clip start).
        float Frame => attackClock * CharacterAnimator.FrameRate + 1f;

        public event System.Action<WeaponProfile> WeaponChanged;

        void Awake()
        {
            player = GetComponent<PlayerController>();
            health = GetComponent<Health>();
        }

        void Start()
        {
            ApplyWeaponVisuals();
            if (shieldVisual != null)
                shieldVisual.SetActive(false);
        }

        public void BufferInput(InputFrame input)
        {
            if (input.attackPressed)
                lastAttackPressed = Time.time;
        }

        // ------------------------------------------------------------- attacks

        public bool TryStartAttack()
        {
            if (Weapon == null || Weapon.combo.Length == 0 || Time.time - lastAttackPressed > attackBufferTime)
                return false;
            lastAttackPressed = -10f;
            if (Time.time - lastComboEnd > comboResetTime)
                comboIndex = 0;
            StartStep(comboIndex);
            return true;
        }

        void StartStep(int index)
        {
            var w = Weapon;
            comboIndex = Mathf.Clamp(index, 0, w.combo.Length - 1);
            step = w.combo[comboIndex];
            attackClock = 0f;
            hitThisSwing.Clear();
            arcStarted = arcEnded = false;
            if (player.Input.moveX != 0f)
                player.anim.SetFacing((int)player.Input.moveX);
            player.anim.Restart(step.clip, 0f);
            player.anim.SetSpeed(w.animSpeed);
            if (!player.Grounded)
            {
                // Air attacks hang briefly so combos read in the air.
                var v = player.Body.linearVelocity;
                player.Body.linearVelocity = new Vector2(v.x * 0.6f, Mathf.Max(v.y, 2.2f));
            }
            player.squash.Add(new Vector2(-0.05f, 0.05f));
        }

        /// <summary>Advances the current swing. Returns true when it has fully ended.</summary>
        public bool UpdateAttack(float dt)
        {
            if (step == null)
                return true;
            var w = Weapon;
            attackClock += dt * w.animSpeed;
            float f = Frame;

            if (f < 2f && player.Input.moveX != 0f)
                player.anim.SetFacing((int)player.Input.moveX);

            if (!arcStarted && f >= step.activeFrames.x - 1)
            {
                arcStarted = true;
                if (slashArc != null)
                    slashArc.Begin(w.arcColor, w.arcCore);
            }
            if (arcStarted && !arcEnded && f > step.activeFrames.y + 1)
            {
                arcEnded = true;
                slashArc?.End();
            }

            if (f >= step.activeFrames.x && f < step.activeFrames.y + 1f)
                DoHits();

            if (f >= step.cancelFrame && Time.time - lastAttackPressed <= attackBufferTime && comboIndex + 1 < w.combo.Length)
            {
                lastAttackPressed = -10f;
                slashArc?.End();
                StartStep(comboIndex + 1);
                return false;
            }

            if (f >= step.totalFrames)
            {
                FinishSwing();
                return true;
            }
            return false;
        }

        void FinishSwing()
        {
            slashArc?.End();
            lastComboEnd = Time.time;
            comboIndex = (comboIndex + 1) % Mathf.Max(1, Weapon.combo.Length);
            step = null;
            player.anim.SetSpeed(1f);
        }

        public void CancelAttack()
        {
            if (step == null)
                return;
            slashArc?.End();
            step = null;
            comboIndex = 0;
            player.anim.SetSpeed(1f);
        }

        public Vector2 AttackVelocity(Vector2 v, float dt, bool grounded)
        {
            if (step == null)
                return v;
            float f = Frame;
            if (f >= step.lungeFrames.x && f <= step.lungeFrames.y)
                v.x = player.Facing * step.lungeSpeed;
            else
                v.x = Mathf.MoveTowards(v.x, 0f, (grounded ? 140f : 25f) * dt);
            return v;
        }

        void DoHits()
        {
            int facing = player.Facing;
            Vector2 origin = transform.position;
            Vector2 center = origin + new Vector2(step.hitboxOffset.x * facing, step.hitboxOffset.y);
            var cols = Physics2D.OverlapBoxAll(center, step.hitboxSize, 0f, DCLayers.EnemyMask);
            foreach (var col in cols)
            {
                var target = col.GetComponentInParent<Health>();
                if (target == null || target.IsDead || hitThisSwing.Contains(target))
                    continue;
                hitThisSwing.Add(target);
                float dmg = step.damage * (step.critical ? 1.5f : 1f) * Random.Range(0.92f, 1.08f);
                Vector2 dir = new Vector2(facing, 0.3f).normalized;
                Vector2 hitPoint = col.ClosestPoint(new Vector2(origin.x, center.y));
                hitPoint = Vector2.Lerp(hitPoint, (Vector2)col.bounds.center, 0.35f);
                var info = new DamageInfo
                {
                    amount = dmg,
                    knockback = dir * step.knockback,
                    hitPoint = hitPoint,
                    source = gameObject,
                    critical = step.critical,
                    stun = step.stun,
                    hitStop = Mathf.Lerp(0.04f, 0.08f, step.hitStopWeight),
                    shake = step.shake,
                    sparkColor = Weapon.sparkColor,
                };
                var result = target.TakeDamage(info);
                if (result != DamageResult.Ignored)
                    ReportHit(target, info, result);
            }
        }

        /// <summary>Shared impact feedback for any player-dealt damage.</summary>
        public void ReportHit(Health target, DamageInfo info, DamageResult result)
        {
            var juice = JuiceEngine.Instance;
            if (juice == null)
                return;
            bool kill = result == DamageResult.Killed;
            if (info.hitStop > 0f)
                juice.HitStop(kill ? info.hitStop + 0.02f : info.hitStop);
            if (info.shake > 0f)
                juice.Shake(info.knockback, kill ? info.shake * 1.4f : info.shake);
            Vector3 p = info.hitPoint;
            float weight = Mathf.Clamp01(info.amount / 30f);
            juice.HitSparks(p, info.knockback, info.sparkColor, weight);
            juice.Ichor(p, info.knockback + Vector2.up, ichorColor, kill ? 18 : 8);
            juice.DamagePopup(target.transform.position + Vector3.up * 2.0f, info.amount, info.critical);
            player.squash.Add(new Vector2(0.06f, -0.05f));
        }

        // -------------------------------------------------------------- weapons

        public void SwapWeapon()
        {
            if (weapons.Length < 2)
                return;
            weaponIndex = (weaponIndex + 1) % weapons.Length;
            ApplyWeaponVisuals();
            comboIndex = 0;
            JuiceEngine.Instance?.Popup(transform.position + Vector3.up * 2.4f, Weapon.displayName.ToUpperInvariant(),
                new Color(0.75f, 0.95f, 1f), false);
            WeaponChanged?.Invoke(Weapon);
        }

        void ApplyWeaponVisuals()
        {
            for (int i = 0; i < weapons.Length; i++)
            {
                if (weapons[i].visual != null)
                    weapons[i].visual.SetActive(i == weaponIndex);
            }
            if (slashArc != null && Weapon != null)
            {
                slashArc.bladeBase = Weapon.bladeBase;
                slashArc.bladeTip = Weapon.bladeTip;
            }
        }

        // --------------------------------------------------------------- shield

        public void BeginBlock()
        {
            blocking = true;
            blockStart = Time.time;
            shieldScale = 0.2f;
            if (shieldVisual != null)
            {
                shieldVisual.SetActive(true);
                shieldVisual.transform.localScale = Vector3.one * shieldScale;
            }
            player.anim.Restart("Shield_Block", 0f);
            health.Interceptor = Intercept;
        }

        public void EndBlock()
        {
            if (!blocking)
                return;
            blocking = false;
            if (shieldVisual != null)
                shieldVisual.SetActive(false);
            if (health.Interceptor == Intercept)
                health.Interceptor = null;
        }

        void Update()
        {
            if (blocking && shieldVisual != null && shieldScale < 1f)
            {
                shieldScale = Mathf.MoveTowards(shieldScale, 1f, Time.deltaTime * 14f);
                float pop = shieldScale < 1f ? shieldScale * 1.15f : 1f;
                shieldVisual.transform.localScale = Vector3.one * pop;
            }
        }

        DamageResult Intercept(DamageInfo info)
        {
            if (!blocking)
                return DamageResult.Hit;
            float sourceX = info.source != null ? info.source.transform.position.x : transform.position.x - info.knockback.x;
            int side = sourceX >= transform.position.x ? 1 : -1;
            if (side != player.Facing)
                return DamageResult.Hit; // shields only cover the front

            var juice = JuiceEngine.Instance;
            Vector3 contact = transform.position + new Vector3(player.Facing * 0.55f, 1.2f, 0f);
            if (Time.time - blockStart <= parryWindow)
            {
                if (info.source != null)
                    info.source.GetComponentInParent<IStunnable>()?.Stun(1.6f, new Vector2(player.Facing * 7f, 2f));
                if (juice != null)
                {
                    juice.HitStop(0.11f);
                    juice.Shake(new Vector2(player.Facing, 0.2f), 0.6f);
                    juice.HitSparks(contact, new Vector2(-player.Facing, 0.4f), new Color(3f, 2.3f, 0.6f), 1f);
                    juice.Popup(transform.position + Vector3.up * 2.4f, "PARRY!", new Color(1f, 0.85f, 0.25f), true);
                }
                player.hitFlash?.Flash(new Color(2.4f, 2.0f, 0.8f), 0.8f);
                return DamageResult.Parried;
            }
            if (juice != null)
            {
                juice.HitStop(0.045f);
                juice.Shake(new Vector2(-player.Facing, 0f), 0.22f);
                juice.HitSparks(contact, new Vector2(-player.Facing, 0.3f), new Color(2f, 2f, 2.2f), 0.4f);
            }
            player.Body.linearVelocity = new Vector2(-player.Facing * 4.5f, player.Body.linearVelocity.y);
            return DamageResult.Blocked;
        }

        void OnDrawGizmosSelected()
        {
            var w = Weapon;
            if (w == null || w.combo.Length == 0)
                return;
            int facing = Application.isPlaying && player != null ? player.Facing : 1;
            foreach (var s in w.combo)
            {
                Gizmos.color = new Color(1f, 0.2f, 0.2f, 0.35f);
                Vector3 c = transform.position + new Vector3(s.hitboxOffset.x * facing, s.hitboxOffset.y, 0f);
                Gizmos.DrawWireCube(c, new Vector3(s.hitboxSize.x, s.hitboxSize.y, 0.1f));
            }
        }
    }
}
