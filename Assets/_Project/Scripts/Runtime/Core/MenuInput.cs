using UnityEngine;
using UnityEngine.InputSystem;

namespace DeadCells.Core
{
    /// <summary>
    /// Menu navigation polled straight from the devices (keyboard, gamepad,
    /// mouse), cached once per frame, with key repeat on held directions.
    /// Works while Time.timeScale is 0.
    /// </summary>
    public static class MenuInput
    {
        static int frame = -1;
        static bool up, down, left, right, confirm, cancel, map, anyKey;
        static Vector2Int heldDir;
        static float repeatAt;
        static string typed = "";

        public static bool Up { get { Poll(); return up; } }
        public static bool Down { get { Poll(); return down; } }
        public static bool Left { get { Poll(); return left; } }
        public static bool Right { get { Poll(); return right; } }
        public static bool Confirm { get { Poll(); return confirm; } }
        public static bool Cancel { get { Poll(); return cancel; } }
        public static bool Map { get { Poll(); return map; } }
        public static bool AnyKey { get { Poll(); return anyKey; } }
        public static Vector2 MousePosition => Mouse.current != null ? Mouse.current.position.ReadValue() : new Vector2(-1f, -1f);
        public static bool MouseClicked => Mouse.current != null && Mouse.current.leftButton.wasPressedThisFrame;
        public static bool MouseMoved => Mouse.current != null && Mouse.current.delta.ReadValue().sqrMagnitude > 0.5f;

        /// <summary>Letters typed recently (for the cheat code), newest last, max 12.</summary>
        public static string Typed { get { Poll(); return typed; } }

        public static void ClearTyped() => typed = "";

        static void Poll()
        {
            if (frame == Time.frameCount)
                return;
            frame = Time.frameCount;
            var kb = Keyboard.current;
            var pad = Gamepad.current;

            Vector2Int dir = Vector2Int.zero;
            if (kb != null)
            {
                if (kb.wKey.isPressed || kb.upArrowKey.isPressed) dir.y += 1;
                if (kb.sKey.isPressed || kb.downArrowKey.isPressed) dir.y -= 1;
                if (kb.aKey.isPressed || kb.leftArrowKey.isPressed) dir.x -= 1;
                if (kb.dKey.isPressed || kb.rightArrowKey.isPressed) dir.x += 1;
            }
            if (pad != null)
            {
                Vector2 s = pad.leftStick.ReadValue() + pad.dpad.ReadValue();
                if (s.y > 0.5f) dir.y = 1;
                if (s.y < -0.5f) dir.y = -1;
                if (s.x < -0.5f) dir.x = -1;
                if (s.x > 0.5f) dir.x = 1;
            }
            dir.x = Mathf.Clamp(dir.x, -1, 1);
            dir.y = Mathf.Clamp(dir.y, -1, 1);
            bool fire = false;
            float now = Time.unscaledTime;
            if (dir != heldDir)
            {
                heldDir = dir;
                fire = dir != Vector2Int.zero;
                repeatAt = now + 0.38f;
            }
            else if (dir != Vector2Int.zero && now >= repeatAt)
            {
                fire = true;
                repeatAt = now + 0.09f;
            }
            up = fire && dir.y > 0;
            down = fire && dir.y < 0;
            left = fire && dir.x < 0 && dir.y == 0;
            right = fire && dir.x > 0 && dir.y == 0;

            confirm = (kb != null && (kb.enterKey.wasPressedThisFrame || kb.numpadEnterKey.wasPressedThisFrame || kb.spaceKey.wasPressedThisFrame || kb.jKey.wasPressedThisFrame))
                      || (pad != null && pad.buttonSouth.wasPressedThisFrame);
            cancel = (kb != null && (kb.escapeKey.wasPressedThisFrame || kb.backspaceKey.wasPressedThisFrame))
                     || (pad != null && (pad.buttonEast.wasPressedThisFrame || pad.startButton.wasPressedThisFrame));
            map = (kb != null && (kb.tabKey.wasPressedThisFrame || kb.mKey.wasPressedThisFrame)) || (pad != null && pad.selectButton.wasPressedThisFrame);
            anyKey = (kb != null && kb.anyKey.wasPressedThisFrame) || (pad != null && (pad.buttonSouth.wasPressedThisFrame || pad.startButton.wasPressedThisFrame)) || MouseClicked;

            if (kb != null)
            {
                for (Key k = Key.A; k <= Key.Z; k++)
                {
                    if (kb[k].wasPressedThisFrame)
                    {
                        typed += (char)('A' + (k - Key.A));
                        if (typed.Length > 12)
                            typed = typed.Substring(typed.Length - 12);
                    }
                }
            }
        }
    }

    /// <summary>Game pause that cooperates with hit-stop (both drive Time.timeScale).</summary>
    public static class GamePause
    {
        public static bool Paused { get; private set; }

        public static event System.Action<bool> Changed;

        public static void Set(bool paused)
        {
            if (Paused == paused)
                return;
            Paused = paused;
            Time.timeScale = paused ? 0f : 1f;
            Changed?.Invoke(paused);
        }
    }
}
