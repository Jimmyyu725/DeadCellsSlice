using DeadCells.FX;
using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>A floating rune tablet dropped by a rune guardian.</summary>
    public class RunePickup : Interactable
    {
        public string rune;
        public Transform display;
        float t;

        public override string Prompt => Loc.Get("hud.rune_take", Loc.Get($"rune.{rune}.name"));

        void Update()
        {
            t += Time.deltaTime;
            if (display != null)
            {
                display.localPosition = new Vector3(0f, 1.2f + Mathf.Sin(t * 2f) * 0.12f, 0f);
                display.localRotation = Quaternion.Euler(0f, Mathf.Sin(t * 0.9f) * 25f, 0f);
            }
            if (Random.value < Time.deltaTime * 8f)
                JuiceEngine.Instance?.Embers(transform.position + Vector3.up * 1.2f + (Vector3)Random.insideUnitCircle * 0.4f, 1, Runes.ColorOf(rune));
        }

        public override void Interact(PlayerController player)
        {
            Runes.Grant(rune);
            Audio.Sfx.Play("pickup.blueprint");
            JuiceEngine.Instance?.Embers(transform.position + Vector3.up * 1.2f, 50, Runes.ColorOf(rune));
            GameHUD.Instance?.ShowTitle(Loc.Get($"rune.{rune}.name"), Loc.Get($"rune.{rune}.desc"), Runes.ColorOf(rune) / 3f);
            Destroy(gameObject);
        }

        public static RunePickup Spawn(string rune, Vector3 at)
        {
            var w = WorldPrefabs.Instance;
            var prefab = rune == Runes.Vine ? w.runeVine : rune == Runes.Ram ? w.runeRam : w.runeSpider;
            if (prefab == null)
                return null;
            var go = Instantiate(prefab, new Vector3(at.x, Mathf.Floor(at.y + 0.1f), 0.3f), Quaternion.identity,
                RunManager.Instance != null ? RunManager.Instance.EntityParent : null);
            var p = go.GetComponent<RunePickup>();
            p.rune = rune;
            return p;
        }
    }
}
