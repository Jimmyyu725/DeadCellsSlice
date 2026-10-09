using System.Collections.Generic;
using DeadCells.Core;
using DeadCells.Enemies;
using DeadCells.Environment;
using DeadCells.Items;
using DeadCells.Meta;
using UnityEngine;
using UnityEngine.Rendering;

namespace DeadCells.Run
{
    /// <summary>
    /// Turns LevelData into a playable level using a biome kit: merged chunk
    /// meshes (front tiles, second-rank floor, back wall), composite
    /// collision, one-way platforms, liquids, hazards, lights, parallax decor
    /// and all entities.
    /// </summary>
    public static class LevelBuilder
    {
        const int Chunk = 16;
        const float WallZ = 2.5f;

        class MeshBatch
        {
            public Material material;
            public bool shadows = true;
            public readonly List<CombineInstance> parts = new List<CombineInstance>();
        }

        static Mesh quad;

        static Mesh Quad
        {
            get
            {
                if (quad == null)
                {
                    quad = new Mesh { name = "DC_Quad", hideFlags = HideFlags.DontSave };
                    quad.vertices = new[] { new Vector3(-0.5f, -0.5f, 0f), new Vector3(-0.5f, 0.5f, 0f), new Vector3(0.5f, 0.5f, 0f), new Vector3(0.5f, -0.5f, 0f) };
                    quad.uv = new[] { Vector2.zero, Vector2.up, Vector2.one, Vector2.right };
                    quad.normals = new[] { Vector3.back, Vector3.back, Vector3.back, Vector3.back };
                    quad.triangles = new[] { 0, 1, 2, 0, 2, 3 };
                    quad.RecalculateBounds();
                }
                return quad;
            }
        }

        public static BuiltLevel Build(LevelData data, BiomeDef biome, Transform parent, int seed)
        {
            var rng = new System.Random(seed ^ 0x5f3759df);
            var root = new GameObject($"Level_{biome.id}");
            root.transform.SetParent(parent, false);
            var built = new BuiltLevel { root = root, data = data, biome = biome };
            built.bounds = new Rect(1f, 1f, data.width - 2f, data.height - 2f);

            var dist = DistanceToAir(data);
            BuildGeometry(data, biome, root.transform, dist, rng);
            BuildCollision(data, root.transform);
            BuildPlatforms(data, root.transform);
            BuildLiquidsAndHazards(data, biome, root.transform);
            BuildDecor(data, biome, root.transform, dist, rng);
            BuildLightShafts(data, biome, root.transform, rng);
            SpawnEntities(data, biome, root.transform, built, rng);
            LogStats(root, biome, data);
            return built;
        }

        static void Kill(Object o)
        {
            if (o == null)
                return;
            if (Application.isPlaying)
                Object.Destroy(o);
            else
                Object.DestroyImmediate(o);
        }

        public static string Stats(GameObject root)
        {
            long tris = 0;
            int renderers = 0;
            var byGroup = new Dictionary<string, long>();
            foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
            {
                if (mf.sharedMesh == null)
                    continue;
                renderers++;
                long t = 0;
                for (int i = 0; i < mf.sharedMesh.subMeshCount; i++)
                    t += mf.sharedMesh.GetIndexCount(i) / 3;
                tris += t;
                // Group: geometry batch prefix, or the top-level decor/entity object name.
                string group = mf.transform.parent != null && mf.transform.parent.name == "Geometry"
                    ? mf.name.Split('_')[0] + (mf.name.EndsWith("_Rank") ? "_Rank" : mf.name.EndsWith("_Back") ? "_Back" : "")
                    : TopName(root.transform, mf.transform);
                byGroup[group] = (byGroup.TryGetValue(group, out long g) ? g : 0) + t;
            }
            int lights = root.GetComponentsInChildren<Light>(true).Length;
            var top = new List<KeyValuePair<string, long>>(byGroup);
            top.Sort((a, b) => b.Value.CompareTo(a.Value));
            var sb = new System.Text.StringBuilder($"renderers={renderers} tris={tris / 1000}k lights={lights} |");
            for (int i = 0; i < Mathf.Min(12, top.Count); i++)
                sb.Append($" {top[i].Key}={top[i].Value / 1000}k");
            return sb.ToString();
        }

        static string TopName(Transform root, Transform t)
        {
            // Child of a container (Decor/Entities/Hazards) → its prefab instance name.
            while (t.parent != null && t.parent.parent != root)
                t = t.parent;
            return t.parent != null ? t.parent.name + "/" + t.name.Replace("(Clone)", "") : t.name;
        }

