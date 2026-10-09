using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// Fog-of-war map: one texel per tile, revealed in a radius around the
    /// player. The map screen and minimap draw this texture plus markers.
    /// </summary>
    public class MapSystem : MonoBehaviour
    {
        public float revealRadius = 11f;

        public static MapSystem Instance { get; private set; }

        LevelData data;
        bool[,] explored;
        Texture2D tex;
        Color32[] pixels;
        bool dirty;
        float timer;
        Color32 liquid = new Color32(140, 70, 200, 230);

        public Texture2D Texture => tex;
        public LevelData Data => data;
        public int Width => data != null ? data.width : 1;
        public int Height => data != null ? data.height : 1;

        void Awake() => Instance = this;

        void OnDestroy()
        {
            if (Instance == this)
                Instance = null;
            if (tex != null)
                Destroy(tex);
        }

        public void Setup(LevelData level, Color liquidColor)
        {
            data = level;
            explored = new bool[level.width, level.height];
            if (tex != null)
                Destroy(tex);
            tex = new Texture2D(level.width, level.height, TextureFormat.RGBA32, false)
            {
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                name = "DC_Map",
            };
            pixels = new Color32[level.width * level.height];
            liquid = (Color32)new Color(Mathf.Clamp01(liquidColor.r), Mathf.Clamp01(liquidColor.g), Mathf.Clamp01(liquidColor.b), 0.9f);
            tex.SetPixels32(pixels);
            tex.Apply(false, false);
        }

        public bool Explored(Vector2 world)
        {
            int x = Mathf.FloorToInt(world.x), y = Mathf.FloorToInt(world.y);
            return data != null && x >= 0 && y >= 0 && x < data.width && y < data.height && explored[x, y];
        }

        Color32 ColorOf(int x, int y)
        {
            switch (data.tiles[x, y])
            {
                case Tile.Air:
                    return new Color32(26, 30, 44, 200);
                case Tile.OneWay:
                    return new Color32(150, 120, 80, 255);
                case Tile.Liquid:
                    return liquid;
                case Tile.Spikes:
                    return new Color32(200, 50, 60, 255);
                default:
                    // Solid: bright only on the surface so rooms read as outlines.
                    bool edge = false;
                    for (int dx = -1; dx <= 1 && !edge; dx++)
                    for (int dy = -1; dy <= 1 && !edge; dy++)
                        if (data.At(x + dx, y + dy) != Tile.Solid)
                            edge = true;
                    return edge ? new Color32(150, 165, 190, 255) : new Color32(10, 12, 18, 160);
            }
        }

        public void Reveal(Vector2 center, float radius)
        {
            if (data == null)
                return;
            int r = Mathf.CeilToInt(radius);
            int cx = Mathf.FloorToInt(center.x), cy = Mathf.FloorToInt(center.y);
            float r2 = radius * radius;
            for (int x = cx - r; x <= cx + r; x++)
            for (int y = cy - r; y <= cy + r; y++)
            {
                if (x < 0 || y < 0 || x >= data.width || y >= data.height || explored[x, y])
                    continue;
                if ((x - cx) * (x - cx) + (y - cy) * (y - cy) > r2)
                    continue;
                explored[x, y] = true;
                pixels[y * data.width + x] = ColorOf(x, y);
                dirty = true;
            }
        }

        public void RevealAll()
        {
            if (data == null)
                return;
            for (int x = 0; x < data.width; x++)
            for (int y = 0; y < data.height; y++)
            {
                explored[x, y] = true;
                pixels[y * data.width + x] = ColorOf(x, y);
            }
            dirty = true;
        }

        void LateUpdate()
        {
            var p = Player.PlayerController.Main;
            timer -= Time.unscaledDeltaTime;
            if (p != null && timer <= 0f)
            {
                timer = 0.12f;
                Reveal(p.transform.position + Vector3.up, revealRadius);
            }
            if (dirty && tex != null)
            {
                tex.SetPixels32(pixels);
                tex.Apply(false, false);
                dirty = false;
            }
        }
    }
}
