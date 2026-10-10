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
    /// Scroll of Power: offers two of the three colours (Brutality, Tactics,
    /// Survival); the chosen stat raises the damage of items of that colour and
    /// the player's health for the rest of the run.
    /// </summary>
    public class ScrollPickup : Interactable
    {
        [Tooltip("Legacy flag from the two-scroll era; ignored.")]
        public bool vitality;
        public Transform display;
        float t;
        ItemColor a, b;

        public override string Prompt => Loc.Get("hud.scroll_choose");

        void Start()
        {
            var colors = new[] { ItemColor.Brutality, ItemColor.Tactics, ItemColor.Survival };
            int skip = Random.Range(0, 3);
            a = colors[(skip + 1) % 3];
            b = colors[(skip + 2) % 3];
        }

        void Update()
        {
            t += Time.deltaTime;
            if (display != null)
                display.localPosition = new Vector3(0f, 1.0f + Mathf.Sin(t * 2.5f) * 0.1f, 0f);
        }

        public static Color Tint(ItemColor c) => c switch
        {
            ItemColor.Brutality => new Color(3f, 0.7f, 0.4f),
            ItemColor.Tactics => new Color(1.8f, 0.8f, 3.2f),
            _ => new Color(0.6f, 3f, 0.8f),
        };

        public override void Interact(PlayerController player)
        {
            if (GameUI.Instance == null)
            {
                Apply(player, a);
                return;
            }
            GameUI.Instance.ChooseScroll(a, b, c => Apply(player, c));
        }

        public void Apply(PlayerController player, ItemColor c)
        {
            if (this == null)
                return;
            var run = SaveSystem.Data.run;
            if (c == ItemColor.Brutality) run.brutality++;
            else if (c == ItemColor.Tactics) run.tactics++;
            else run.survival++;
            player.RecalculateStats(false);
            player.Health.Heal(player.Health.maxHealth * (c == ItemColor.Survival ? 0.2f : 0.1f));
            Audio.Sfx.Play("pickup.scroll");
            GameHUD.Instance?.Toast(Loc.Get("hud.scroll_taken", Loc.Get("color." + c.ToString().ToLowerInvariant())), Tint(c) / 3f);
            JuiceEngine.Instance?.Embers(transform.position + Vector3.up, 26, Tint(c));
            Destroy(gameObject);
        }
    }
}
