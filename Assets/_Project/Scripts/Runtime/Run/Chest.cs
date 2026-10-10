using System.Collections;
using System.Collections.Generic;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>Treasure chest: gold burst plus an item, scroll or blueprint.</summary>
    public class Chest : Interactable
    {
        public Transform lid;
        public Light glow;
        bool opened;

        public override bool CanInteract => !opened;
        public override string Prompt => Loc.Get("hud.open_chest");

        public override void Interact(PlayerController player)
        {
            if (opened)
                return;
            opened = true;
            StartCoroutine(Open());
        }

        IEnumerator Open()
        {
            var juice = JuiceEngine.Instance;
            Audio.Sfx.Play("chest.open", transform.position);
            juice?.Shake(Vector2.up, 0.2f);
            juice?.HitStop(0.05f);
            float t = 0f;
            while (t < 0.35f)
            {
                t += Time.deltaTime;
                if (lid != null)
                    lid.localRotation = Quaternion.Euler(Mathf.Lerp(0f, 105f, Mathf.SmoothStep(0f, 1f, t / 0.35f)), 0f, 0f);
                yield return null;
            }
            if (glow != null)
                glow.enabled = false;
            var rm = RunManager.Instance;
            Vector3 mouth = transform.position + Vector3.up * 1.0f;
            juice?.Embers(mouth, 30, new Color(3f, 2.2f, 0.8f));
            Loot.DropGold(mouth, Mathf.RoundToInt(Random.Range(40, 80) * (1f + 0.6f * rm.BiomeDepth) * Difficulty.RewardMultiplier));
            float roll = Random.value;
            if (roll < 0.55f)
                Loot.DropRandomItem(mouth + Vector3.right * 0.8f, rm.BiomeDepth);
            else if (roll < 0.85f)
                Loot.DropScroll(mouth + Vector3.right * 0.8f);
            else
                Loot.DropCells(mouth, 6);
            if (Random.value < 0.25f)
                Loot.DropBlueprint(mouth + Vector3.left * 0.8f);
        }
    }
}
