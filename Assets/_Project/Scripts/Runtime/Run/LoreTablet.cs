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
    public class LoreTablet : Interactable
    {
        public string loreId;
        public Light glow;

        bool Unread => !SaveSystem.Data.meta.loreRead.Contains(loreId);

        /// <summary>Cells for the first reading: more the deeper the area.</summary>
        static int RewardCells => 8 + 4 * (RunManager.Instance != null ? RunManager.Instance.BiomeDepth : 0);

        public override string Prompt => Unread ? Loc.Get("hud.read_new", RewardCells) : Loc.Get("hud.read");

        void Start()
        {
            if (glow != null && SaveSystem.Data.meta.loreRead.Contains(loreId))
                glow.intensity *= 0.35f;
        }

        public override void Interact(PlayerController player)
        {
            var meta = SaveSystem.Data.meta;
            Audio.Sfx.Play("lore.read");
            if (!meta.loreRead.Contains(loreId))
            {
                meta.loreRead.Add(loreId);
                Reward(meta);
                SaveSystem.Save();
            }
            if (glow != null)
                glow.intensity *= 0.35f;
            GameUI.Instance?.ShowLore(loreId);
        }

        /// <summary>
        /// First reading pays out: cells for every tablet, a Scroll of Power for
        /// finishing an area's set, and the Chronicler outfit for all of them.
        /// </summary>
        void Reward(MetaProgress meta)
        {
            Vector3 at = transform.position + Vector3.up * 1.2f;
            int cells = RewardCells;
            Loot.DropCells(at, cells);
            JuiceEngine.Instance?.Glints(at, 8, new Color(0.8f, 2.2f, 3.4f));
            GameHUD.Instance?.Toast(Loc.Get("hud.lore_reward", cells), UIKit.CellBlue);
            var biome = RunManager.Instance != null ? RunManager.Instance.Current : null;
            if (biome != null && biome.lore.Length > 0 && System.Array.TrueForAll(biome.lore, id => meta.loreRead.Contains(id)))
            {
                // The last unread tablet of the area: this happens exactly once per area.
                Loot.DropScroll(at + Vector3.right * 1.2f);
                GameHUD.Instance?.Toast(Loc.Get("hud.lore_set"), new Color(1f, 0.8f, 0.5f));
                Audio.Sfx.Play("pickup.scroll");
            }
            if (meta.loreRead.Count >= RunManager.TotalLore)
            {
                Achievements.Unlock("lore_all");
                Outfits.Grant("lore_all");
            }
        }
    }
}
