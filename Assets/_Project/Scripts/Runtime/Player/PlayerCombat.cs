using System.Collections.Generic;
using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Meta;
using UnityEngine;

namespace DeadCells.Player
{
    /// <summary>Lets crit rules and the HUD query an enemy without knowing its type.</summary>
    public interface ICombatTarget
    {
        int FacingDir { get; }
        bool IsDisabled { get; }
    }

    /// <summary>
    /// The Beheaded's four equipment slots (two weapons, two skills) and the
    /// health flask. Melee combos with per-item crit rules, bows, thrown
    /// skills with cooldowns, shields (block + parry, also reflects
    /// projectiles), and shared impact feedback.
    /// </summary>
    [RequireComponent(typeof(PlayerController))]
    public class PlayerCombat : MonoBehaviour
    {
        public const int SlotCount = 4;

        [System.Serializable]
        public struct Mount
        {
            public Transform socket;
            public Vector3 localPosition;
            public Quaternion localRotation;
        }

        enum ActionKind { None, Melee, Shoot, Throw, Drink }

        public SlashArc slashArc;
        public Mount weaponMount;
        public Mount offhandMount;
        public Mount shieldMount;
        public Mount bowMount;
        [Tooltip("Shown in the right hand while drinking.")]
        public GameObject flaskVisual;

        [Header("Timing")]
        public float attackBufferTime = 0.22f;
        public float comboResetTime = 0.5f;

        [Header("Flask")]
        public float flaskHealFraction = 0.55f;
        public int flaskHealFrame = 20;

        [Header("Victim FX")]
        public Color ichorColor = new Color(0.32f, 0.62f, 0.18f, 1f);

        public static PlayerCombat Instance { get; private set; }

        readonly ItemDef[] slots = new ItemDef[SlotCount];
        readonly GameObject[] mainVisual = new GameObject[SlotCount];
        readonly GameObject[] offVisual = new GameObject[SlotCount];
        readonly float[] cooldownUntil = new float[SlotCount];
        readonly float[] cooldownLength = new float[SlotCount];
        readonly int[] comboIndex = new int[SlotCount];
        readonly float[] lastComboEnd = { -10f, -10f, -10f, -10f };
        readonly float[] lastPressed = { -10f, -10f, -10f, -10f };
        readonly HashSet<Health> hitThisSwing = new HashSet<Health>();

        PlayerController player;
        Health health;
        ActionKind action;
        int actionSlot;
        AttackStep step;
        float clock;
        bool released;
        bool arcStarted, arcEnded;
        bool blocking;
        int blockSlot = -1;
        float blockStart;
        float shieldScale;
        float flaskPressed = -10f;

        public bool Attacking => action != ActionKind.None;
        public bool Drinking => action == ActionKind.Drink;
        public bool CanCancel => action switch
        {
            ActionKind.Melee => step != null && Frame >= step.cancelFrame,
            ActionKind.Shoot or ActionKind.Throw => released,
            _ => false,
        };
        // Frame numbers match the Blender timeline (frame 1 = clip start).
        float Frame => clock * CharacterAnimator.FrameRate + 1f;
        static RunState Run => SaveSystem.Data.run;

        public event System.Action SlotsChanged;

        void Awake()
        {
            Instance = this;
            player = GetComponent<PlayerController>();
            health = GetComponent<Health>();
        }

        void OnDestroy()
        {
            if (Instance == this)
                Instance = null;
        }

        // ---------------------------------------------------------------- slots

        public ItemDef Slot(int i) => i >= 0 && i < SlotCount ? slots[i] : null;

        public float CooldownRemaining(int i) => Cheats.NoCooldowns ? 0f : Mathf.Max(0f, cooldownUntil[i] - Time.time);

        public float CooldownFraction(int i) => cooldownLength[i] > 0f ? Mathf.Clamp01(CooldownRemaining(i) / cooldownLength[i]) : 0f;

        public int ShieldSlot
        {
            get
            {
                for (int i = 0; i < 2; i++)
                    if (slots[i] != null && slots[i].kind == ItemKind.Shield)
                        return i;
                return -1;
            }
        }

