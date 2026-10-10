using System.Collections.Generic;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// Everything the runtime generator needs for one area: the kit (tile
    /// meshes by role, decor prefabs), atmosphere, enemy pools and story keys.
    /// Built by the editor from the Blender biome manifests.
    /// </summary>
    [CreateAssetMenu(menuName = "Dead Cells/Biome")]
    public class BiomeDef : ScriptableObject
    {
        [System.Serializable]
        public class TileModule
        {
            public string role;
            public Mesh mesh;
            public Matrix4x4 matrix = Matrix4x4.identity;
        }

        [System.Serializable]
        public class EnemyEntry
        {
            public GameObject prefab;
            public float weight = 1f;
        }

        public enum Placement
        {
            FarBackground,   // z 10-16, below/behind the level
            MidBackground,   // z 4-6
            Floating,        // hangs in open air, z 3-6
            WallMounted,     // against the back wall, z ~2.3
            Floor,           // on the floor, z 0.8-1.6
            Ceiling,         // hangs from ceilings, z 0.5-1.5
            UnderPlatform,   // stilts under one-way platforms
        }

        [System.Serializable]
        public class Decor
        {
            public GameObject prefab;
            public Placement placement;
            [Tooltip("Instances per 100 m of level width.")]
            public float density = 2f;
            public Vector2 scale = Vector2.one;
            public Vector2 z = new Vector2(1f, 2f);
            public float spinSpeed;
            public float bob;
        }

        public enum LiquidKind { None, Water, Wine, Void, Brass }

        [Header("Identity")]
        public string id;
        public string locKey;
        public int depth;
        public bool isPassage;

        [Header("Layout")]
        public int mainRooms = 10;
        public int treasureRooms = 2;
        public int eliteRooms;
        public bool merchant = true;
        public string[] lore = new string[0];
        public string bossTag = "";
        public string rune = "";            // rune carried by this biome's rune guardian
        public string requiredRune = "";    // variant biomes: rune needed to open the branch door
        [Range(0f, 1.5f)] public float enemyDensity = 0.8f;

        [Header("Kit")]
        public List<TileModule> tiles = new List<TileModule>();
        public Material kitMaterial;
        public Material wallMaterial;
        public Material deepMaterial;
        public Material platformMaterial;
        public float backWallScale = 0.5f;
        [Tooltip("Back wall height above the floor below it (tiles); above that the background shows.")]
        public Vector2 backWallHeight = new Vector2(6f, 9f);
        [Tooltip("Automatic wall lights along floors, metres apart (0 = only 't' markers).")]
        public float lightSpacing = 9f;
        public GameObject lightPrefab;
        public GameObject doorPrefab;
        public List<Decor> decor = new List<Decor>();

        [Header("Atmosphere")]
        [ColorUsage(false, true)] public Color fogColor = new Color(0.10f, 0.26f, 0.32f);
        public float fogDensity = 0.15f;
        [ColorUsage(false, true)] public Color ambient = new Color(0.035f, 0.05f, 0.075f);
        public Color ambientLight = new Color(0.06f, 0.11f, 0.14f);
        public Color keyColor = new Color(0.62f, 0.82f, 1f);
        public float keyIntensity = 0.65f;
        public Vector3 keyEuler = new Vector3(20f, 24f, 0f);
        public Color rimColor = new Color(0.35f, 0.85f, 1f);
        public float rimIntensity = 0.9f;
        public Color torchColor = new Color(1f, 0.55f, 0.22f);
        public float torchIntensity = 4f;
        public Color motesA = new Color(0.55f, 0.95f, 1.1f, 0.5f);
        public Color motesB = new Color(0.9f, 1.1f, 1.2f, 0.9f);
        public Color embersA = new Color(3f, 1.1f, 0.3f, 1f);
        public Color embersB = new Color(3.5f, 1.8f, 0.5f, 1f);
        [Tooltip("Upward rain (Stilt Village).")]
        public bool rainUp;
        [Tooltip("God-ray shafts from ceilings per 100 m.")]
        public float lightShafts = 3f;
        public Color shaftColor = new Color(0.55f, 0.95f, 1f);
        public LiquidKind liquid;
        public Material liquidMaterial;
        public Color titleColor = new Color(0.75f, 0.9f, 1f);

        [Header("Population")]
        public List<EnemyEntry> ground = new List<EnemyEntry>();
        public List<EnemyEntry> flying = new List<EnemyEntry>();
        public List<EnemyEntry> turrets = new List<EnemyEntry>();
        public GameObject boss;
        public GameObject hazardPrefab;     // biome special (sorrow cloud / furnace vent)
        public float hazardDensity;

        public string DisplayName => Meta.Loc.Get($"biome.{locKey}.name");
        public string Subtitle => Meta.Loc.Get($"biome.{locKey}.sub");

        public TileModule Tile(string role)
        {
            foreach (var t in tiles)
                if (t.role == role)
                    return t;
            return null;
        }

        public static GameObject Pick(List<EnemyEntry> pool, System.Random rng)
        {
            float total = 0f;
            foreach (var e in pool)
                if (e.prefab != null)
                    total += e.weight;
            if (total <= 0f)
                return null;
            double r = rng.NextDouble() * total;
            foreach (var e in pool)
            {
                if (e.prefab == null)
                    continue;
                r -= e.weight;
                if (r <= 0)
                    return e.prefab;
            }
            return pool[pool.Count - 1].prefab;
        }
    }
}
