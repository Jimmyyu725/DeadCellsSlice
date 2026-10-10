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

        public override string Prompt => Loc.Get("hud.read");

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
                SaveSystem.Save();
                if (meta.loreRead.Count >= RunManager.TotalLore)
                    Achievements.Unlock("lore_all");
            }
            if (glow != null)
                glow.intensity *= 0.35f;
            GameUI.Instance?.ShowLore(loreId);
        }
    }
}