        /// <summary>Puts `item` in `slot`; returns what was there.</summary>
        public ItemDef Equip(int slot, ItemDef item)
        {
            CancelAttack();
            EndBlock();
            var old = slots[slot];
            Destroy(mainVisual[slot]);
            Destroy(offVisual[slot]);
            mainVisual[slot] = offVisual[slot] = null;
            slots[slot] = item;
            comboIndex[slot] = 0;
            if (item == null || item.kind != ItemKind.Skill)
                cooldownUntil[slot] = 0f; // a fresh weapon is ready at once (skills keep theirs: no swap exploit)
            if (item != null)
            {
                mainVisual[slot] = Spawn(item.visual, item.mount);
                if (item.dualWield)
                    offVisual[slot] = Spawn(item.offhandVisual != null ? item.offhandVisual : item.visual, MountPoint.Offhand);
            }
            RefreshVisuals();
            WriteRun();
            SlotsChanged?.Invoke();
            return old;
        }

        GameObject Spawn(GameObject prefab, MountPoint mountPoint)
        {
            if (prefab == null)
                return null;
            var m = mountPoint switch
            {
                MountPoint.Offhand => offhandMount,
                MountPoint.Shield => shieldMount,
                MountPoint.Bow => bowMount,
                _ => weaponMount,
            };
            if (m.socket == null)
                return null;
            var go = Instantiate(prefab, m.socket);
            go.transform.localPosition = m.localPosition;
            go.transform.localRotation = m.localRotation;
            go.transform.localScale = Vector3.one;
            foreach (var r in go.GetComponentsInChildren<Renderer>())
                r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            go.SetActive(false);
            return go;
        }

        /// <summary>Which visuals show depends on the current action (Dead Cells swaps weapons on use).</summary>
        void RefreshVisuals()
        {
            int shown = -1;
            if (action == ActionKind.Melee || action == ActionKind.Throw)
                shown = actionSlot;
            else
            {
                // At rest show the first melee weapon.
                for (int i = 0; i < 2; i++)
                    if (slots[i] != null && slots[i].kind == ItemKind.Melee)
                    {
                        shown = i;
                        break;
                    }
            }
            for (int i = 0; i < SlotCount; i++)
            {
                var item = slots[i];
                bool on = false;
                bool offOn = false;
                if (item != null)
                {
                    switch (item.kind)
                    {
                        case ItemKind.Melee:
                            on = i == shown;
                            offOn = on && item.dualWield;
                            break;
                        case ItemKind.Shield:
                            on = blocking && blockSlot == i;
                            break;
                        case ItemKind.Bow:
                            on = action == ActionKind.Shoot && actionSlot == i;
                            break;
                        case ItemKind.Skill:
                            on = action == ActionKind.Throw && actionSlot == i && !released;
                            break;
                    }
                }
                if (mainVisual[i] != null) mainVisual[i].SetActive(on);
                if (offVisual[i] != null) offVisual[i].SetActive(offOn);
            }
            if (flaskVisual != null)
                flaskVisual.SetActive(action == ActionKind.Drink);
            if (slashArc != null && shown >= 0 && mainVisual[shown] != null)
            {
                slashArc.bladeBase = mainVisual[shown].transform.Find("BladeBase");
                slashArc.bladeTip = mainVisual[shown].transform.Find("BladeTip");
            }
        }

        public void LoadFromRun()
        {
            var db = ItemDatabase.Instance;
            if (db == null)
                return;
            string[] ids = { Run.primary, Run.secondary, Run.skill1, Run.skill2 };
            for (int i = 0; i < SlotCount; i++)
            {
                var item = db.Get(ids[i]);
                if (slots[i] != item)
                {
                    Destroy(mainVisual[i]);
                    Destroy(offVisual[i]);
                    mainVisual[i] = offVisual[i] = null;
                    slots[i] = item;
                    if (item != null)
                    {
                        mainVisual[i] = Spawn(item.visual, item.mount);
                        if (item.dualWield)
                            offVisual[i] = Spawn(item.offhandVisual != null ? item.offhandVisual : item.visual, MountPoint.Offhand);
                    }
                }
            }
            RefreshVisuals();
            SlotsChanged?.Invoke();
        }

