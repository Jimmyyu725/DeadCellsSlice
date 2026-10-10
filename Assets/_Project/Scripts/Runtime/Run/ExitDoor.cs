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
    /// <summary>Door to the next area (biome exit or passage exit).</summary>
    public class ExitDoor : Interactable
    {
        public Transform leaf;
        public Transform leafRight;
        public bool locked;
        /// <summary>Branch door in a passage: leads to the variant biome, sealed without its rune.</summary>
        public bool variant;
        public string requiredRune = "";

        bool Sealed => variant && !string.IsNullOrEmpty(requiredRune) && !Runes.Has(requiredRune);

        public override bool CanInteract => true;

        public override string Prompt
        {
            get
            {
                if (locked)
                    return Loc.Get("hud.door_locked");
                if (Sealed)
                    return Loc.Get("hud.need_rune", Loc.Get($"rune.{requiredRune}.name"));
                if (variant && RunManager.Instance?.VariantAhead != null)
                    return Loc.Get("hud.enter_variant", RunManager.Instance.VariantAhead.DisplayName);
                return Loc.Get("hud.enter");
            }
        }

        public override void Interact(PlayerController player)
        {
            if (locked)
                return;
            if (Sealed)
            {
                Audio.Sfx.Play("ui.error");
                return;
            }
            Audio.Sfx.Play("door.open", transform.position);
            RunManager.Instance.ExitReached(variant);
        }

        void Update()
        {
            // Unlocked doors stand ajar, light spilling through.
            bool shut = locked || Sealed;
            if (leaf != null)
                leaf.localRotation = Quaternion.Slerp(leaf.localRotation, Quaternion.Euler(0f, shut ? 0f : 55f, 0f), Time.deltaTime * 3f);
            if (leafRight != null)
                leafRight.localRotation = Quaternion.Slerp(leafRight.localRotation, Quaternion.Euler(0f, shut ? 0f : -55f, 0f), Time.deltaTime * 3f);
        }
    }
}
