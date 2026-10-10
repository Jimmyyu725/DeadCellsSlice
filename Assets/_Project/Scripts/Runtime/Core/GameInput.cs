using UnityEngine;
using UnityEngine.InputSystem;

namespace DeadCells.Core
{
    /// <summary>One frame of player intent, independent of the device that produced it.</summary>
    public struct InputFrame
    {
        public float moveX;
        public bool down;
        public bool up;
        public bool jumpPressed;
        public bool jumpHeld;
        public bool primaryPressed;
        public bool primaryHeld;
        public bool secondaryPressed;
        public bool secondaryHeld;
        public bool skill1Pressed;
        public bool skill2Pressed;
        public bool dodgePressed;
        public bool interactPressed;
        public bool flaskPressed;
        public bool mapPressed;
        public bool pausePressed;
        public bool backpackPressed;
    }

    public interface IInputSource
    {
        InputFrame Read();
    }

    /// <summary>
    /// Keyboard + gamepad bindings built in code (no asset dependency).
    /// Keyboard: A/D or arrows move, Space jump, J/LMB primary, K/RMB secondary,
    /// Q/E skills, Shift/L roll, F interact, R flask, Tab/M map, Esc pause,
    /// down + Space drop through / ground slam.
    /// Gamepad: stick/d-pad, South jump, West primary, North secondary, East roll,
    /// LT/RT skills, LB interact, RB flask, Select map, Start pause.
    /// </summary>
    public class GameInput : MonoBehaviour, IInputSource
    {
        InputAction move, jump, primary, secondary, skill1, skill2, dodge, interact, flask, map, pause, backpack;

        /// <summary>When false (menus open) the player receives an empty frame.</summary>
        public static bool GameplayEnabled = true;

        void Awake()
        {
            move = new InputAction("Move", InputActionType.Value);
            move.AddCompositeBinding("2DVector")
                .With("Up", "<Keyboard>/w").With("Down", "<Keyboard>/s")
                .With("Left", "<Keyboard>/a").With("Right", "<Keyboard>/d");
            move.AddCompositeBinding("2DVector")
                .With("Up", "<Keyboard>/upArrow").With("Down", "<Keyboard>/downArrow")
                .With("Left", "<Keyboard>/leftArrow").With("Right", "<Keyboard>/rightArrow");
            move.AddBinding("<Gamepad>/leftStick");
            move.AddBinding("<Gamepad>/dpad");

            jump = Button("Jump", "<Keyboard>/space", "<Gamepad>/buttonSouth");
            primary = Button("Primary", "<Keyboard>/j", "<Mouse>/leftButton", "<Gamepad>/buttonWest");
            secondary = Button("Secondary", "<Keyboard>/k", "<Mouse>/rightButton", "<Gamepad>/buttonNorth");
            skill1 = Button("Skill1", "<Keyboard>/q", "<Gamepad>/leftTrigger");
            skill2 = Button("Skill2", "<Keyboard>/e", "<Gamepad>/rightTrigger");
            dodge = Button("Dodge", "<Keyboard>/leftShift", "<Keyboard>/l", "<Gamepad>/buttonEast");
            interact = Button("Interact", "<Keyboard>/f", "<Gamepad>/leftShoulder");
            flask = Button("Flask", "<Keyboard>/r", "<Gamepad>/rightShoulder");
            map = Button("Map", "<Keyboard>/tab", "<Keyboard>/m", "<Gamepad>/select");
            pause = Button("Pause", "<Keyboard>/escape", "<Gamepad>/start");
            backpack = Button("Backpack", "<Keyboard>/c", "<Gamepad>/rightStickPress");
        }

        static InputAction Button(string name, params string[] paths)
        {
            var a = new InputAction(name, InputActionType.Button);
            foreach (var p in paths)
                a.AddBinding(p);
            return a;
        }

        void OnEnable()
        {
            foreach (var a in All())
                a.Enable();
        }

        void OnDisable()
        {
            foreach (var a in All())
                a.Disable();
        }

        void OnDestroy()
        {
            foreach (var a in All())
                a.Dispose();
        }

        InputAction[] All() => new[] { move, jump, primary, secondary, skill1, skill2, dodge, interact, flask, map, pause, backpack };

        public InputFrame Read()
        {
            if (!GameplayEnabled)
                return default;
            Vector2 m = move.ReadValue<Vector2>();
            return new InputFrame
            {
                moveX = Mathf.Abs(m.x) > 0.25f ? Mathf.Sign(m.x) : 0f,
                down = m.y < -0.5f,
                up = m.y > 0.5f,
                jumpPressed = jump.WasPressedThisFrame(),
                jumpHeld = jump.IsPressed(),
                primaryPressed = primary.WasPressedThisFrame(),
                primaryHeld = primary.IsPressed(),
                secondaryPressed = secondary.WasPressedThisFrame(),
                secondaryHeld = secondary.IsPressed(),
                skill1Pressed = skill1.WasPressedThisFrame(),
                skill2Pressed = skill2.WasPressedThisFrame(),
                dodgePressed = dodge.WasPressedThisFrame(),
                interactPressed = interact.WasPressedThisFrame(),
                flaskPressed = flask.WasPressedThisFrame(),
                mapPressed = map.WasPressedThisFrame(),
                pausePressed = pause.WasPressedThisFrame(),
                backpackPressed = backpack.WasPressedThisFrame(),
            };
        }
    }
}