        void WriteRun()
        {
            Run.primary = slots[0] != null ? slots[0].id : "";
            Run.secondary = slots[1] != null ? slots[1].id : "";
            Run.skill1 = slots[2] != null ? slots[2].id : "";
            Run.skill2 = slots[3] != null ? slots[3].id : "";
        }

        /// <summary>Which slot a picked-up item would replace (empty first, then same kind).</summary>
        public int SlotFor(ItemDef item)
        {
            if (item == null)
                return -1;
            int a = item.IsWeapon ? 0 : 2, b = a + 1;
            if (slots[a] == null) return a;
            if (slots[b] == null) return b;
            if (slots[a].kind == item.kind) return a;
            if (slots[b].kind == item.kind) return b;
            return b;
        }

        // ---------------------------------------------------------------- input

        public void BufferInput(InputFrame input)
        {
            if (input.primaryPressed) lastPressed[0] = Time.time;
            if (input.secondaryPressed) lastPressed[1] = Time.time;
            if (input.skill1Pressed) lastPressed[2] = Time.time;
            if (input.skill2Pressed) lastPressed[3] = Time.time;
            if (input.flaskPressed) flaskPressed = Time.time;
            // Holding a weapon button keeps attacking; shields use the hold to block instead.
            if (input.primaryHeld && RepeatsWhileHeld(0)) lastPressed[0] = Time.time;
            if (input.secondaryHeld && RepeatsWhileHeld(1)) lastPressed[1] = Time.time;
        }

        bool RepeatsWhileHeld(int slot) => slots[slot] != null && (slots[slot].kind == ItemKind.Melee || slots[slot].kind == ItemKind.Bow);

        bool Buffered(int slot) => Time.time - lastPressed[slot] <= attackBufferTime;

        /// <summary>Slot of a held shield button, or -1.</summary>
        public int HeldShield(InputFrame input)
        {
            for (int i = 0; i < 2; i++)
            {
                if (slots[i] == null || slots[i].kind != ItemKind.Shield)
                    continue;
                if (i == 0 ? input.primaryHeld : input.secondaryHeld)
                    return i;
            }
            return -1;
        }

        public bool TryStartAction()
        {
            for (int i = 0; i < SlotCount; i++)
            {
                if (!Buffered(i))
                    continue;
                var item = slots[i];
                if (item == null || item.kind == ItemKind.Shield)
                    continue;
                if (CooldownRemaining(i) > 0f)
                {
                    if (i >= 2)
                        lastPressed[i] = -10f;
                    continue;
                }
                lastPressed[i] = -10f;
                switch (item.kind)
                {
                    case ItemKind.Melee:
                        if (item.combo.Length == 0)
                            continue;
                        if (Time.time - lastComboEnd[i] > comboResetTime)
                            comboIndex[i] = 0;
                        StartMelee(i, comboIndex[i]);
                        return true;
                    case ItemKind.Bow:
                        StartRanged(i, ActionKind.Shoot, "Bow_Shoot");
                        return true;
                    case ItemKind.Skill:
                        StartRanged(i, ActionKind.Throw, "Throw");
                        return true;
                }
            }
            return false;
        }

        public bool TryDrink()
        {
            if (Time.time - flaskPressed > attackBufferTime)
                return false;
            flaskPressed = -10f;
            if (Run.flaskCharges <= 0)
            {
                Hud?.Toast(Loc.Get("hud.flask_empty"), UIColorWarn);
                return false;
            }
            if (health.Current >= health.maxHealth - 0.5f)
                return false;
            action = ActionKind.Drink;
            actionSlot = -1;
            clock = 0f;
            released = false;
            player.anim.Restart("Drink", 0f);
            RefreshVisuals();
            return true;
        }

        static readonly Color UIColorWarn = new Color(1f, 0.55f, 0.45f);
        static UI.GameHUD Hud => UI.GameHUD.Instance;

