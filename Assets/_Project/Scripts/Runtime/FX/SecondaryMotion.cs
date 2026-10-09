using System.Collections.Generic;
using UnityEngine;

namespace DeadCells.FX
{
    /// <summary>
    /// Lightweight spring bones layered on top of the baked animation, for the
    /// scarf and tunic tails. Each simulated tip is pulled towards its animated
    /// target, carries inertia and gravity, and is length-constrained; the bone
    /// is then rotated to point at it. Runs on scaled time (freezes in hit-stop).
    /// </summary>
    [DefaultExecutionOrder(200)]
    public class SecondaryMotion : MonoBehaviour
    {
        [System.Serializable]
        public class Chain
        {
            public string name;
            public Transform[] bones;
            [Range(0f, 1f)] public float stiffness = 0.12f;
            [Range(0f, 1f)] public float damping = 0.82f;
            public float gravity = 4f;
            [Range(0f, 1f)] public float inheritBody = 0.6f;
        }

        public List<Chain> chains = new List<Chain>();
        [Tooltip("Snap the simulation back to the pose if anything moves further than this in one frame.")]
        public float teleportDistance = 2f;

        class State
        {
            public Vector3[] curr, prev;
            public Vector3[] localTip;   // tip offset in each bone's local space
            public float[] length;
        }

        readonly List<State> states = new List<State>();
        Vector3 lastRoot;
        float lastFacingSign = 1f;

        void Start()
        {
            states.Clear();
            foreach (var c in chains)
            {
                int n = c.bones.Length;
                var s = new State
                {
                    curr = new Vector3[n],
                    prev = new Vector3[n],
                    localTip = new Vector3[n],
                    length = new float[n],
                };
                for (int i = 0; i < n; i++)
                {
                    Transform b = c.bones[i];
                    Vector3 tipWorld = i + 1 < n
                        ? c.bones[i + 1].position
                        : b.position + (b.position - c.bones[Mathf.Max(0, i - 1)].position).normalized * 0.12f;
                    s.localTip[i] = b.InverseTransformPoint(tipWorld);
                    s.length[i] = Vector3.Distance(b.position, tipWorld);
                    s.curr[i] = s.prev[i] = tipWorld;
                }
                states.Add(s);
            }
            lastRoot = transform.position;
            lastFacingSign = Mathf.Sign(transform.lossyScale.x);
        }

        public void ResetPose()
        {
            for (int ci = 0; ci < chains.Count && ci < states.Count; ci++)
            {
                var c = chains[ci];
                var s = states[ci];
                for (int i = 0; i < c.bones.Length; i++)
                    s.curr[i] = s.prev[i] = c.bones[i].TransformPoint(s.localTip[i]);
            }
        }

        void LateUpdate()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f || states.Count != chains.Count)
                return;
            float facing = Mathf.Sign(transform.lossyScale.x);
            if ((transform.position - lastRoot).sqrMagnitude > teleportDistance * teleportDistance || facing != lastFacingSign)
                ResetPose();
            lastRoot = transform.position;
            lastFacingSign = facing;

            float frameScale = dt * 60f;
            for (int ci = 0; ci < chains.Count; ci++)
            {
                var c = chains[ci];
                var s = states[ci];
                for (int i = 0; i < c.bones.Length; i++)
                {
                    Transform b = c.bones[i];
                    Vector3 animTip = b.TransformPoint(s.localTip[i]);
                    Vector3 vel = (s.curr[i] - s.prev[i]) * Mathf.Pow(c.damping, frameScale);
                    s.prev[i] = s.curr[i];
                    Vector3 next = s.curr[i] + vel + Vector3.down * (c.gravity * dt * dt);
                    next = Vector3.Lerp(next, animTip, 1f - Mathf.Pow(1f - c.stiffness, frameScale));
                    Vector3 dir = next - b.position;
                    if (dir.sqrMagnitude < 1e-8f)
                        continue;
                    next = b.position + dir.normalized * s.length[i];
                    s.curr[i] = next;
                    Quaternion delta = Quaternion.FromToRotation(animTip - b.position, next - b.position);
                    b.rotation = delta * b.rotation;
                }
            }
        }
    }
}