        static void LogStats(GameObject root, BiomeDef biome, LevelData d)
        {
            Debug.Log($"[DC] level {biome.id} {d.width}x{d.height} rooms={d.rooms.Count} {Stats(root)}");
        }

        // ------------------------------------------------------------ helpers

        static bool Open(LevelData d, int x, int y) => d.At(x, y) != Tile.Solid;

        static int[,] DistanceToAir(LevelData d)
        {
            var dist = new int[d.width, d.height];
            var q = new Queue<Vector2Int>();
            for (int x = 0; x < d.width; x++)
            for (int y = 0; y < d.height; y++)
            {
                if (Open(d, x, y))
                {
                    dist[x, y] = 0;
                    q.Enqueue(new Vector2Int(x, y));
                }
                else
                {
                    dist[x, y] = int.MaxValue;
                }
            }
            while (q.Count > 0)
            {
                var p = q.Dequeue();
                int nd = dist[p.x, p.y] + 1;
                for (int dx = -1; dx <= 1; dx++)
                for (int dy = -1; dy <= 1; dy++)
                {
                    int nx = p.x + dx, ny = p.y + dy;
                    if (nx < 0 || ny < 0 || nx >= d.width || ny >= d.height || dist[nx, ny] <= nd)
                        continue;
                    dist[nx, ny] = nd;
                    q.Enqueue(new Vector2Int(nx, ny));
                }
            }
            return dist;
        }

        static void Add(Dictionary<string, MeshBatch> batches, string key, Material mat, Mesh mesh, Matrix4x4 m, bool shadows = true)
        {
            if (mesh == null || mat == null)
                return;
            if (!batches.TryGetValue(key, out var b))
            {
                b = new MeshBatch { material = mat, shadows = shadows };
                batches[key] = b;
            }
            b.parts.Add(new CombineInstance { mesh = mesh, transform = m });
        }

        static void Put(Dictionary<string, MeshBatch> batches, string key, Material mat, BiomeDef.TileModule mod, Vector3 pos, Vector3 scale, bool shadows = true)
        {
            if (mod == null)
                return;
            Add(batches, key, mat, mod.mesh, Matrix4x4.TRS(pos, Quaternion.identity, scale) * mod.matrix, shadows);
        }

        static void Emit(Dictionary<string, MeshBatch> batches, Transform parent, string prefix)
        {
            foreach (var kv in batches)
            {
                var b = kv.Value;
                if (b.parts.Count == 0)
                    continue;
                var mesh = new Mesh { name = prefix + kv.Key, indexFormat = IndexFormat.UInt32 };
                mesh.CombineMeshes(b.parts.ToArray(), true, true);
                mesh.RecalculateBounds();
                mesh.UploadMeshData(true);
                var go = new GameObject(prefix + kv.Key, typeof(MeshFilter), typeof(MeshRenderer));
                go.transform.SetParent(parent, false);
                go.GetComponent<MeshFilter>().sharedMesh = mesh;
                var r = go.GetComponent<MeshRenderer>();
                r.sharedMaterial = b.material;
                r.shadowCastingMode = b.shadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
                go.AddComponent<OwnedMesh>();
            }
        }

        static T Pick<T>(System.Random rng, params T[] options) => options[rng.Next(options.Length)];

        // ----------------------------------------------------------- geometry