        // -------------------------------------------------------------- melee

        /// <summary>Count of attacks/shots started (test statistics).</summary>
        public int ActionsStarted { get; private set; }

        void StartMelee(int slot, int index)
        {
            ActionsStarted++;
            var item = slots[slot];
            action = ActionKind.Melee;
            actionSlot = slot;
            comboIndex[slot] = Mathf.Clamp(index, 0, item.combo.Length - 1);
            step = item.combo[comboIndex[slot]];
            clock = 0f;
            hitThisSwing.Clear();
            arcStarted = arcEnded = false;
            if (player.Input.moveX != 0f)
                player.anim.SetFacing((int)player.Input.moveX);
            RefreshVisuals();
            player.anim.Restart(step.clip, 0f);
            player.anim.SetSpeed(item.animSpeed);
            AirHang();
            player.squash.Add(new Vector2(-0.05f, 0.05f));
        }

        void AirHang()
        {
            if (player.Grounded)
                return;
            // Air attacks hang briefly so combos read in the air.
            var v = player.Body.linearVelocity;
            player.Body.linearVelocity = new Vector2(v.x * 0.6f, Mathf.Max(v.y, 2.2f));
        }

        void StartRanged(int slot, ActionKind kind, string clip)
        {
            ActionsStarted++;
            action = kind;
            actionSlot = slot;
            clock = 0f;
            released = false;
            step = null;
            if (player.Input.moveX != 0f)
                player.anim.SetFacing((int)player.Input.moveX);
            RefreshVisuals();
            player.anim.Restart(clip, 0f);
            player.anim.SetSpeed(1f);
            AirHang();
        }

        /// <summary>Advances the current action. Returns true when it has fully ended.</summary>
        public bool UpdateAttack(float dt)
        {
            switch (action)
            {
                case ActionKind.Melee:
                    return UpdateMelee(dt);
                case ActionKind.Shoot:
                    return UpdateRanged(dt, 9, 20);
                case ActionKind.Throw:
                    return UpdateRanged(dt, 6, 18);
                case ActionKind.Drink:
                    return UpdateDrink(dt);
                default:
                    return true;
            }
        }

        bool UpdateMelee(float dt)
        {
            var item = slots[actionSlot];
            if (item == null || step == null)
            {
                FinishAction();
                return true;
            }
            clock += dt * item.animSpeed;
            float f = Frame;

            if (f < 2f && player.Input.moveX != 0f)
                player.anim.SetFacing((int)player.Input.moveX);

            if (!arcStarted && f >= step.activeFrames.x - 1)
            {
                arcStarted = true;
                if (slashArc != null)
                    slashArc.Begin(item.arcColor, item.arcCore);
            }
            if (arcStarted && !arcEnded && f > step.activeFrames.y + 1)
            {
                arcEnded = true;
                slashArc?.End();
            }

            if (f >= step.activeFrames.x && f < step.activeFrames.y + 1f)
                DoHits(item);

            if (f >= step.cancelFrame && Buffered(actionSlot) && comboIndex[actionSlot] + 1 < item.combo.Length)
            {
                lastPressed[actionSlot] = -10f;
                slashArc?.End();
                StartMelee(actionSlot, comboIndex[actionSlot] + 1);
                return false;
            }

            if (f >= step.totalFrames)
            {
                lastComboEnd[actionSlot] = Time.time;
                comboIndex[actionSlot] = (comboIndex[actionSlot] + 1) % Mathf.Max(1, item.combo.Length);
                FinishAction();
                return true;
            }
            return false;
        }

        bool UpdateRanged(float dt, int releaseFrame, int totalFrames)
        {
            var item = slots[actionSlot];
            clock += dt;
            if (!released && Frame >= releaseFrame)
            {
                released = true;
                if (item != null)
                    Fire(actionSlot, item);
                RefreshVisuals();
            }
            if (Frame >= totalFrames)
            {
                FinishAction();
                return true;
            }
            return false;
        }

