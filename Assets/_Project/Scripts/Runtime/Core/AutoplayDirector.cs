using System.Collections.Generic;
using System.IO;
using DeadCells.Enemies;
using DeadCells.Player;
using UnityEngine;

namespace DeadCells.Core
{
    /// <summary>
    /// Demo/verification driver, enabled by the -autoplay command-line flag
    /// (or the inspector toggle). Plays a scripted showcase of every move, then
    /// a simple seek-and-fight bot; saves screenshots to -captureDir and quits
    /// after -autoplaySeconds. Writes a short run log next to the captures.
    /// </summary>
    public class AutoplayDirector : MonoBehaviour, IInputSource
    {
        public PlayerController player;
        public bool forceEnable;
        public float duration = 26f;
        public float captureInterval = 0.5f;
        public string captureDir = "Captures";
        [Tooltip("Dense capture window (seconds since start) for inspecting animation/FX timing.")]
        public Vector2 burstWindow = new Vector2(-1f, -1f);
        public float burstInterval = 1f / 30f;

        struct Step
        {
            public float start, length;
            public float moveX;
            public bool down, jump, attack, dodge, shield, swap, flame;
        }

        /// <summary>Signed direction to the nearest living zombie (0 if none).</summary>
        float AimAtNearest()
        {
            var z = Nearest(out _);
            return z == null ? 0f : Mathf.Sign(z.transform.position.x - player.transform.position.x);
        }

        ZombieEnemy Nearest(out float score)
        {
            ZombieEnemy target = null;
            score = float.MaxValue;
            foreach (var z in FindObjectsByType<ZombieEnemy>())
            {
                if (z.IsDead || !z.gameObject.activeInHierarchy)
                    continue;
                float d = Mathf.Abs(z.transform.position.x - player.transform.position.x) + Mathf.Abs(z.transform.position.y - player.transform.position.y) * 2f;
                if (d < score)
                {
                    score = d;
                    target = z;
                }
            }
            return target;
        }

        readonly List<Step> script = new List<Step>();
        float startTime;
        float nextCapture;
        int captureIndex;
        bool active;
        StreamWriter log;
        int prevStep = -1;
        float botAttackTimer;
        float botJumpTimer;
        int errors;