        static void BuildGeometry(LevelData d, BiomeDef biome, Transform root, int[,] dist, System.Random rng)
        {
            var geo = new GameObject("Geometry").transform;
            geo.SetParent(root, false);
            var batches = new Dictionary<string, MeshBatch>();
            var kit = biome.kitMaterial;
            var wall = biome.wallMaterial != null ? biome.wallMaterial : kit;
            var deep = biome.deepMaterial != null ? biome.deepMaterial : WorldPrefabs.Instance.deepMaterial;
            var fills = new[] { biome.Tile("Fill_A"), biome.Tile("Fill_B"), biome.Tile("Fill_C") };
            var tops = new[] { biome.Tile("Top_A"), biome.Tile("Top_B") };
            var edgeL = biome.Tile("Edge_L");
            var edgeR = biome.Tile("Edge_R");
            var backWall = biome.Tile("BackWall");

            // Deep rock: merged dark quads per row run (cheap, no detail needed).
            for (int y = 0; y < d.height; y++)
            {
                int x = 0;
                while (x < d.width)
                {
                    if (dist[x, y] < 3)
                    {
                        x++;
                        continue;
                    }
                    int start = x;
                    while (x < d.width && dist[x, y] >= 3 && x - start < Chunk)
                        x++;
                    int len = x - start;
                    var m = Matrix4x4.TRS(new Vector3(start + len * 0.5f, y + 0.5f, -0.9f), Quaternion.identity, new Vector3(len, 1f, 1f));
                    Add(batches, $"Deep_{start / Chunk}_{y / Chunk}", deep, Quad, m, false);
                }
            }

            for (int x = 0; x < d.width; x++)
            for (int y = 0; y < d.height; y++)
            {
                // Two rings of kit modules around open space; deeper rock is dark fill.
                if (Open(d, x, y) || dist[x, y] >= 3)
                    continue;
                string key = $"Chunk_{x / Chunk}_{y / Chunk}";
                // Dark card just behind the tile faces hides hairline gaps between modules.
                Add(batches, key + "_Back", deep, Quad, Matrix4x4.TRS(new Vector3(x + 0.5f, y + 0.5f, -0.4f), Quaternion.identity, new Vector3(1.04f, 1f, 1f)), false);
                bool airAbove = Open(d, x, y + 1) && d.At(x, y + 1) != Tile.Liquid;
                bool airLeft = Open(d, x - 1, y) && airAbove;
                bool airRight = Open(d, x + 1, y) && airAbove;
                BiomeDef.TileModule mod;
                if (airAbove && airLeft && edgeL != null)
                    mod = edgeL;
                else if (airAbove && airRight && edgeR != null)
                    mod = edgeR;
                else if (airAbove)
                    mod = Pick(rng, tops);
                else
                    mod = Pick(rng, fills);
                Put(batches, key, kit, mod, new Vector3(x, y, 0f), Vector3.one);
                // Second rank of floor behind, filling the gap up to the back wall.
                if (airAbove)
                    Put(batches, key + "_Rank", kit, Pick(rng, tops), new Vector3(x, y, 2.45f), Vector3.one, false);
            }

            // One-way platform planks.
            var plank = biome.Tile("Platform");
            var plankMat = biome.platformMaterial != null ? biome.platformMaterial : kit;
            for (int x = 0; x < d.width; x++)
            for (int y = 0; y < d.height; y++)
                if (d.tiles[x, y] == Tile.OneWay)
                    Put(batches, $"Plank_{x / Chunk}_{y / Chunk}", plankMat, plank, new Vector3(x, y, 0f), Vector3.one);

            // Back wall panels behind open space, up to a ragged height above the
            // local floor; above that the fogged background silhouettes show through.
            float s = biome.backWallScale;
            float step = 4f * s;
            var floorBelow = FloorBelow(d);
            for (float wx = 0f; wx < d.width; wx += step)
            {
                float noise = Mathf.PerlinNoise(wx * 0.11f, d.seed * 0.001f);
                float limit = Mathf.Lerp(biome.backWallHeight.x, biome.backWallHeight.y, noise);
                for (float wy = 0f; wy < d.height; wy += step)
                {
                    int cx = Mathf.FloorToInt(wx), cy = Mathf.FloorToInt(wy);
                    if (!AirNear(d, cx, cy, Mathf.CeilToInt(step)))
                        continue;
                    // Height of this panel above the floor under the open cells it backs.
                    int floor = int.MaxValue;
                    for (int px = cx; px < cx + step && px < d.width; px++)
                    for (int py = cy; py < cy + step && py < d.height; py++)
                        if (Open(d, px, py))
                            floor = Mathf.Min(floor, floorBelow[px, py]);
                    if (floor != int.MaxValue && wy - floor > limit)
                        continue;
                    string key = $"Wall_{(int)(wx / Chunk)}_{(int)(wy / Chunk)}";
                    Put(batches, key, wall, backWall, new Vector3(wx, wy, WallZ), new Vector3(s, s, 1f), false);
                }
            }
            Emit(batches, geo, "");
        }

        /// <summary>For each open cell, the y of the first solid/one-way tile below it.</summary>
        static int[,] FloorBelow(LevelData d)
        {
            var f = new int[d.width, d.height];
            for (int x = 0; x < d.width; x++)
            {
                int last = 0;
                for (int y = 0; y < d.height; y++)
                {
                    if (d.tiles[x, y] == Tile.Solid || d.tiles[x, y] == Tile.OneWay)
                        last = y + 1;
                    f[x, y] = last;
                }
            }
            return f;
        }

        static bool AirNear(LevelData d, int x, int y, int size)
        {
            for (int cx = x - 1; cx <= x + size; cx++)
            for (int cy = y - 1; cy <= y + size; cy++)
                if (Open(d, cx, cy))
                    return true;
            return false;
        }

