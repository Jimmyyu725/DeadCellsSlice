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
        public bool attackPressed;
        public bool dodgePressed;
        public bool shieldPressed;
        public bool shieldHeld;
        public bool swapWeaponPressed;
        public bool cycleFlamePressed;
    }

    public interface IInputSource
    {
        InputFrame Read();
    }

    /// <summary>
    /// Keyboard + gamepad bindings built in code (no asset dependency).
    /// Keyboard: A/D or arrows move, Space jump, J or LMB attack, Shift or K dodge,
    /// L or RMB shield, S + Space ground pound, Q swap weapon, F cycle flame colour.
    /// Gamepad: stick/d-pad, South jump, West attack, East/RT dodge, LB/LT shield,
    /// down + South ground pound, North swap, Select cycle flame.
    /// </summary>
    public class GameInput : MonoBehaviour, IInputSource
    {
        InputAction move, jump, attack, dodge, shield, swap, flame;

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
            attack = Button("Attack", "<Keyboard>/j", "<Mouse>/leftButton", "<Gamepad>/buttonWest");
            dodge = Button("Dodge", "<Keyboard>/leftShift", "<Keyboard>/k", "<Gamepad>/buttonEast", "<Gamepad>/rightTrigger");
            shield = Button("Shield", "<Keyboard>/l", "<Mouse>/rightButton", "<Gamepad>/leftShoulder", "<Gamepad>/leftTrigger");
            swap = Button("Swap", "<Keyboard>/q", "<Gamepad>/buttonNorth");
            flame = Button("Flame", "<Keyboard>/f", "<Gamepad>/select");
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

        InputAction[] All() => new[] { move, jump, attack, dodge, shield, swap, flame };

        public InputFrame Read()
        {
            Vector2 m = move.ReadValue<Vector2>();
            return new InputFrame
            {
                moveX = Mathf.Abs(m.x) > 0.25f ? Mathf.Sign(m.x) : 0f,
                down = m.y < -0.5f,
                up = m.y > 0.5f,
                jumpPressed = jump.WasPressedThisFrame(),
                jumpHeld = jump.IsPressed(),
                attackPressed = attack.WasPressedThisFrame(),
                dodgePressed = dodge.WasPressedThisFrame(),
                shieldPressed = shield.WasPressedThisFrame(),
                shieldHeld = shield.IsPressed(),
                swapWeaponPressed = swap.WasPressedThisFrame(),
                cycleFlamePressed = flame.WasPressedThisFrame(),
            };
        }
    }
}