        void Awake()
        {
            var args = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == "-autoplay")
                    active = true;
                else if (args[i] == "-captureDir" && i + 1 < args.Length)
                    captureDir = args[i + 1];
                else if (args[i] == "-autoplaySeconds" && i + 1 < args.Length && float.TryParse(args[i + 1], out float s))
                    duration = s;
                else if (args[i] == "-captureInterval" && i + 1 < args.Length && float.TryParse(args[i + 1], out float c))
                    captureInterval = c;
                else if (args[i] == "-burst" && i + 2 < args.Length && float.TryParse(args[i + 1], out float b0) && float.TryParse(args[i + 2], out float b1))
                    burstWindow = new Vector2(b0, b1);
            }
            active |= forceEnable;
            if (!active)
            {
                enabled = false;
                return;
            }
            Directory.CreateDirectory(captureDir);
            log = new StreamWriter(Path.Combine(captureDir, "autoplay_log.txt"), false);
            Application.logMessageReceived += OnLog;
            BuildScript();
        }

        void Start()
        {
            if (!active)
                return;
            player.InputSource = this;
            startTime = Time.time;
            nextCapture = startTime + 0.6f;
        }

        void OnDestroy()
        {
            Application.logMessageReceived -= OnLog;
            log?.Dispose();
        }

        void OnLog(string condition, string stackTrace, LogType type)
        {
            if (type == LogType.Error || type == LogType.Exception || type == LogType.Assert)
            {
                errors++;
                log?.WriteLine($"[{Time.time:F2}] {type}: {condition}\n{stackTrace}");
            }
        }

        void Add(float start, float length, float moveX = 0f, bool down = false, bool jump = false, bool attack = false,
            bool dodge = false, bool shield = false, bool swap = false, bool flame = false)
        {
            script.Add(new Step { start = start, length = length, moveX = moveX, down = down, jump = jump, attack = attack, dodge = dodge, shield = shield, swap = swap, flame = flame });
        }

        void BuildScript()
        {
            Add(0.0f, 1.0f);                                   // idle: breathing, scarf
            Add(1.0f, 1.1f, moveX: 1f);                        // run right
            Add(2.1f, 0.6f, moveX: 1f, jump: true);            // running jump
            Add(2.7f, 0.5f, moveX: 1f);
            Add(3.2f, 0.4f, moveX: 1f, dodge: true);           // dodge roll
            Add(3.6f, 0.4f);
            Add(4.0f, 0.35f, jump: true);                      // jump...
            Add(4.35f, 0.9f, down: true, jump: true);          // ...ground pound
            Add(5.25f, 0.5f);
            Add(5.75f, 0.12f, attack: true);                   // combo in the air-free spot
            Add(5.95f, 0.12f, attack: true);
            Add(6.25f, 0.12f, attack: true);
            Add(6.9f, 0.7f, shield: true);                     // shield raise
            Add(7.6f, 0.1f, flame: true);                      // flame preset cycle
            Add(7.8f, 0.4f, moveX: -1f);
            Add(8.2f, 0.1f, swap: true);                       // broadsword
            Add(8.4f, 0.12f, attack: true);
            Add(8.8f, 0.12f, attack: true);
            Add(9.3f, 0.12f, attack: true);
            Add(10.2f, 0.1f, swap: true);                      // back to rusty sword
            Add(10.3f, 0.1f, flame: true);
            Add(10.4f, 0.1f, flame: true);
        }

        public InputFrame Read()
        {
            var f = new InputFrame();
            float t = Time.time - startTime;
            int stepIndex = -1;
            for (int i = 0; i < script.Count; i++)
            {
                if (t >= script[i].start && t < script[i].start + script[i].length)
                    stepIndex = i;
            }
            if (stepIndex >= 0)
            {
                var s = script[stepIndex];
                bool first = stepIndex != prevStep;
                f.moveX = s.moveX;
                // Showcase attacks and blocks turn towards the nearest zombie on their first frame.
                if (first && (s.attack || s.shield) && s.moveX == 0f)
                    f.moveX = AimAtNearest();
                f.down = s.down;
                f.jumpHeld = s.jump;
                f.jumpPressed = s.jump && first;
                f.attackPressed = s.attack && first;
                f.dodgePressed = s.dodge && first;
                f.shieldHeld = s.shield;
                f.shieldPressed = s.shield && first;
                f.swapWeaponPressed = s.swap && first;
                f.cycleFlamePressed = s.flame && first;
                prevStep = stepIndex;
                return f;
            }
            prevStep = -1;
            if (t > script[script.Count - 1].start + 0.6f)
                return Bot(f);
            return f;
        }

        InputFrame Bot(InputFrame f)
        {
            var target = Nearest(out _);
            if (target == null)
            {
                f.moveX = 1f;
                return f;
            }
            float dx = target.transform.position.x - player.transform.position.x;
            float dy = target.transform.position.y - player.transform.position.y;
            botAttackTimer -= Time.deltaTime;
            botJumpTimer -= Time.deltaTime;
            bool blocked = false;
            if (Mathf.Abs(dx) > 1.6f)
            {
                f.moveX = Mathf.Sign(dx);
                // A wall or ledge in the way: jump over it.
                var hit = Physics2D.Raycast((Vector2)player.transform.position + Vector2.up * 0.4f, new Vector2(f.moveX, 0f), 0.8f, DCLayers.SolidMask);
                blocked = hit.collider != null;
            }
            else
            {
                if (Mathf.Sign(dx) != player.Facing)
                    f.moveX = Mathf.Sign(dx);
                if (botAttackTimer <= 0f)
                {
                    f.attackPressed = true;
                    botAttackTimer = 0.17f;
                }
            }
            if ((dy > 1.2f || blocked) && botJumpTimer <= 0f && player.Grounded)
            {
                f.jumpPressed = true;
                f.jumpHeld = true;
                botJumpTimer = 0.8f;
            }
            else
                f.jumpHeld = botJumpTimer > 0.35f;
            return f;
        }

        void LateUpdate()
        {
            float t = Time.time - startTime;
            if (Time.time >= nextCapture)
            {
                bool burst = t >= burstWindow.x && t <= burstWindow.y;
                nextCapture = Time.time + (burst ? burstInterval : captureInterval);
                string path = Path.Combine(captureDir, $"frame_{captureIndex++:000}_{t:00.00}s.png");
                ScreenCapture.CaptureScreenshot(path);
                log?.WriteLine($"[{t:F2}] capture {path} state={player.State} hp={player.Health.Current:F0} pos={player.transform.position}");
            }
            if (t >= duration)
            {
                log?.WriteLine($"done. errors={errors} fps~{1f / Mathf.Max(0.0001f, Time.smoothDeltaTime):F0}");
                log?.Flush();
                Application.Quit();
#if UNITY_EDITOR
                UnityEditor.EditorApplication.isPlaying = false;
#endif
                enabled = false;
            }
        }
    }
}
