using UnityEngine;

namespace DeadCells.FX
{
    /// <summary>
    /// Procedural squash &amp; stretch on a visual pivot placed at the feet.
    /// Punches spring back to rest with a critically-damped overshoot.
    /// Scale is volume-preserving-ish: callers pass (width, height).
    /// </summary>
    public class SquashStretch : MonoBehaviour
    {
        [Tooltip("Spring stiffness of the recovery.")]
        public float stiffness = 420f;
        [Tooltip("Damping ratio (<1 overshoots, giving a wobble).")]
        public float dampingRatio = 0.45f;

        Vector2 offset;     // current deviation from (1,1)
        Vector2 velocity;

        public void Punch(Vector2 scale)
        {
            offset = scale - Vector2.one;
            velocity = Vector2.zero;
            Apply();
        }

        /// <summary>Adds to the current deformation instead of replacing it.</summary>
        public void Add(Vector2 delta)
        {
            offset += delta;
            Apply();
        }

        void LateUpdate()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f)
                return;
            float damping = 2f * dampingRatio * Mathf.Sqrt(stiffness);
            Vector2 accel = -stiffness * offset - damping * velocity;
            velocity += accel * dt;
            offset += velocity * dt;
            if (offset.sqrMagnitude < 1e-7f && velocity.sqrMagnitude < 1e-6f)
            {
                offset = Vector2.zero;
                velocity = Vector2.zero;
            }
            Apply();
        }

        void Apply()
        {
            float sx = Mathf.Max(0.2f, 1f + offset.x);
            float sy = Mathf.Max(0.2f, 1f + offset.y);
            transform.localScale = new Vector3(sx, sy, sx);
        }
    }
}
