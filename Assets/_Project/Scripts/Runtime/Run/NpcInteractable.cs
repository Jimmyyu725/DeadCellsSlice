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
    /// <summary>NPC that talks when used (Merchant) or opens a screen (Collector).</summary>
    public class NpcInteractable : Interactable
    {
        public enum Role { Merchant, Collector }

        public Role role;
        public Animator animator;

        public override string Prompt => role == Role.Collector ? Loc.Get("hud.collector") : Loc.Get("hud.talk");

        public override void Interact(PlayerController player)
        {
            if (role == Role.Collector)
                GameUI.Instance?.OpenCollector();
            else
                GameUI.Instance?.Say(Loc.Get("npc.merchant.name"), Loc.Get("npc.merchant.greet"));
        }
    }
}