        // ---------------------------------------------------------- collision

        static void BuildCollision(LevelData d, Transform root)
        {
            var go = new GameObject("Collision");
            go.transform.SetParent(root, false);
            go.layer = DCLayers.Ground;
            var body = go.AddComponent<Rigidbody2D>();
            body.bodyType = RigidbodyType2D.Static;
            var composite = go.AddComponent<CompositeCollider2D>();
            composite.geometryType = CompositeCollider2D.GeometryType.Polygons;
            composite.generationType = CompositeCollider2D.GenerationType.Manual;
            for (int y = 0; y < d.height; y++)
            {
                int x = 0;
                while (x < d.width)
                {
                    if (d.tiles[x, y] != Tile.Solid)
                    {
                        x++;
                        continue;
                    }
                    int start = x;
                    while (x < d.width && d.tiles[x, y] == Tile.Solid)
                        x++;
                    var box = go.AddComponent<BoxCollider2D>();
                    box.size = new Vector2(x - start, 1f);
                    box.offset = new Vector2(start + (x - start) * 0.5f, y + 0.5f);
                    box.compositeOperation = Collider2D.CompositeOperation.Merge;
                }
            }
            composite.GenerateGeometry();
        }

        static void BuildPlatforms(LevelData d, Transform root)
        {
            var parent = new GameObject("OneWayPlatforms").transform;
            parent.SetParent(root, false);
            for (int y = 0; y < d.height; y++)
            {
                int x = 0;
                while (x < d.width)
                {
                    if (d.tiles[x, y] != Tile.OneWay)
                    {
                        x++;
                        continue;
                    }
                    int start = x;
                    while (x < d.width && d.tiles[x, y] == Tile.OneWay)
                        x++;
                    var go = new GameObject($"Platform_{start}_{y}");
                    go.transform.SetParent(parent, false);
                    go.layer = DCLayers.OneWay;
                    var col = go.AddComponent<BoxCollider2D>();
                    col.size = new Vector2(x - start, 0.2f);
                    col.offset = new Vector2(start + (x - start) * 0.5f, y + 0.9f);
                    col.usedByEffector = true;
                    var eff = go.AddComponent<PlatformEffector2D>();
                    eff.useOneWay = true;
                    eff.surfaceArc = 170f;
                    eff.useSideFriction = false;
                    eff.useSideBounce = false;
                }
            }
        }

        static Material LiquidMaterial(BiomeDef biome)
        {
            if (biome.liquidMaterial != null)
                return biome.liquidMaterial;
            var w = WorldPrefabs.Instance;
            return biome.liquid switch
            {
                BiomeDef.LiquidKind.Wine => w.liquidWine,
                BiomeDef.LiquidKind.Void => w.liquidVoid,
                BiomeDef.LiquidKind.Brass => w.liquidBrass,
                _ => w.liquidWater,
            };
        }