        bool UpdateDrink(float dt)
        {
            clock += dt;
            if (!released && Frame >= flaskHealFrame)
            {
                released = true;
                Run.flaskCharges = Mathf.Max(0, Run.flaskCharges - 1);
                float amount = health.maxHealth * flaskHealFraction;
                health.Heal(amount);
                var juice = JuiceEngine.Instance;
                if (juice != null)
                {
                    juice.Embers(transform.position + Vector3.up * 1.2f, 22, new Color(1.2f, 3f, 1.1f));
                    juice.Popup(transform.position + Vector3.up * 2.4f, "+" + Mathf.RoundToInt(amount), new Color(0.5f, 1f, 0.55f), false);
                }
                player.hitFlash?.Flash(new Color(0.8f, 2.4f, 0.9f), 0.7f);
            }
            if (Frame >= 36f)
            {
                FinishAction();
                return true;
            }
            return false;
        }

        void FinishAction()
        {
            slashArc?.End();
            action = ActionKind.None;
            step = null;
            player.anim.SetSpeed(1f);
            RefreshVisuals();
        }

        public void CancelAttack()
        {
            if (action == ActionKind.None)
                return;
            // An interrupted drink does not use the charge.
            slashArc?.End();
            if (action == ActionKind.Melee && actionSlot >= 0)
                comboIndex[actionSlot] = 0;
            action = ActionKind.None;
            step = null;
            if (player != null && player.anim != null)
                player.anim.SetSpeed(1f);
            RefreshVisuals();
        }

        public Vector2 AttackVelocity(Vector2 v, float dt, bool grounded)
        {
            if (action == ActionKind.Melee && step != null)
            {
                float f = Frame;
                if (f >= step.lungeFrames.x && f <= step.lungeFrames.y)
                    v.x = player.Facing * step.lungeSpeed;
                else
                    v.x = Mathf.MoveTowards(v.x, 0f, (grounded ? 140f : 25f) * dt);
                return v;
            }
            float target = action == ActionKind.Drink ? player.Input.moveX * player.runSpeed * 0.25f : 0f;
            v.x = Mathf.MoveTowards(v.x, target, (grounded ? 120f : 25f) * dt);
            return v;
        }

        public float DamageMultiplier => 1f + 0.15f * Run.scrollsPower;

        bool IsCrit(ItemDef item, AttackStep s, Health target)
        {
            var ct = target.GetComponent<ICombatTarget>();
            switch (item.crit)
            {
                case CritRule.Finisher:
                    return s != null && s.finisher;
                case CritRule.Behind:
                    if (ct == null)
                        return false;
                    int side = target.transform.position.x > transform.position.x ? 1 : -1;
                    return ct.FacingDir == side; // facing away from the player
                case CritRule.Disabled:
                    return ct != null && ct.IsDisabled;
                case CritRule.AfterDodge:
                    return Time.time - player.LastDodgeTime <= 1.5f;
                case CritRule.LowHealth:
                    return target.Current <= target.maxHealth * 0.35f;
                default:
                    return false;
            }
        }

