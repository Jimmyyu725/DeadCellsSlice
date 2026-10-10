using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// Talkable NPCs: the merchant greets, the Collector sells permanent
    /// upgrades, the Mutator hands out mutations, the Blacksmith upgrades
    /// gear and the Tailor changes outfits.
    /// </summary>
    public class NpcInteractable : Interactable
    {
        public enum Role { Merchant, Collector, Mutator, Blacksmith, Tailor }

        public Role role;
        public Animator animator;

        public override string Prompt => role switch
        {
            Role.Collector => Loc.Get("hud.collector"),
            Role.Mutator => Loc.Get("hud.mutator"),
            Role.Blacksmith => Loc.Get("hud.smith"),
            Role.Tailor => Loc.Get("hud.tailor"),
            _ => Loc.Get("hud.talk"),
        };

        public override void Interact(PlayerController player)
        {
            Audio.Sfx.Play("npc.talk", transform.position + Vector3.up * 1.5f);
            var ui = GameUI.Instance;
            switch (role)
            {
                case Role.Collector: ui?.OpenCollector(); break;
                case Role.Mutator: ui?.OpenMutations(); break;
                case Role.Blacksmith: ui?.OpenBlacksmith(); break;
                case Role.Tailor: ui?.OpenTailor(); break;
                default: ui?.Say(Loc.Get("npc.merchant.name"), Loc.Get("npc.merchant.greet")); break;
            }
        }
    }
}
