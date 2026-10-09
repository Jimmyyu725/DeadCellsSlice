using System.Collections.Generic;
using UnityEngine;

namespace DeadCells.Core
{
    /// <summary>
    /// Code-driven animation: one Animator state per clip (named after the clip),
    /// no transitions in the controller. Gameplay decides what plays and when,
    /// with explicit cross-fade times (0 for snappy combat cuts).
    ///
    /// Visual hierarchy (built by the editor setup):
    ///   Root (physics) -> Facing (x scale +-1 mirror) -> Squash (feet pivot)
    ///   -> Yaw (3/4 turn towards camera) -> imported model
    /// </summary>
    public class CharacterAnimator : MonoBehaviour
    {
        public Animator animator;
        public Transform facingPivot;
        public Transform yawPivot;
        [Tooltip("Model yaw that shows the character facing +X with its front turned towards the camera.")]
        public float yawFacingRight = -65f;
        public const float FrameRate = 60f;

        readonly Dictionary<string, float> clipLengths = new Dictionary<string, float>();
        string current;
        float speed = 1f;

        public string Current => current;
        public int Facing { get; private set; } = 1;

        void Awake()
        {
            if (animator == null)
                animator = GetComponentInChildren<Animator>();
            if (animator != null && animator.runtimeAnimatorController != null)
            {
                foreach (var clip in animator.runtimeAnimatorController.animationClips)
                    clipLengths[clip.name] = clip.length;
            }
            if (yawPivot != null)
                yawPivot.localRotation = Quaternion.Euler(0f, yawFacingRight, 0f);
        }

        public void SetFacing(int dir)
        {
            if (dir == 0)
                return;
            Facing = dir > 0 ? 1 : -1;
            if (facingPivot != null)
            {
                var s = facingPivot.localScale;
                s.x = Facing;
                facingPivot.localScale = s;
            }
        }

        /// <summary>Play `clip` unless it is already playing (loops keep their phase).</summary>
        public void Play(string clip, float fade = 0.06f)
        {
            if (current == clip)
                return;
            Restart(clip, fade);
        }

        /// <summary>Always (re)start `clip` from `normalizedTime`.</summary>
        public void Restart(string clip, float fade = 0f, float normalizedTime = 0f)
        {
            if (animator == null)
                return;
            current = clip;
            int hash = Animator.StringToHash(clip);
            if (fade <= 0f)
                animator.Play(hash, 0, normalizedTime);
            else
                animator.CrossFadeInFixedTime(hash, fade, 0, normalizedTime * Length(clip));
            animator.Update(0f);
        }

        public void SetSpeed(float s)
        {
            speed = s;
            if (animator != null)
                animator.speed = s;
        }

        public float Speed => speed;

        public float Length(string clip) => clipLengths.TryGetValue(clip, out float l) ? l : 1f;

        public int FrameCount(string clip) => Mathf.RoundToInt(Length(clip) * FrameRate);

        /// <summary>Jump to a Blender-numbered frame (1 = first) of `clip` (used to hold/resume the slam).</summary>
        public void SeekFrame(string clip, float frame)
        {
            float n = Mathf.Clamp01((frame - 1f) / Mathf.Max(1f, FrameCount(clip)));
            Restart(clip, 0f, n);
        }
    }
}
