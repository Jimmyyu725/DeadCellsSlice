using System.Collections;
using DeadCells.FX;
using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// Timed vault near a biome exit: it opens only if the player reaches it
    /// before the run clock passes its limit (the clock hand counts down),
    /// then pours out gold, cells and a high-quality item.
    /// </summary>
    public class TimedDoor : Interactable
    {
        public Transform leafLeft, leafRight, hand;
        public Light glow;
        public float limit = 120f;
        bool opened;

        float Remaining => limit - SaveSystem.Data.run.time;
        bool Expired => Remaining <= 0f;

        public override bool CanInteract => !opened;

        public override string Prompt => Expired
            ? Loc.Get("hud.timed_sealed")
            : Loc.Get("hud.timed_open", UIKit.FormatTime(Remaining));

        public static float LimitFor(int depth) => (2f + 4f * depth) * 60f;

        public override void Interact(PlayerController player)
        {
            if (opened)
                return;
            if (Expired)
            {
                Audio.Sfx.Play("ui.error");
                return;
            }
            opened = true;
            Achievements.Unlock("timed_door");
            StartCoroutine(Open());
        }

        void Update()
        {
            if (hand != null && !opened)
            {
                // One full turn of the hand = the whole limit; it rests at 12 when sealed.
                float f = Mathf.Clamp01(Remaining / Mathf.Max(1f, limit));
                hand.localRotation = Quaternion.Euler(0f, 0f, -360f * (1f - f));
            }
            if (glow != null)
                glow.intensity = Mathf.MoveTowards(glow.intensity, Expired && !opened ? 0f : 2f, Time.deltaTime * 2f);
        }

        IEnumerator Open()
        {
            var juice = JuiceEngine.Instance;
            Audio.Sfx.Play("door.open", transform.position);
            juice?.Shake(Vector2.up, 0.3f);
            float t = 0f;
            while (t < 0.8f)
            {
                t += Time.deltaTime;
                float k = Mathf.SmoothStep(0f, 1f, t / 0.8f);
                if (leafLeft != null)
                    leafLeft.localRotation = Quaternion.Euler(0f, -100f * k, 0f);
                if (leafRight != null)
                    leafRight.localRotation = Quaternion.Euler(0f, 100f * k, 0f);
                yield return null;
            }
            var rm = RunManager.Instance;
            int depth = rm != null ? rm.BiomeDepth : 0;
            Vector3 mouth = transform.position + Vector3.up * 1.2f;
            juice?.Embers(mouth, 50, new Color(3.4f, 2.6f, 0.9f));
            Loot.DropGold(mouth, Mathf.RoundToInt(Random.Range(150, 220) * (1f + 0.6f * depth) * Difficulty.RewardMultiplier));
            Loot.DropCells(mouth, 10 + 4 * depth);
            Loot.DropRandomItem(mouth + Vector3.right * 1.2f, depth + 2);
            Loot.DropScroll(mouth + Vector3.left * 1.2f);
            GameHUD.Instance?.Toast(Loc.Get("hud.timed_reward"), UIKit.Gold);
        }
    }
}