        static void BuildLiquidsAndHazards(LevelData d, BiomeDef biome, Transform root)
        {
            var parent = new GameObject("Hazards").transform;
            parent.SetParent(root, false);
            var mat = LiquidMaterial(biome);
            var visited = new bool[d.width, d.height];
            for (int y = 0; y < d.height; y++)
            for (int x = 0; x < d.width; x++)
            {
                if (visited[x, y] || d.tiles[x, y] != Tile.Liquid)
                    continue;
                // Rectangle of liquid: run along x, then down while the whole run is liquid.
                int x1 = x;
                while (x1 + 1 < d.width && d.tiles[x1 + 1, y] == Tile.Liquid && !visited[x1 + 1, y])
                    x1++;
                int y0 = y, y1 = y;
                while (y1 + 1 < d.height && RunIs(d, x, x1, y1 + 1, Tile.Liquid))
                    y1++;
                for (int cx = x; cx <= x1; cx++)
                for (int cy = y0; cy <= y1; cy++)
                    visited[cx, cy] = true;
                float w = x1 - x + 1, h = y1 - y0 + 1;
                var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
                Kill(go.GetComponent<Collider>());
                go.name = "Liquid";
                go.transform.SetParent(parent, false);
                float top = y1 + 0.82f;
                go.transform.localPosition = new Vector3(x + w * 0.5f, (y0 + top) * 0.5f, 0.8f);
                go.transform.localScale = new Vector3(w, top - y0, 3.6f);
                var r = go.GetComponent<MeshRenderer>();
                r.sharedMaterial = mat;
                r.shadowCastingMode = ShadowCastingMode.Off;
                go.layer = DCLayers.Fx;
                var hz = go.AddComponent<Hazard>();
                hz.kind = biome.liquid == BiomeDef.LiquidKind.Void ? Hazard.Kind.Pit : Hazard.Kind.Liquid;
                hz.size = new Vector2(w, top - y0 - 0.3f);
                hz.harmless = biome.liquid == BiomeDef.LiquidKind.Water;
                hz.returnToSafety = !hz.harmless;
                hz.damageFraction = biome.liquid == BiomeDef.LiquidKind.Void ? 0.08f : 0.12f;
                hz.splashColor = mat != null && mat.HasProperty("_Color") ? mat.GetColor("_Color") : Color.white;
            }

            var spikes = WorldPrefabs.Instance.spikes;
            for (int y = 0; y < d.height; y++)
            {
                int x = 0;
                while (x < d.width)
                {
                    if (d.tiles[x, y] != Tile.Spikes)
                    {
                        x++;
                        continue;
                    }
                    int start = x;
                    while (x < d.width && d.tiles[x, y] == Tile.Spikes)
                        x++;
                    var holder = new GameObject("Spikes");
                    holder.transform.SetParent(parent, false);
                    holder.transform.localPosition = new Vector3(start + (x - start) * 0.5f, y + 0.35f, 0f);
                    var hz = holder.AddComponent<Hazard>();
                    hz.kind = Hazard.Kind.Spikes;
                    hz.size = new Vector2(x - start - 0.2f, 0.6f);
                    hz.damageFraction = 0.08f;
                    hz.flatDamage = 8f;
                    hz.splashColor = new Color(0.8f, 0.1f, 0.15f);
                    if (spikes != null)
                    {
                        for (int sx = start; sx < x; sx++)
                        {
                            var s = Object.Instantiate(spikes, parent);
                            s.transform.localPosition = new Vector3(sx + 0.5f, y, 0f);
                        }
                    }
                }
            }
        }

        static bool RunIs(LevelData d, int x0, int x1, int y, Tile t)
        {
            for (int x = x0; x <= x1; x++)
                if (d.At(x, y) != t)
                    return false;
            return true;
        }

        // -------------------------------------------------------------- decor

        static GameObject Place(GameObject prefab, Transform parent, Vector3 pos, float yRot = 0f, float scale = 1f)
        {
            if (prefab == null)
                return null;
            var go = Object.Instantiate(prefab, parent);
            go.transform.localPosition = pos;
            go.transform.localRotation = Quaternion.Euler(0f, yRot, 0f);
            go.transform.localScale = Vector3.one * scale;
            return go;
        }

        static void Tint(GameObject lightObject, BiomeDef biome)
        {
            foreach (var light in lightObject.GetComponentsInChildren<Light>())
            {
                light.color = biome.torchColor;
                var flicker = light.GetComponent<TorchFlicker>();
                if (flicker != null)
                    flicker.baseIntensity = biome.torchIntensity;
                else
                    light.intensity = biome.torchIntensity;
            }
        }

        static bool FloorCell(LevelData d, int x, int y) =>
            d.At(x, y) == Tile.Air && d.At(x, y + 1) == Tile.Air && d.At(x, y - 1) == Tile.Solid;

        static bool CeilingCell(LevelData d, int x, int y) =>
            d.At(x, y) == Tile.Air && d.At(x, y - 1) == Tile.Air && d.At(x, y - 2) == Tile.Air && d.At(x, y + 1) == Tile.Solid;

