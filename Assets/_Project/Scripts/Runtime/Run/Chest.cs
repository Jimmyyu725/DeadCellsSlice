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
    /// <summary>
    /// Treasure chest: gold burst plus an item, scroll or blueprint. A cursed
    /// chest (chains + skull padlock) pays far better but curses the run: the
    /// next hit taken before `CurseKills` kills is fatal.
    /// </summary>
    public class Chest : Interactable
    {
        public Transform lid;
        public Light glow;
        public bool cursed;
        public GameObject shroud;
        bool opened;

        public const int CurseKills = 10;

        public override bool CanInteract => !opened;
        public override string Prompt => cursed ? Loc.Get("hud.open_cursed", CurseKills) : Loc.Get("hud.open_chest");

        /// <summary>Turn this chest into a cursed one (LevelBuilder, before the player arrives).</summary>
        public void Curse(GameObject shroudPrefab)
        {
            cursed = true;
            if (shroudPrefab != null)
            {
                shroud = Instantiate(shroudPrefab, transform);
                shroud.transform.localPosition = Vector3.zero;
            }
            if (glow != null)
                glow.color = new Color(0.75f, 0.4f, 1f);
            // A sickly violet cast on the wood so the chest reads as cursed at a glance.
            var block = new MaterialPropertyBlock();
            foreach (var r in GetComponentsInChildren<Renderer>())
            {
                if (shroud != null && r.transform.IsChildOf(shroud.transform))
                    continue;
                r.GetPropertyBlock(block);
                block.SetColor("_BaseColor", new Color(0.8f, 0.55f, 1.05f));
                r.SetPropertyBlock(block);
            }
        }

        float nextEmber;

        void Update()
        {
            if (!cursed || opened || Time.time < nextEmber)
                return;
            nextEmber = Time.time + 0.25f;
            JuiceEngine.Instance?.Embers(transform.position + new Vector3(Random.Range(-0.5f, 0.5f), 0.3f, -0.4f), 2, new Color(2.2f, 0.8f, 3.4f));
        }

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
            if (cursed)
            {
                OpenCursed(rm, mouth);
                yield break;
            }
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
            if (Random.value < 0.15f)
                Loot.DropAmulet(mouth + Vector3.left * 1.4f, rm.BiomeDepth);
        }

        void OpenCursed(RunManager rm, Vector3 mouth)
        {
            var juice = JuiceEngine.Instance;
            if (shroud != null)
            {
                juice?.Embers(shroud.transform.position + Vector3.up * 0.4f, 60, new Color(2.2f, 0.9f, 3.4f));
                Destroy(shroud);
            }
            Audio.Sfx.Play("curse", transform.position);
            int depth = rm != null ? rm.BiomeDepth : 0;
            Loot.DropGold(mouth, Mathf.RoundToInt(Random.Range(120, 180) * (1f + 0.6f * depth) * Difficulty.RewardMultiplier));
            Loot.DropRandomItem(mouth + Vector3.right * 0.8f, depth + 2);
            Loot.DropScroll(mouth + Vector3.left * 0.8f);
            Loot.DropCells(mouth, 8);
            if (Random.value < 0.5f)
                Loot.DropAmulet(mouth + Vector3.left * 1.6f, depth + 1);
            var run = SaveSystem.Data.run;
            run.curse = CurseKills;
            Achievements.Unlock("cursed_chest");
            GameHUD.Instance?.Toast(Loc.Get("hud.cursed", CurseKills), new Color(0.85f, 0.45f, 1f));
        }
    }
}
