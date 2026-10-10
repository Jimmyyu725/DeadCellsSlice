using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>Equipment lying on the ground or on a shop pedestal.</summary>
    public class ItemPickup : Interactable
    {
        public ItemDef item;
        public int price;
        public Transform display;

        GameObject visual;
        float spin;

        public override ItemDef CardItem => item;
        public override int CardPrice => price;
        public override bool CanInteract => item != null;

        public override string Prompt => price > 0 ? Loc.Get("hud.buy", price) : Loc.Get("hud.pickup");

        public void Setup(ItemDef def, int cost)
        {
            item = def;
            price = cost;
            if (visual != null)
                Destroy(visual);
            if (def != null && def.visual != null)
            {
                var parent = display != null ? display : transform;
                visual = Instantiate(def.visual, parent);
                visual.transform.localPosition = Vector3.zero;
                // Show weapons tilted like a trophy; skills/bows upright.
                visual.transform.localRotation = def.kind switch
                {
                    ItemKind.Melee => Quaternion.Euler(0f, 0f, -35f),
                    ItemKind.Shield => Quaternion.Euler(-90f, 0f, 0f), // shield face (+Y) towards the camera
                    _ => Quaternion.identity,
                };
                visual.SetActive(true);
            }
            // The glow takes the quality colour: white, blue (+), violet (++), gold (legendary).
            var glow = GetComponentInChildren<Light>();
            if (glow != null && def != null && def.quality > 0)
            {
                glow.color = ItemForge.QualityColor(def.quality);
                glow.intensity *= def.quality >= ItemForge.Legendary ? 2f : 1.4f;
            }
        }

        float glintAt;

        void Update()
        {
            if (display == null)
                return;
            if (item != null && Time.time >= glintAt)
            {
                bool legendary = item.quality >= ItemForge.Legendary;
                glintAt = Time.time + (legendary ? 0.1f : item.quality > 0 ? 0.3f : 0.7f) * Random.Range(0.7f, 1.3f);
                var juice = JuiceEngine.Instance;
                Color c = ItemForge.QualityColor(item.quality);
                juice?.Glints(display.position, 1, c * (item.quality > 0 ? 3f : 1.6f));
                if (legendary)
                    juice?.Embers(display.position + Vector3.down * 0.9f + (Vector3)Random.insideUnitCircle * 0.4f, 1, new Color(3.4f, 2.6f, 0.8f));
            }
            spin += Time.deltaTime;
            display.localPosition = new Vector3(0f, 1.15f + Mathf.Sin(spin * 2.2f) * 0.08f, 0f);
            display.localRotation = Quaternion.Euler(0f, Mathf.Sin(spin * 0.9f) * 35f, 0f);
        }

        public override void Interact(PlayerController player)
        {
            var run = SaveSystem.Data.run;
            if (price > 0)
            {
                if (run.gold < price)
                {
                    GameHUD.Instance?.Toast(Loc.Get("hud.not_enough_gold"), new Color(1f, 0.5f, 0.4f));
                    Audio.Sfx.Play("ui.error");
                    return;
                }
                RunManager.Instance.SpendGold(price);
                SaveSystem.Data.stats.goldSpent += price;
                Achievements.CheckThresholds();
                GameHUD.Instance?.Toast(Loc.Get("npc.merchant.bought"), UIKit.Gold);
                Audio.Sfx.Play("shop.buy");
            }
            var combat = player.Combat;
            if (item.quality >= ItemForge.Legendary)
                Achievements.Unlock("legendary");
            ItemDef old;
            if (item.kind == ItemKind.Amulet)
                old = combat.EquipAmulet(item);
            else
                old = combat.Equip(combat.SlotFor(item), item);
            Audio.Sfx.Play("pickup.item");
            JuiceEngine.Instance?.Embers(transform.position + Vector3.up * 1.1f, 16, item.arcColor);
            if (old != null)
            {
                Setup(old, 0);
            }
            else
            {
                Destroy(gameObject);
            }
            price = 0;
        }
    }
}