        static void BuildDecor(LevelData d, BiomeDef biome, Transform root, int[,] dist, System.Random rng)
        {
            var parent = new GameObject("Decor").transform;
            parent.SetParent(root, false);
            var occupied = new HashSet<int>();
            foreach (var s in d.spawns)
                for (int dx = -2; dx <= 2; dx++)
                    occupied.Add((s.cell.x + dx) * 100000 + s.cell.y);

            // Wall lights at 't' markers.
            foreach (var s in d.spawns)
            {
                if (s.code != 't' || biome.lightPrefab == null)
                    continue;
                var l = Place(biome.lightPrefab, parent, new Vector3(s.cell.x + 0.5f, s.cell.y + 0.2f, WallZ - 0.05f));
                Tint(l, biome);
            }

            // Extra wall lights along floors so every stretch of a room is lit.
            if (biome.lightPrefab != null && biome.lightSpacing > 0f)
            {
                foreach (var room in d.rooms)
                {
                    var r = room.rect;
                    float next = r.xMin + 3f + (float)rng.NextDouble() * 3f;
                    for (int x = r.xMin + 1; x < r.xMax - 1; x++)
                    {
                        if (x < next)
                            continue;
                        int fy = -1;
                        for (int y = r.yMin + 1; y < r.yMax - 3; y++)
                            if (FloorCell(d, x, y) && Open(d, x, y + 2) && Open(d, x, y + 3))
                            {
                                fy = y;
                                break;
                            }
                        if (fy < 0)
                            continue;
                        next = x + biome.lightSpacing * (0.8f + (float)rng.NextDouble() * 0.4f);
                        var l = Place(biome.lightPrefab, parent, new Vector3(x + 0.5f, fy + 2.6f, WallZ - 0.05f));
                        Tint(l, biome);
                    }
                }
            }

            foreach (var dec in biome.decor)
            {
                if (dec.prefab == null || dec.density <= 0f)
                    continue;
                int count = Mathf.Max(1, Mathf.RoundToInt(dec.density * d.width / 100f));
                for (int i = 0, tries = 0; i < count && tries < count * 30; tries++)
                {
                    int x = rng.Next(2, d.width - 2), y = rng.Next(2, d.height - 2);
                    float z = Mathf.Lerp(dec.z.x, dec.z.y, (float)rng.NextDouble());
                    float scale = Mathf.Lerp(dec.scale.x, dec.scale.y, (float)rng.NextDouble());
                    Vector3 pos;
                    switch (dec.placement)
                    {
                        case BiomeDef.Placement.Floor:
                            if (!FloorCell(d, x, y) || occupied.Contains(x * 100000 + y))
                                continue;
                            pos = new Vector3(x + 0.5f, y, z);
                            occupied.Add(x * 100000 + y);
                            break;
                        case BiomeDef.Placement.Ceiling:
                            if (!CeilingCell(d, x, y))
                                continue;
                            pos = new Vector3(x + 0.5f, y + 1f, z);
                            break;
                        case BiomeDef.Placement.WallMounted:
                            if (!Open(d, x, y) || !Open(d, x, y + 1) || d.At(x, y - 1) == Tile.Air && d.At(x, y - 2) == Tile.Air && d.At(x, y - 3) == Tile.Air)
                                continue;
                            pos = new Vector3(x + 0.5f, y, WallZ - 0.1f);
                            break;
                        case BiomeDef.Placement.UnderPlatform:
                            if (d.At(x, y) != Tile.OneWay || d.At(x, y - 1) != Tile.Air)
                                continue;
                            pos = new Vector3(x + 0.5f, y + 0.9f, z);
                            break;
                        case BiomeDef.Placement.Floating:
                            if (!Open(d, x, y) || !Open(d, x, y + 2) || !Open(d, x, y - 2))
                                continue;
                            pos = new Vector3(x + 0.5f, y + 0.5f, z);
                            break;
                        case BiomeDef.Placement.MidBackground:
                        case BiomeDef.Placement.FarBackground:
                        {
                            // Anchor silhouettes below the room they stand behind.
                            int room = d.RoomAt(new Vector2(x, y));
                            if (room < 0)
                                continue;
                            var rect = d.rooms[room].rect;
                            // Bases sit low enough to hide, tops rise above the back-wall band.
                            float baseY = rect.yMin + (dec.placement == BiomeDef.Placement.FarBackground ? -2f + (float)rng.NextDouble() * 4f : 2f + (float)rng.NextDouble() * 2f);
                            pos = new Vector3(x, baseY, z);
                            break;
                        }
                        default:
                            continue;
                    }
                    var go = Place(dec.prefab, parent, pos, dec.placement == BiomeDef.Placement.Floor ? rng.Next(-25, 25) : 0f, scale);
                    if (go != null && (dec.placement == BiomeDef.Placement.FarBackground || dec.placement == BiomeDef.Placement.MidBackground))
                        foreach (var r in go.GetComponentsInChildren<Renderer>())
                            r.shadowCastingMode = ShadowCastingMode.Off;
                    if (go != null && (dec.spinSpeed != 0f || dec.bob > 0f))
                    {
                        var m = go.AddComponent<DecorMotion>();
                        m.spinSpeed = dec.spinSpeed * (rng.NextDouble() < 0.5 ? -1f : 1f);
                        m.bob = dec.bob;
                    }
                    i++;
                }
            }
        }

