using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>Blueprint dropped by elites and bosses; picked up on touch.</summary>
    public class BlueprintPickup : MonoBehaviour
    {
        public string itemId;
        float t;

        void Update()
        {
            t += Time.deltaTime;
            transform.GetChild(0).localPosition = new Vector3(0f, 0.8f + Mathf.Sin(t * 3f) * 0.12f, 0f);
            var p = PlayerController.Main;
            if (p == null || t < 0.6f)
                return;
            if (Vector2.Distance(p.transform.position + Vector3.up, transform.position + Vector3.up * 0.8f) < 1.3f)
            {
                var meta = SaveSystem.Data.meta;
                var def = ItemDatabase.Instance != null ? ItemDatabase.Instance.Get(itemId) : null;
                if (def != null && !def.IsUnlocked && !meta.blueprints.Contains(itemId))
                {
                    meta.blueprints.Add(itemId);
                    SaveSystem.Save();
                    GameHUD.Instance?.Toast(Loc.Get("hud.blueprint", def.DisplayName), UIKit.CellBlue);
                }
                JuiceEngine.Instance?.Embers(transform.position + Vector3.up, 20, new Color(0.6f, 1.8f, 3f));
                Audio.Sfx.Play("pickup.blueprint");
                Destroy(gameObject);
            }
        }
    }
}
