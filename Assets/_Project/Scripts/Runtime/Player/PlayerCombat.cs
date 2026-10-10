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
        readonly Dictionary<string, float> itemCooldowns = new Dictionary<string, float>();
        readonly float[] cooldownLength = new float[SlotCount];
        readonly int[] comboIndex = new int[SlotCount];
        readonly float[] lastComboEnd = { -10f, -10f, -10f, -10f };
        readonly float[] lastPressed = { -10f, -10f, -10f, -10f };
        readonly HashSet<Health> hitThisSwing = new HashSet<Health>();
        bool blockHitThisSwing;

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
            // No recovery lock: once the hit frames are over anything may cancel.
            ActionKind.Melee => step != null && Frame > step.activeFrames.y,
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
            // Cooldowns belong to the item: a new pick-up is ready at once, and dropping and
            // re-taking an item does not reset its cooldown.
            cooldownUntil[slot] = item != null && itemCooldowns.TryGetValue(item.id, out float until) ? until : 0f;
            cooldownLength[slot] = item != null ? item.cooldown : 0f;
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
            string[] rolls = { Run.primaryRoll, Run.secondaryRoll, Run.skill1Roll, Run.skill2Roll };
            amulet = ItemForge.Decode(db.Get(Run.amulet), Run.amuletRoll);
            backpack = ItemForge.Decode(db.Get(Run.backpack), Run.backpackRoll);
            for (int i = 0; i < SlotCount; i++)
            {
                var item = ItemForge.Decode(db.Get(ids[i]), rolls[i]);
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
            Run.primaryRoll = ItemForge.Encode(slots[0]);
            Run.secondaryRoll = ItemForge.Encode(slots[1]);
            Run.skill1Roll = ItemForge.Encode(slots[2]);
            Run.skill2Roll = ItemForge.Encode(slots[3]);
            Run.amulet = amulet != null ? amulet.id : "";
            Run.amuletRoll = ItemForge.Encode(amulet);
            Run.backpack = backpack != null ? backpack.id : "";
            Run.backpackRoll = ItemForge.Encode(backpack);
        }

        ItemDef amulet, backpack;

        /// <summary>Passive amulet slot.</summary>
        public ItemDef Amulet => amulet;

        /// <summary>Weapon carried in the backpack (swap with the primary slot).</summary>
        public ItemDef Backpack => backpack;

        public ItemDef EquipAmulet(ItemDef item)
        {
            var old = amulet;
            amulet = item;
            WriteRun();
            player.RecalculateStats(false);
            SlotsChanged?.Invoke();
            return old;
        }

        /// <summary>Swap the primary weapon with the backpack (backpack must be unlocked).</summary>
        public bool SwapBackpack()
        {
            if (!SaveSystem.Data.meta.backpackUnlocked)
            {
                UI.GameHUD.Instance?.Toast(Loc.Get("hud.backpack_locked"), new Color(0.8f, 0.8f, 0.85f));
                return false;
            }
            if (action != ActionKind.None || blocking)
                return false;
            var stored = backpack;
            backpack = slots[0];
            Equip(0, stored);
            WriteRun();
            Audio.Sfx.Play("weapon.equip");
            if (backpack != null)
                UI.GameHUD.Instance?.Toast(Loc.Get("hud.backpack_swap", ItemForge.FullName(backpack)), new Color(0.8f, 0.9f, 1f));
            return true;
        }

        /// <summary>Which slot a picked-up item would replace (empty first, then same kind).</summary>
        public int SlotFor(ItemDef item)
        {
            if (item == null)
                return -1;
            if (item.kind == ItemKind.Amulet)
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

        const float StartupBoost = 3f;

        /// <summary>
        /// During a cancellable recovery, start another slot's action (the same
        /// slot keeps chaining its own combo in UpdateMelee).
        /// </summary>
        public bool TrySwitchAction()
        {
            if (!CanCancel)
                return false;
            for (int i = 0; i < SlotCount; i++)
            {
                if (i == actionSlot || !Buffered(i) || slots[i] == null || slots[i].kind == ItemKind.Shield || CooldownRemaining(i) > 0f)
                    continue;
                EndEarly();
                return TryStartAction();
            }
            return false;
        }

        /// <summary>Ends the current action as if it had played out (keeps combo progress).</summary>
        public void EndEarly()
        {
            if (action == ActionKind.Melee && actionSlot >= 0 && slots[actionSlot] != null)
            {
                lastComboEnd[actionSlot] = Time.time;
                comboIndex[actionSlot] = (comboIndex[actionSlot] + 1) % Mathf.Max(1, slots[actionSlot].combo.Length);
            }
            slashArc?.End();
            FinishAction();
        }

        /// <summary>True while some attack button is pressed or buffered.</summary>
        public bool AnyAttackBuffered
        {
            get
            {
                for (int i = 0; i < SlotCount; i++)
                    if (Buffered(i) && slots[i] != null && slots[i].kind != ItemKind.Shield)
                        return true;
                return false;
            }
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
                Audio.Sfx.Play("player.flask_empty");
                return false;
            }
            if (health.Current >= health.maxHealth - 0.5f)
                return false;
            action = ActionKind.Drink;
            actionSlot = -1;
            clock = 0f;
            released = false;
            player.anim.Restart("Drink", 0f);
            Audio.Sfx.Play("player.drink", transform.position);
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
            if (comboIndex[slot] == 0)
                chainHits = 0;
            waveFired = false;
            clock = 0f;
            hitThisSwing.Clear();
            blockHitThisSwing = false;
            arcStarted = arcEnded = false;
            if (player.Input.moveX != 0f)
                player.anim.SetFacing((int)player.Input.moveX);
            RefreshVisuals();
            player.anim.Restart(step.clip, 0f);
            player.anim.SetSpeed(item.animSpeed);
            Audio.Sfx.Play(string.IsNullOrEmpty(item.swingSound) ? "swing.light" : item.swingSound, transform.position + Vector3.up,
                1f, step.finisher ? 0.9f : 1f);
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
                    return UpdateRanged(dt, 5, 14);
                case ActionKind.Throw:
                    return UpdateRanged(dt, 4, 12);
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
            // Wind-up frames play three times faster so the hit comes out at once.
            float boost = Frame < step.activeFrames.x ? StartupBoost : 1f;
            clock += dt * item.animSpeed * boost;
            player.anim.SetSpeed(item.animSpeed * (Frame < step.activeFrames.x ? StartupBoost : 1f));
            float f = Frame;

            // Turning is never locked.
            if (player.Input.moveX != 0f && (int)Mathf.Sign(player.Input.moveX) != player.Facing)
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
            if (step.finisher && !waveFired && item.finisherWave != null && f >= step.activeFrames.x)
            {
                waveFired = true;
                LaunchWave(item);
            }

            if (f > step.activeFrames.y && Buffered(actionSlot) && comboIndex[actionSlot] + 1 < item.combo.Length)
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
            if (!released && player.Input.moveX != 0f)
                player.anim.SetFacing((int)player.Input.moveX);
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
                float amount = health.maxHealth * flaskHealFraction * (1f + 0.3f * ItemForge.AmuletCount(Affix.FlaskPower));
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

        /// <summary>Generic damage multiplier (best colour stat) for sources without an item.</summary>
        public float DamageMultiplier => DamageFor(null);

        /// <summary>Scroll level an item scales with: the best of its colours (Dead Cells rule).</summary>
        public static int ColorLevel(ItemDef item)
        {
            var r = Run;
            if (item == null || item.colors == ItemColor.None)
                return Mathf.Max(r.brutality, Mathf.Max(r.tactics, r.survival));
            int best = 0;
            if ((item.colors & ItemColor.Brutality) != 0) best = Mathf.Max(best, r.brutality);
            if ((item.colors & ItemColor.Tactics) != 0) best = Mathf.Max(best, r.tactics);
            if ((item.colors & ItemColor.Survival) != 0) best = Mathf.Max(best, r.survival);
            return best;
        }

        /// <summary>Damage multiplier for hits made with `item` (colour scrolls, amulet, rage buff).</summary>
        public float DamageFor(ItemDef item) =>
            (1f + 0.15f * ColorLevel(item)) * (1f + 0.1f * ItemForge.AmuletCount(Affix.AllDamage)) *
            (Time.time < buffUntil ? 1f + buffAmount : 1f);

        float buffUntil, buffAmount;
        int chainHits;
        bool waveFired;

        /// <summary>Reflected projectiles gain this multiplier (the raised shield's).</summary>
        public float ReflectMultiplier => blocking && blockSlot >= 0 && slots[blockSlot] != null ? slots[blockSlot].reflectMultiplier : 1.5f;

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
                case CritRule.Burning:
                    return target.GetComponent<StatusEffects>()?.Burning ?? false;
                case CritRule.Airborne:
                    return !player.Grounded;
                case CritRule.Afflicted:
                    return target.GetComponent<StatusEffects>()?.Afflicted ?? false;
                default:
                    return false;
            }
        }

        void DoHits(ItemDef item)
        {
            int facing = player.Facing;
            Vector2 origin = transform.position;
            Vector2 center = origin + new Vector2(step.hitboxOffset.x * facing, step.hitboxOffset.y);
            if (!blockHitThisSwing && DeadCells.Run.Breakable.HitArea(center, step.hitboxSize, false))
                blockHitThisSwing = true;
            var cols = Physics2D.OverlapBoxAll(center, step.hitboxSize, 0f, DCLayers.EnemyMask);
            foreach (var col in cols)
            {
                var target = col.GetComponentInParent<Health>();
                if (target == null || target.IsDead || hitThisSwing.Contains(target))
                    continue;
                hitThisSwing.Add(target);
                bool crit = IsCrit(item, step, target) || (target.GetComponent<StatusEffects>()?.Frozen ?? false);
                var status = target.GetComponent<StatusEffects>();
                float dmg = step.damage * DamageFor(item) * Mutations.Damage(item, target, player)
                            * (crit ? item.critMultiplier + Mutations.CritBonus : 1f) * Random.Range(0.92f, 1.08f);
                if (item.bonusVsAfflicted > 0f && status != null && status.Afflicted)
                    dmg *= 1f + item.bonusVsAfflicted;
                if (item.comboRamp > 0f)
                    dmg *= 1f + item.comboRamp * Mathf.Min(chainHits, 20);
                var enemy = target.GetComponentInParent<Enemies.EnemyBase>();
                if (item.eliteBonus != 1f && enemy != null && (enemy.IsElite || enemy.IsBoss))
                    dmg *= item.eliteBonus;
                if (Cheats.OneHitKills)
                    dmg = 99999f;
                Vector2 dir = new Vector2(facing, 0.3f).normalized;
                if (item.pull > 0f && step.finisher)
                    dir = new Vector2(-facing * item.pull / Mathf.Max(1f, step.knockback), 0.35f);
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
                if (result == DamageResult.Hit || result == DamageResult.Killed)
                {
                    chainHits++;
                    if (item.onHitChance > 0f && item.hasEffect && Random.value < item.onHitChance)
                        status?.Apply(item.effect, item.effectDuration * Mutations.StatusDuration(item.effect));
                    if (item.hasAffixEffect && Random.value < item.affixEffectChance)
                        status?.Apply(item.affixEffect, item.effectDuration * Mutations.StatusDuration(item.affixEffect));
                    float steal = item.lifesteal + Mutations.MeleeLifesteal;
                    if (steal > 0f)
                        health.Heal(dmg * steal);
                }
                if (result != DamageResult.Ignored)
                    ReportHit(target, info, result);
            }
        }

        void LaunchWave(ItemDef item)
        {
            int facing = player.Facing;
            var go = Instantiate(item.finisherWave, transform.position + new Vector3(facing * 1.0f, 0.6f, 0f), Quaternion.identity);
            go.SetActive(true);
            var p = go.GetComponent<Projectile>();
            p.velocity = new Vector2(facing * 15f, 0f);
            p.gravity = 0f;
            p.damage = item.finisherWaveDamage * DamageFor(item);
            p.fromPlayer = true;
            p.owner = gameObject;
            p.pierce = true;
            p.lifetime = 0.7f;
            p.knockback = 6f;
            p.weaponId = item.id;
            p.sparkColor = item.sparkColor;
            Audio.Sfx.Play("boss.shockwave", transform.position, 0.6f, 1.3f);
        }

        // ------------------------------------------------------------ ranged

        void Fire(int slot, ItemDef item)
        {
            if (!Cheats.NoCooldowns)
            {
                float cd = item.cooldown * Mutations.CooldownMultiplier(item);
                cooldownUntil[slot] = Time.time + cd;
                cooldownLength[slot] = cd;
                itemCooldowns[item.id] = cooldownUntil[slot];
            }
            string fire = !string.IsNullOrEmpty(item.fireSound) ? item.fireSound : item.kind == ItemKind.Bow ? "bow.shoot" : "grenade.throw";
            Audio.Sfx.Play(fire, transform.position + Vector3.up * 1.3f);
            if (item.kind == ItemKind.Skill && item.skillKind != SkillKind.Throw)
            {
                UseSkill(item);
                return;
            }
            if (item.projectile == null)
                return;
            Volley(item);
            for (int b = 1; b < Mathf.Max(1, item.burst); b++)
                StartCoroutine(DelayedVolley(item, b * item.burstInterval));
            player.squash.Add(new Vector2(0.04f, -0.03f));
            if (item.kind == ItemKind.Bow)
                JuiceEngine.Instance?.Shake(new Vector2(-player.Facing, 0f), 0.06f);
        }

        System.Collections.IEnumerator DelayedVolley(ItemDef item, float delay)
        {
            yield return new WaitForSeconds(delay);
            if (player.State != PlayerState.Dead)
            {
                Volley(item);
                Audio.Sfx.Play(!string.IsNullOrEmpty(item.fireSound) ? item.fireSound : "bow.shoot", transform.position + Vector3.up * 1.3f, 0.7f, 1.1f);
            }
        }

        void Volley(ItemDef item)
        {
            int facing = player.Facing;
            Vector3 spawn = item.kind == ItemKind.Bow && bowMount.socket != null
                ? new Vector3(transform.position.x + facing * 0.6f, bowMount.socket.position.y, 0f)
                : new Vector3(transform.position.x + facing * 0.5f, transform.position.y + 1.45f, 0f);
            Vector2 dir = Quaternion.Euler(0f, 0f, item.launchAngle * facing) * new Vector2(facing, 0f);
            if (item.kind == ItemKind.Bow || item.projectileGravity <= 0f)
                dir = AutoAim(spawn, dir, facing);
            int n = Mathf.Max(1, item.projectileCount);
            for (int i = 0; i < n; i++)
            {
                float a = (i - (n - 1) * 0.5f) * item.spread;
                SpawnProjectile(item, spawn, Quaternion.Euler(0f, 0f, a) * dir);
            }
        }

        Projectile SpawnProjectile(ItemDef item, Vector3 spawn, Vector2 dir)
        {
            var go = Instantiate(item.projectile, spawn, Quaternion.identity);
            go.SetActive(true);
            if (item.projectileScale != 1f)
                go.transform.localScale *= item.projectileScale;
            var p = go.GetComponent<Projectile>() ?? go.AddComponent<Projectile>();
            p.velocity = dir.normalized * item.projectileSpeed;
            p.gravity = item.projectileGravity;
            p.damage = item.damage * DamageFor(item) * Mutations.Damage(item, null, player) * (Cheats.OneHitKills ? 9999f : 1f);
            p.bonusVsAfflicted = item.bonusVsAfflicted;
            p.hasAffixEffect = item.hasAffixEffect;
            p.affixEffect = item.affixEffect;
            p.affixEffectChance = item.affixEffectChance;
            p.knockback = (item.kind == ItemKind.Bow ? 3f : 6f) * item.knockbackScale;
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
            p.critMultiplier = item.critMultiplier + Mutations.CritBonus;
            p.spin = item.spin;
            p.hitRadius = (item.kind == ItemKind.Bow ? 0.22f : 0.35f) * Mathf.Max(1f, item.projectileScale);
            p.homing = item.homing;
            p.bounces = item.bounces;
            p.boomerang = item.boomerang;
            p.chain = item.chain;
            p.pull = item.pullOnHit;
            p.lifetime = item.boomerang ? 3f : item.projectileLifetime;
            p.burstItem = item.burstKind != BurstKind.None ? item : null;
            return p;
        }

        // -------------------------------------------------------------- skills

        void UseSkill(ItemDef item)
        {
            int facing = player.Facing;
            var juice = JuiceEngine.Instance;
            Vector3 chest = transform.position + Vector3.up * 1.1f;
            switch (item.skillKind)
            {
                case SkillKind.Rain:
                {
                    Vector3 target = transform.position + new Vector3(facing * 5f, 0f, 0f);
                    float best = 14f;
                    foreach (var c in Physics2D.OverlapCircleAll(chest, 14f, DCLayers.EnemyMask))
                    {
                        var h = c.GetComponentInParent<Health>();
                        float d = Vector2.Distance(chest, c.bounds.center);
                        if (h != null && !h.IsDead && d < best)
                        {
                            best = d;
                            target = c.bounds.center;
                        }
                    }
                    for (int i = 0; i < item.count; i++)
                        StartCoroutine(RainDrop(item, target + new Vector3(Random.Range(-2.6f, 2.6f), 9f + Random.Range(0f, 2f), 0f), i * 0.12f));
                    break;
                }
                case SkillKind.Deploy:
                    DeadCells.Run.Deployable.Spawn(item, transform.position + new Vector3(facing * 0.9f, 0f, 0f), gameObject);
                    break;
                case SkillKind.Nova:
                {
                    juice?.SlamWave(chest, item.radius);
                    juice?.Embers(chest, 30, item.effectColor);
                    juice?.Shake(Vector2.up, 0.3f);
                    foreach (var c in Physics2D.OverlapCircleAll(chest, item.radius, DCLayers.EnemyMask))
                    {
                        var h = c.GetComponentInParent<Health>();
                        if (h == null || h.IsDead)
                            continue;
                        Vector2 away = ((Vector2)c.bounds.center - (Vector2)chest).normalized;
                        var info = new DamageInfo
                        {
                            amount = item.damage * DamageFor(item), knockback = away * 6f * item.power + Vector2.up * 2f,
                            hitPoint = c.bounds.center, source = gameObject, stun = 0.4f, hitStop = 0.03f, shake = 0.1f,
                            sparkColor = item.effectColor, weaponId = item.id, projectile = true, effect = -1,
                        };
                        var result = item.damage > 0f ? h.TakeDamage(info) : DamageResult.Hit;
                        if (item.hasEffect && (result == DamageResult.Hit || result == DamageResult.Killed))
                            h.GetComponent<StatusEffects>()?.Apply(item.effect, item.effectDuration);
                        if (item.damage > 0f && result != DamageResult.Ignored)
                            ReportHit(h, info, result);
                    }
                    break;
                }
                case SkillKind.Dash:
                {
                    Vector2 dir = new Vector2(facing, 0f);
                    float dist = item.power;
                    var wall = Physics2D.Raycast(chest, dir, dist, DCLayers.SolidMask);
                    if (wall.collider != null)
                        dist = Mathf.Max(0f, wall.distance - 0.5f);
                    Vector3 start = transform.position;
                    Vector3 end = start + new Vector3(facing * dist, 0f, 0f);
                    Vector2 mid = (Vector2)(start + end) * 0.5f + Vector2.up * 1f;
                    foreach (var c in Physics2D.OverlapBoxAll(mid, new Vector2(dist + 1f, 1.8f), 0f, DCLayers.EnemyMask))
                    {
                        var h = c.GetComponentInParent<Health>();
                        if (h == null || h.IsDead)
                            continue;
                        var info = new DamageInfo
                        {
                            amount = item.damage * DamageFor(item), knockback = new Vector2(facing * 3f, 3f), hitPoint = c.bounds.center,
                            source = gameObject, stun = 0.3f, hitStop = 0.03f, shake = 0.12f, sparkColor = item.effectColor,
                            weaponId = item.id, projectile = true, effect = -1,
                        };
                        var result = h.TakeDamage(info);
                        if (item.hasEffect && (result == DamageResult.Hit || result == DamageResult.Killed))
                            h.GetComponent<StatusEffects>()?.Apply(item.effect, item.effectDuration);
                        if (result != DamageResult.Ignored)
                            ReportHit(h, info, result);
                    }
                    for (int k = 0; k <= 8; k++)
                        juice?.Embers(Vector3.Lerp(start, end, k / 8f) + Vector3.up, 4, item.effectColor);
                    health.InvulnerableUntil = Mathf.Max(health.InvulnerableUntil, Time.time + 0.35f);
                    player.Teleport(end + Vector3.up * 0.05f);
                    break;
                }
                case SkillKind.Buff:
                    buffUntil = Time.time + item.duration;
                    buffAmount = item.power;
                    player.hitFlash?.Flash(new Color(3f, 0.6f, 0.5f), 0.9f);
                    juice?.Embers(chest, 24, item.effectColor);
                    juice?.Popup(transform.position + Vector3.up * 2.4f, "+" + Mathf.RoundToInt(item.power * 100f) + "%", new Color(1f, 0.4f, 0.35f), true);
                    break;
            }
        }

        System.Collections.IEnumerator RainDrop(ItemDef item, Vector3 from, float delay)
        {
            yield return new WaitForSeconds(delay);
            if (item.projectile == null)
                yield break;
            var p = SpawnProjectile(item, from, new Vector2(Random.Range(-0.15f, 0.15f), -1f));
            p.gravity = 12f;
            p.lifetime = 2.5f;
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
            bool kill = result == DamageResult.Killed;
            if (result == DamageResult.Hit || kill)
                player.Recover(info.amount);
            if (kill)
            {
                Mutations.OnKill(player);
                var src = SlotItem(info.weaponId);
                if (src != null && src.healOnKill > 0f)
                    health.Heal(health.maxHealth * src.healOnKill);
                if (src != null && src.killBurst > 0f)
                    KillBurst(target.transform.position + Vector3.up, info.amount * src.killBurst, src);
            }
            var juice = JuiceEngine.Instance;
            if (juice == null)
                return;
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
            {
                var item = slots[Mathf.Clamp(actionSlot, 0, SlotCount - 1)];
                string hit = item != null && item.id == info.weaponId && !string.IsNullOrEmpty(item.hitSound) ? item.hitSound : "hit.flesh";
                Audio.Sfx.Play(hit, p);
            }
            if (info.critical)
                Audio.Sfx.Play("hit.crit", p);
            if (kill)
                Audio.Sfx.Play("enemy.kill", p);
            if (!info.projectile)
                player.squash.Add(new Vector2(0.06f, -0.05f));
        }

        ItemDef SlotItem(string id)
        {
            if (string.IsNullOrEmpty(id))
                return null;
            foreach (var it in slots)
                if (it != null && it.id == id)
                    return it;
            return null;
        }

        void KillBurst(Vector3 at, float damage, ItemDef src)
        {
            JuiceEngine.Instance?.SlamWave(at, 2f);
            Audio.Sfx.Play("explode.fire", at, 0.5f, 1.2f);
            foreach (var c in Physics2D.OverlapCircleAll(at, 2f, DCLayers.EnemyMask))
            {
                var h = c.GetComponentInParent<Health>();
                if (h == null || h.IsDead)
                    continue;
                h.TakeDamage(new DamageInfo
                {
                    amount = Mathf.Max(5f, damage), knockback = ((Vector2)(c.bounds.center - at)).normalized * 5f, hitPoint = c.bounds.center,
                    source = gameObject, stun = 0.2f, sparkColor = src.sparkColor, weaponId = "killburst", projectile = true, effect = -1,
                });
            }
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
            Audio.Sfx.Play("shield.raise", transform.position + Vector3.up);
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
            float window = (shield != null ? shield.parryWindow : 0.18f) * Mutations.ParryWindowMultiplier;
            if (Time.time - blockStart <= window)
            {
                if (shield != null && shield.parryRadius > 0f)
                {
                    foreach (var c in Physics2D.OverlapCircleAll(contact, shield.parryRadius, DCLayers.EnemyMask))
                    {
                        c.GetComponentInParent<IStunnable>()?.Stun(1.4f, new Vector2(Mathf.Sign(c.bounds.center.x - contact.x) * 5f, 2f));
                        if (shield.parryApplies && shield.hasEffect)
                            c.GetComponentInParent<StatusEffects>()?.Apply(shield.effect, shield.effectDuration);
                    }
                    juice?.SlamWave(contact, shield.parryRadius);
                }
                if (!info.projectile && info.source != null)
                {
                    info.source.GetComponentInParent<IStunnable>()?.Stun(1.6f, new Vector2(player.Facing * 7f, 2f));
                    if (shield != null && shield.parryApplies && shield.hasEffect)
                        info.source.GetComponentInParent<StatusEffects>()?.Apply(shield.effect, shield.effectDuration);
                    var attacker = info.source.GetComponentInParent<Health>();
                    if (attacker != null && !attacker.IsDead && shield != null)
                    {
                        var counter = new DamageInfo
                        {
                            amount = shield.parryDamage * DamageFor(shield) * Mutations.ParryDamageMultiplier * (Cheats.OneHitKills ? 9999f : 1f),
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
                Audio.Sfx.Play("shield.parry", contact);
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
            Audio.Sfx.Play("shield.block", contact);
            if (shield != null && shield.thorns > 0f && !info.projectile && info.source != null)
            {
                var attacker = info.source.GetComponentInParent<Health>();
                if (attacker != null && !attacker.IsDead)
                {
                    var thorn = new DamageInfo
                    {
                        amount = shield.thorns * DamageFor(shield), knockback = new Vector2(player.Facing * 4f, 1f), hitPoint = contact,
                        source = gameObject, sparkColor = shield.sparkColor, weaponId = shield.id, effect = -1, stun = 0.2f,
                    };
                    var r = attacker.TakeDamage(thorn);
                    if (r != DamageResult.Ignored)
                        ReportHit(attacker, thorn, r);
                }
            }
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