        void DoHits(ItemDef item)
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
                bool crit = IsCrit(item, step, target) || (target.GetComponent<StatusEffects>()?.Frozen ?? false);
                float dmg = step.damage * DamageMultiplier * (crit ? item.critMultiplier : 1f) * Random.Range(0.92f, 1.08f);
                if (Cheats.OneHitKills)
                    dmg = 99999f;
                Vector2 dir = new Vector2(facing, 0.3f).normalized;
                Vector2 hitPoint = col.ClosestPoint(new Vector2(origin.x, center.y));
                hitPoint = Vector2.Lerp(hitPoint, (Vector2)col.bounds.center, 0.35f);
                var info = new DamageInfo
                {
                    amount = dmg,
                    knockback = dir * step.knockback * (crit ? 1.3f : 1f),
                    hitPoint = hitPoint,
                    source = gameObject,
                    critical = crit,
                    stun = step.stun,
                    hitStop = Mathf.Lerp(0.04f, 0.08f, crit ? 1f : step.hitStopWeight),
                    shake = crit ? step.shake * 1.5f : step.shake,
                    sparkColor = item.sparkColor,
                    weaponId = item.id,
                    effect = -1,
                };
                // Hitting a frozen enemy shatters the ice.
                target.GetComponent<StatusEffects>()?.BreakFreeze();
                var result = target.TakeDamage(info);
                if (result != DamageResult.Ignored)
                    ReportHit(target, info, result);
            }
        }

        // ------------------------------------------------------------ ranged

        void Fire(int slot, ItemDef item)
        {
            if (!Cheats.NoCooldowns)
            {
                cooldownUntil[slot] = Time.time + item.cooldown;
                cooldownLength[slot] = item.cooldown;
            }
            if (item.projectile == null)
                return;
            int facing = player.Facing;
            Vector3 spawn = item.kind == ItemKind.Bow && bowMount.socket != null
                ? new Vector3(transform.position.x + facing * 0.6f, bowMount.socket.position.y, 0f)
                : new Vector3(transform.position.x + facing * 0.5f, transform.position.y + 1.45f, 0f);
            Vector2 dir = Quaternion.Euler(0f, 0f, item.launchAngle * facing) * new Vector2(facing, 0f);
            if (item.kind == ItemKind.Bow || item.projectileGravity <= 0f)
                dir = AutoAim(spawn, dir, facing);
            var go = Instantiate(item.projectile, spawn, Quaternion.identity);
            go.SetActive(true);
            var p = go.GetComponent<Projectile>() ?? go.AddComponent<Projectile>();
            p.velocity = dir * item.projectileSpeed;
            p.gravity = item.projectileGravity;
            p.damage = item.damage * DamageMultiplier * (Cheats.OneHitKills ? 9999f : 1f);
            p.knockback = item.kind == ItemKind.Bow ? 3f : 6f;
            p.fromPlayer = true;
            p.owner = gameObject;
            p.explodeRadius = item.radius;
            p.pierce = item.pierce;
            p.hasEffect = item.hasEffect;
            p.effect = item.effect;
            p.effectDuration = item.effectDuration;
            p.sparkColor = item.effectColor;
            p.weaponId = item.id;
            p.critAtLongRange = item.crit == CritRule.LongRange;
            p.critMultiplier = item.critMultiplier;
            p.spin = item.spin;
            p.hitRadius = item.kind == ItemKind.Bow ? 0.22f : 0.35f;
            player.squash.Add(new Vector2(0.04f, -0.03f));
            if (item.kind == ItemKind.Bow)
                JuiceEngine.Instance?.Shake(new Vector2(-facing, 0f), 0.06f);
        }

        Vector2 AutoAim(Vector3 from, Vector2 dir, int facing)
        {
            Vector2 best = dir;
            float bestScore = float.MaxValue;
            foreach (var c in Physics2D.OverlapCircleAll(from, 22f, DCLayers.EnemyMask))
            {
                var h = c.GetComponentInParent<Health>();
                if (h == null || h.IsDead)
                    continue;
                Vector2 to = (Vector2)c.bounds.center - (Vector2)from;
                if (Mathf.Sign(to.x) != facing)
                    continue;
                float angle = Vector2.Angle(dir, to);
                if (angle > 30f)
                    continue;
                if (Physics2D.Raycast(from, to.normalized, to.magnitude, DCLayers.SolidMask).collider != null)
                    continue;
                float score = to.magnitude + angle * 0.2f;
                if (score < bestScore)
                {
                    bestScore = score;
                    best = to.normalized;
                }
            }
            return best;
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
            if (!info.projectile)
                player.squash.Add(new Vector2(0.06f, -0.05f));
        }

        // --------------------------------------------------------------- shield

        public void BeginBlock(int slot)
        {
            blocking = true;
            blockSlot = slot;
            blockStart = Time.time;
            shieldScale = 0.2f;
            RefreshVisuals();
            if (mainVisual[slot] != null)
                mainVisual[slot].transform.localScale = Vector3.one * shieldScale;
            player.anim.Restart("Shield_Block", 0f);
            health.blockMultiplier = slots[slot] != null ? 1f - slots[slot].blockReduction : 0.2f;
            health.Interceptor = Intercept;
        }

        public void EndBlock()
        {
            if (!blocking)
                return;
            if (blockSlot >= 0 && mainVisual[blockSlot] != null)
                mainVisual[blockSlot].transform.localScale = Vector3.one;
            blocking = false;
            blockSlot = -1;
            RefreshVisuals();
            if (health.Interceptor == Intercept)
                health.Interceptor = null;
        }

        void Update()
        {
            if (blocking && blockSlot >= 0 && mainVisual[blockSlot] != null && shieldScale < 1f)
            {
                shieldScale = Mathf.MoveTowards(shieldScale, 1f, Time.deltaTime * 14f);
                float pop = shieldScale < 1f ? shieldScale * 1.15f : 1f;
                mainVisual[blockSlot].transform.localScale = Vector3.one * pop;
            }
        }

        DamageResult Intercept(DamageInfo info)
        {
            if (Cheats.GodMode)
                return DamageResult.Ignored;
            if (!blocking || blockSlot < 0)
                return DamageResult.Hit;
            var shield = slots[blockSlot];
            float sourceX = info.projectile ? info.hitPoint.x : info.source != null ? info.source.transform.position.x : transform.position.x - info.knockback.x;
            int side = sourceX >= transform.position.x ? 1 : -1;
            if (side != player.Facing)
                return DamageResult.Hit; // shields only cover the front

            var juice = JuiceEngine.Instance;
            Vector3 contact = transform.position + new Vector3(player.Facing * 0.55f, 1.2f, 0f);
            float window = shield != null ? shield.parryWindow : 0.18f;
            if (Time.time - blockStart <= window)
            {
                if (!info.projectile && info.source != null)
                {
                    info.source.GetComponentInParent<IStunnable>()?.Stun(1.6f, new Vector2(player.Facing * 7f, 2f));
                    var attacker = info.source.GetComponentInParent<Health>();
                    if (attacker != null && !attacker.IsDead && shield != null)
                    {
                        var counter = new DamageInfo
                        {
                            amount = shield.parryDamage * DamageMultiplier * (Cheats.OneHitKills ? 9999f : 1f),
                            knockback = new Vector2(player.Facing * 5f, 1.5f),
                            hitPoint = contact,
                            source = gameObject,
                            critical = true,
                            sparkColor = shield.sparkColor,
                            weaponId = shield.id,
                            effect = -1,
                        };
                        if (attacker.TakeDamage(counter) == DamageResult.Killed)
                            juice?.DamagePopup(attacker.transform.position + Vector3.up * 2f, counter.amount, true);
                    }
                }
                if (juice != null)
                {
                    juice.HitStop(0.11f);
                    juice.Shake(new Vector2(player.Facing, 0.2f), 0.6f);
                    juice.HitSparks(contact, new Vector2(-player.Facing, 0.4f), new Color(3f, 2.3f, 0.6f), 1f);
                    juice.Popup(transform.position + Vector3.up * 2.4f, "PARRY!", new Color(1f, 0.85f, 0.25f), true);
                }
                player.hitFlash?.Flash(new Color(2.4f, 2.0f, 0.8f), 0.8f);
                SaveSystem.Data.stats.parries++;
                Achievements.CheckThresholds();
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

        public bool IsBlocking => blocking;

        void OnDrawGizmosSelected()
        {
            var item = slots[0];
            if (item == null || item.combo.Length == 0)
                return;
            int facing = Application.isPlaying && player != null ? player.Facing : 1;
            foreach (var s in item.combo)
            {
                Gizmos.color = new Color(1f, 0.2f, 0.2f, 0.35f);
                Vector3 c = transform.position + new Vector3(s.hitboxOffset.x * facing, s.hitboxOffset.y, 0f);
                Gizmos.DrawWireCube(c, new Vector3(s.hitboxSize.x, s.hitboxSize.y, 0.1f));
            }
        }
    }
}
