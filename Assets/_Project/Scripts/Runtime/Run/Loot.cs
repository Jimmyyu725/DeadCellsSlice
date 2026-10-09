using System.Collections.Generic;
using System.Linq;
using DeadCells.Items;
using DeadCells.Meta;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>Drops (gold, cells, items, scrolls, blueprints) and shop stock.</summary>
    public static class Loot
    {
        static WorldPrefabs W => WorldPrefabs.Instance;
        static Transform Parent => RunManager.Instance != null ? RunManager.Instance.EntityParent : null;

        public static void DropGold(Vector3 pos, int amount) => SpawnCurrency(W.gold, CurrencyPickup.Kind.Gold, pos, amount, Mathf.Clamp(amount / 12, 2, 10));

        public static void DropCells(Vector3 pos, int count) => SpawnCurrency(W.cell, CurrencyPickup.Kind.Cell, pos, count, count);

        public static void SpawnGoldPile(Vector3 pos, int amount, Transform parent) =>
            SpawnCurrency(W.gold, CurrencyPickup.Kind.Gold, pos, amount, Mathf.Clamp(amount / 10, 3, 8), parent, 0.4f);

        static void SpawnCurrency(GameObject prefab, CurrencyPickup.Kind kind, Vector3 pos, int amount, int pieces, Transform parent = null, float speed = 1f)
        {
            if (prefab == null || amount <= 0)
                return;
            pieces = Mathf.Max(1, Mathf.Min(pieces, amount));
            int each = amount / pieces, rest = amount - each * pieces;
            for (int i = 0; i < pieces; i++)
            {
                var go = Object.Instantiate(prefab, pos, Quaternion.identity, parent != null ? parent : Parent);
                go.SetActive(true);
                var c = go.GetComponent<CurrencyPickup>();
                c.kind = kind;
                c.amount = each + (i < rest ? 1 : 0);
                c.Launch(new Vector2(Random.Range(-3.5f, 3.5f), Random.Range(5f, 9f)) * speed);
            }
        }

        static IEnumerable<ItemDef> Pool(bool skills, int depth)
        {
            var db = ItemDatabase.Instance;
            if (db == null)
                return Enumerable.Empty<ItemDef>();
            int maxTier = Mathf.Clamp(1 + depth / 2 + 1, 1, 3);
            return db.Unlocked().Where(i => i.tier <= maxTier && (skills ? i.kind == ItemKind.Skill : i.kind != ItemKind.Skill));
        }

        public static ItemDef RandomItem(int depth, System.Random rng = null)
        {
            bool skill = (rng != null ? rng.NextDouble() : Random.value) < 0.4;
            var pool = Pool(skill, depth).ToList();
            if (pool.Count == 0)
                pool = Pool(!skill, depth).ToList();
            if (pool.Count == 0)
                return null;
            return pool[rng != null ? rng.Next(pool.Count) : Random.Range(0, pool.Count)];
        }

        public static void DropRandomItem(Vector3 pos, int depth)
        {
            var item = RandomItem(depth);
            if (item == null || W.itemDrop == null)
                return;
            var go = Object.Instantiate(W.itemDrop, pos, Quaternion.identity, Parent);
            go.transform.position = new Vector3(pos.x, Mathf.Floor(pos.y), 0.3f);
            go.GetComponent<ItemPickup>().Setup(item, 0);
            SnapToFloor(go.transform);
        }

        public static void DropScroll(Vector3 pos)
        {
            if (W.scroll == null)
                return;
            var go = Object.Instantiate(W.scroll, pos, Quaternion.identity, Parent);
            go.GetComponent<ScrollPickup>().vitality = Random.value < 0.5f;
            SnapToFloor(go.transform);
        }

        /// <summary>Blueprint for a random locked item the player has not found yet.</summary>
        public static bool DropBlueprint(Vector3 pos)
        {
            var db = ItemDatabase.Instance;
            if (db == null || W.blueprint == null)
                return false;
            var meta = SaveSystem.Data.meta;
            var candidates = db.Locked().Where(i => !meta.blueprints.Contains(i.id)).ToList();
            if (candidates.Count == 0)
                return false;
            var go = Object.Instantiate(W.blueprint, pos, Quaternion.identity, Parent);
            go.GetComponent<BlueprintPickup>().itemId = candidates[Random.Range(0, candidates.Count)].id;
            SnapToFloor(go.transform);
            return true;
        }

        static void SnapToFloor(Transform t)
        {
            var hit = Physics2D.Raycast((Vector2)t.position + Vector2.up * 0.5f, Vector2.down, 20f, Core.DCLayers.GroundMask);
            if (hit.collider != null)
                t.position = new Vector3(t.position.x, hit.point.y, t.position.z);
        }

        public static List<(ItemDef item, int price)> ShopStock(System.Random rng, int depth)
        {
            var list = new List<(ItemDef, int)>();
            var db = ItemDatabase.Instance;
            if (db == null)
                return list;
            // Never offer what the player already carries.
            var run = SaveSystem.Data.run;
            var carried = new HashSet<string> { run.primary, run.secondary, run.skill1, run.skill2 };
            var pool = db.Unlocked().Where(i => !carried.Contains(i.id) && (i.kind != ItemKind.Shield || rng.NextDouble() < 0.6))
                .OrderBy(_ => rng.Next()).Take(3).ToList();
            foreach (var item in pool)
                list.Add((item, Mathf.RoundToInt(item.PriceFor(depth) / Mathf.Max(0.5f, Difficulty.RewardMultiplier))));
            return list;
        }
    }
}