        /// <summary>God rays falling from ceilings into open rooms, each with a matching spot light.</summary>
        static void BuildLightShafts(LevelData d, BiomeDef biome, Transform root, System.Random rng)
        {
            var mat = WorldPrefabs.Instance.shaftMaterial;
            if (mat == null || biome.lightShafts <= 0f)
                return;
            var parent = new GameObject("LightShafts").transform;
            parent.SetParent(root, false);
            int count = Mathf.RoundToInt(biome.lightShafts * d.width / 100f);
            float lastX = -100f;
            for (int i = 0, tries = 0; i < count && tries < count * 40; tries++)
            {
                int x = rng.Next(3, d.width - 3), y = rng.Next(6, d.height - 2);
                if (!CeilingCell(d, x, y) || Mathf.Abs(x - lastX) < 8f)
                    continue;
                // Needs a tall open drop below the ceiling.
                int clear = 0;
                while (clear < 8 && Open(d, x, y - clear))
                    clear++;
                if (clear < 6)
                    continue;
                lastX = x;
                var go = new GameObject("LightShaft", typeof(MeshFilter), typeof(MeshRenderer));
                go.layer = DCLayers.Fx;
                go.transform.SetParent(parent, false);
                float tilt = (float)(rng.NextDouble() * 10.0 + 8.0) * (rng.NextDouble() < 0.5 ? -1f : 1f);
                go.transform.localPosition = new Vector3(x + 0.5f, y + 0.9f, 1.3f);
                go.transform.localRotation = Quaternion.Euler(0f, 0f, tilt);
                var shaft = go.AddComponent<LightShaftMesh>();
                shaft.length = clear + 0.5f;
                shaft.bottomWidth = 1.8f + (float)rng.NextDouble() * 0.6f;
                var r = go.GetComponent<MeshRenderer>();
                r.sharedMaterial = mat;
                r.shadowCastingMode = ShadowCastingMode.Off;
                r.receiveShadows = false;
                var lgo = new GameObject("ShaftLight");
                lgo.transform.SetParent(go.transform, false);
                lgo.transform.localPosition = new Vector3(0f, 0f, -0.6f);
                lgo.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
                var l = lgo.AddComponent<Light>();
                l.type = LightType.Spot;
                l.color = biome.shaftColor;
                l.intensity = 3.5f;
                l.range = clear + 4f;
                l.spotAngle = 38f;
                l.innerSpotAngle = 12f;
                l.shadows = LightShadows.None;
                i++;
            }
        }

        // ------------------------------------------------------------ entities

