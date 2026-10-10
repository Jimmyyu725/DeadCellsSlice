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

        public override bool CanInteract => true;
        public override string Prompt => locked ? Loc.Get("hud.door_locked") : Loc.Get("hud.enter");

        public override void Interact(PlayerController player)
        {
            if (locked)
                return;
            Audio.Sfx.Play("door.open", transform.position);
            RunManager.Instance.ExitReached();
        }

        void Update()
        {
            // Unlocked doors stand ajar, light spilling through.
            if (leaf != null)
                leaf.localRotation = Quaternion.Slerp(leaf.localRotation, Quaternion.Euler(0f, locked ? 0f : 55f, 0f), Time.deltaTime * 3f);
            if (leafRight != null)
                leafRight.localRotation = Quaternion.Slerp(leafRight.localRotation, Quaternion.Euler(0f, locked ? 0f : -55f, 0f), Time.deltaTime * 3f);
        }
    }
}
