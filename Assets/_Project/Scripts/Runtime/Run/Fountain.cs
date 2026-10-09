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
    /// <summary>Refills the flask once per visit (Boss Cells reduce the refill).</summary>
    public class Fountain : Interactable
    {
        public ParticleSystem water;
        bool used;

        public override string Prompt => used ? Loc.Get("hud.fountain_used") : Loc.Get("hud.fountain");
        public override bool CanInteract => true;

        public override void Interact(PlayerController player)
        {
            if (used)
            {
                GameHUD.Instance?.Toast(Loc.Get("npc.fountain.text"), UIKit.TextDim);
                return;
            }
            used = true;
            var run = SaveSystem.Data.run;
            int max = RunManager.MaxFlaskCharges;
            run.flaskCharges = Mathf.Max(run.flaskCharges, Mathf.RoundToInt(max * Difficulty.FountainRefill));
            player.Health.Heal(player.Health.maxHealth * 0.25f * Difficulty.FountainRefill);
            GameHUD.Instance?.Toast(Loc.Get("hud.flask_refill"), new Color(0.6f, 1f, 0.7f));
            JuiceEngine.Instance?.Embers(transform.position + Vector3.up, 30, new Color(1.6f, 0.8f, 3.2f));
            if (water != null)
            {
                var e = water.emission;
                e.rateOverTime = 2f;
            }
        }
    }
}
