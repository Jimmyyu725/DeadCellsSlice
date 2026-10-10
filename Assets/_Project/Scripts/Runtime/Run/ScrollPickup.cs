using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>Scrolls raise power or vitality for the rest of the run.</summary>
    public class ScrollPickup : Interactable
    {
        public bool vitality;
        public Transform display;
        float t;

        public override string Prompt => Loc.Get(vitality ? "hud.scroll_vitality" : "hud.scroll_power");

        void Update()
        {
            t += Time.deltaTime;
            if (display != null)
                display.localPosition = new Vector3(0f, 1.0f + Mathf.Sin(t * 2.5f) * 0.1f, 0f);
        }

        public override void Interact(PlayerController player)
        {
            var run = SaveSystem.Data.run;
            if (vitality)
                run.scrollsVitality++;
            else
                run.scrollsPower++;
            player.RecalculateStats(false);
            Audio.Sfx.Play("pickup.scroll");
            if (vitality)
                player.Health.Heal(player.Health.maxHealth * 0.15f);
            GameHUD.Instance?.Toast(Prompt, vitality ? new Color(0.5f, 1f, 0.6f) : new Color(1f, 0.55f, 0.4f));
            JuiceEngine.Instance?.Embers(transform.position + Vector3.up, 26, vitality ? new Color(0.6f, 3f, 0.8f) : new Color(3f, 0.9f, 0.4f));
            Destroy(gameObject);
        }
    }
}
