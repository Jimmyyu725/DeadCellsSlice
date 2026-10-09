using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace DeadCells.Items
{
    /// <summary>All items plus shared pickup/projectile prefabs. Lives at Resources/ItemDatabase.</summary>
    public class ItemDatabase : ScriptableObject
    {
        public List<ItemDef> items = new List<ItemDef>();
        public GameObject coinPrefab;
        public GameObject cellPrefab;
        public GameObject flaskPrefab;
        public GameObject scrollPrefab;
        public GameObject itemDropPrefab;

        static ItemDatabase instance;

        public static ItemDatabase Instance
        {
            get
            {
                if (instance == null)
                    instance = Resources.Load<ItemDatabase>("ItemDatabase");
                return instance;
            }
        }

        public ItemDef Get(string id) => string.IsNullOrEmpty(id) ? null : items.FirstOrDefault(i => i != null && i.id == id);

        public IEnumerable<ItemDef> Unlocked() => items.Where(i => i != null && i.IsUnlocked);

        public IEnumerable<ItemDef> Locked() => items.Where(i => i != null && !i.IsUnlocked);
    }
}