        static void SpawnEntities(LevelData d, BiomeDef biome, Transform root, BuiltLevel built, System.Random rng)
        {
            var parent = new GameObject("Entities").transform;
            parent.SetParent(root, false);
            var w = WorldPrefabs.Instance;
            var db = ItemDatabase.Instance;
            int loreIndex = 0;
            int teleIndex = 0;
            float density = Mathf.Clamp01(biome.enemyDensity * Difficulty.EnemyCount);
            ExitDoor exitDoor = null;
            BossGate gate = null;
            var shopItems = Loot.ShopStock(rng, biome.depth);
            int shopIndex = 0;
            var starters = new Queue<string>(new[] { "shield_frontline", "bow_spiked" });

            foreach (var s in d.spawns)
            {
                Vector3 pos = new Vector3(s.cell.x + 0.5f, s.cell.y, 0f);
                switch (s.code)
                {
                    case 'P':
                        built.playerStart = pos;
                        break;
                    case 'e':
                    case 'f':
                    case 'o':
                    case 'E':
                    {
                        bool elite = s.code == 'E' || rng.NextDouble() < Difficulty.EliteChance * 0.5;
                        if (s.code != 'E' && rng.NextDouble() > density)
                            break;
                        var pool = s.code == 'f' && biome.flying.Count > 0 ? biome.flying
                            : s.code == 'o' && biome.turrets.Count > 0 ? biome.turrets : biome.ground;
                        var prefab = BiomeDef.Pick(pool, rng);
                        if (prefab == null)
                            break;
                        Vector3 at = s.code == 'f' ? pos + Vector3.up * 0.5f : pos;
                        var go = Object.Instantiate(prefab, at, Quaternion.identity, parent);
                        var enemy = go.GetComponent<EnemyBase>();
                        if (enemy != null)
                        {
                            enemy.Configure(biome.depth, elite);
                            built.enemies.Add(enemy);
                        }
                        break;
                    }
                    case 'T':
                    {
                        var go = Place(w.teleporter, parent, pos + new Vector3(0f, 0f, 1.2f));
                        var t = go.GetComponent<Teleporter>();
                        t.Index = teleIndex++;
                        built.teleporters.Add(t);
                        break;
                    }
                    case 'C':
                        Place(w.chest, parent, pos + new Vector3(0f, 0f, 0.6f));
                        built.treasures.Add(pos);
                        break;
                    case '$':
                        Loot.SpawnGoldPile(pos + Vector3.up * 0.5f, Mathf.RoundToInt((20 + rng.Next(30)) * (1f + 0.6f * biome.depth) * Difficulty.RewardMultiplier), parent);
                        break;
                    case 's':
                    {
                        var go = Place(w.scroll, parent, pos + new Vector3(0f, 0f, 0.3f));
                        go.GetComponent<ScrollPickup>().vitality = rng.NextDouble() < 0.5;
                        built.treasures.Add(pos);
                        break;
                    }
                    case 'W':
                    {
                        if (db == null || starters.Count == 0)
                            break;
                        var def = db.Get(starters.Dequeue());
                        if (def == null)
                            break;
                        var go = Place(w.pedestal, parent, pos + new Vector3(0f, 0f, 0.4f));
                        go.GetComponent<ItemPickup>().Setup(def, 0);
                        break;
                    }
                    case 'M':
                        Place(w.merchant, parent, pos + new Vector3(0f, 0f, 1.0f), 180f);
                        built.shops.Add(pos);
                        break;
                    case 'p':
                    {
                        if (shopIndex >= shopItems.Count)
                            break;
                        var (def, price) = shopItems[shopIndex++];
                        var go = Place(w.pedestal, parent, pos + new Vector3(0f, 0f, 0.4f));
                        go.GetComponent<ItemPickup>().Setup(def, price);
                        break;
                    }
                    case 'L':
                    {
                        if (loreIndex >= biome.lore.Length)
                            break;
                        var go = Place(w.loreTablet, parent, pos + new Vector3(0f, 0f, 1.0f));
                        go.GetComponent<LoreTablet>().loreId = biome.lore[loreIndex++];
                        built.lore.Add(pos);
                        break;
                    }
                    case 'F':
                        Place(w.fountain, parent, pos + new Vector3(0f, 0f, 1.2f));
                        break;
                    case 'K':
                        Place(w.collector, parent, pos + new Vector3(0f, 0f, 1.0f), 180f);
                        break;
                    case 'D':
                    {
                        var go = Place(biome.doorPrefab != null ? biome.doorPrefab : w.exitDoor, parent, pos + new Vector3(0f, 0f, 1.6f));
                        exitDoor = go.GetComponent<ExitDoor>() ?? go.AddComponent<ExitDoor>();
                        exitDoor.range = 2.2f;
                        built.exits.Add(pos);
                        break;
                    }
                    case 'B':
                    {
                        if (biome.boss == null)
                            break;
                        var go = Object.Instantiate(biome.boss, pos, Quaternion.identity, parent);
                        built.boss = go.GetComponent<EnemyBase>();
                        built.boss?.Configure(biome.depth, false);
                        if (built.boss != null)
                            built.enemies.Add(built.boss);
                        break;
                    }
                    case 'G':
                    {
                        var go = Place(w.bossGate, parent, pos + new Vector3(-0.5f, 0f, 0f));
                        gate = go.GetComponent<BossGate>();
                        if (gate != null)
                            gate.triggerX = pos.x;
                        break;
                    }
                }
            }
            if (gate != null)
            {
                gate.boss = built.boss;
                gate.exit = exitDoor;
            }
            // Biome hazards (sorrow clouds, furnace vents) over open floors.
            if (biome.hazardPrefab != null && biome.hazardDensity > 0f)
            {
                int count = Mathf.RoundToInt(biome.hazardDensity * d.width / 100f);
                for (int i = 0, tries = 0; i < count && tries < count * 40; tries++)
                {
                    int x = rng.Next(4, d.width - 4), y = rng.Next(3, d.height - 3);
                    int room = d.RoomAt(new Vector2(x, y));
                    if (room < 0 || !d.rooms[room].main || d.rooms[room].kind == "start" || d.rooms[room].kind.StartsWith("boss"))
                        continue;
                    bool cloud = biome.hazardPrefab.GetComponent<SorrowCloud>() != null;
                    if (cloud ? !(Open(d, x, y) && Open(d, x, y - 1) && Open(d, x + 1, y) && d.At(x, y + 2) == Tile.Solid) : !FloorCell(d, x, y))
                        continue;
                    Place(biome.hazardPrefab, parent, new Vector3(x + 0.5f, y, cloud ? 0f : 0.2f));
                    i++;
                }
            }
            if (built.playerStart == Vector3.zero && d.rooms.Count > 0)
            {
                var r = d.rooms[0].rect;
                built.playerStart = new Vector3(r.xMin + 3.5f, r.yMin + 2f, 0f);
            }
        }
    }
}
