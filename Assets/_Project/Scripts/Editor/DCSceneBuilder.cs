using System.Collections.Generic;
using System.IO;
using System.Linq;
using DeadCells.CameraRig;
using DeadCells.Core;
using DeadCells.Environment;
using DeadCells.FX;
using DeadCells.Player;
using DeadCells.Rendering;
using DeadCells.UI;
using Unity.Cinemachine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace DeadCells.EditorTools
{
    /// <summary>
    /// Builds Scenes/PrisonersQuarters.unity: a ~75 m slice of the starting
    /// biome. Layout is a height profile on a 1 m grid; visible tiles are
    /// combined into chunk meshes, collisions merged into a composite collider.
    /// Depth layers: gameplay z=0, props/doors/torches z~1-2.5, back wall z=2.5,
    /// ruins z=5, towers/spires z=10, all melted together by DCAtmosphere fog.
    /// </summary>
    public static class DCSceneBuilder
    {
        public const string ScenePath = "Assets/_Project/Scenes/PrisonersQuarters.unity";
        const string GenDir = "Assets/_Project/Generated"; // legacy output folder, removed on rebuild
        const string Env = "Assets/_Project/Art/Environment/Meshes/";
        const int W = 76;
        const int H = 18;
        const float WallZ = 2.5f;

        static bool[,] solid;
        static System.Random rnd;
        static LevelGeometry geo;
        static readonly Dictionary<string, int> moduleIndex = new Dictionary<string, int>();
        static readonly List<Mesh> moduleMeshes = new List<Mesh>();
        static readonly List<Matrix4x4> moduleMatrices = new List<Matrix4x4>();

        // ------------------------------------------------------------- layout

        static int FloorTop(int x)
        {
            if (x < 2) return H;
            if (x < 21) return 4;
            if (x < 34) return 1;
            if (x >= 42 && x <= 46) return 6;
            if (x < 56) return 4;
            if (x < 58) return 5;
            if (x < 73) return 6;
            return H;
        }

        static int CeilingBottom(int x)
        {
            if (x < 20) return 13;
            if (x < 24) return 11;
            if (x < 56) return 16;
            if (x < 61) return 12;
            return 14;
        }

        static readonly (int x0, int x1, int top)[] Platforms =
        {
            (24, 26, 4), (29, 31, 4), (36, 38, 7), (49, 51, 7), (63, 65, 9),
        };

        static readonly Vector2[] ZombieSpawns =
        {
            new Vector2(27.5f, 1f), new Vector2(39f, 4f), new Vector2(44.5f, 6f), new Vector2(52f, 4f),
            new Vector2(65.5f, 6f), new Vector2(70f, 6f),
        };

        static readonly Vector2 PlayerSpawn = new Vector2(4.5f, 4f);

        [MenuItem("Dead Cells/Setup/3 Build Scene")]
        public static void BuildScene()
        {
            rnd = new System.Random(1337);
            Directory.CreateDirectory(Path.GetDirectoryName(ScenePath));
            AssetDatabase.DeleteAsset(GenDir); // merged meshes are no longer stored on disk
            moduleIndex.Clear();
            moduleMeshes.Clear();
            moduleMatrices.Clear();
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            BuildGrid();
            var level = new GameObject("Level").transform;
            geo = new GameObject("LevelGeometry").AddComponent<LevelGeometry>();
            geo.transform.SetParent(level, false);
            geo.enabled = false;
            BuildTiles(level);
            BuildCollision(level);
            BuildPlatforms(level);
            BuildBackWall(level);
            BuildDecor(level);
            BuildBackground(level);
            BuildLighting(level);
            geo.modules = moduleMeshes.ToArray();
            geo.moduleMatrices = moduleMatrices.ToArray();
            geo.enabled = true;

            var player = SpawnPlayer();
            SpawnEnemies();
            var cam = BuildCamera(player);
            BuildSystems(player, cam);

            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.06f, 0.11f, 0.14f);
            RenderSettings.fog = false;
            RenderSettings.skybox = null;

            EditorSceneManager.SaveScene(scene, ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            Debug.Log($"[DC] scene built: {ScenePath} ({geo.PlacementCount} module placements in {geo.batches.Count} batches)");
        }

        static void BuildGrid()
        {
            solid = new bool[W, H];
            for (int x = 0; x < W; x++)
            for (int y = 0; y < H; y++)
                solid[x, y] = y < FloorTop(x) || y >= CeilingBottom(x);
        }

        static bool Solid(int x, int y) => x < 0 || x >= W || y < 0 || y >= H || solid[x, y];

        static int DistanceToAir(int x, int y)
        {
            for (int r = 0; r <= 3; r++)
            for (int dx = -r; dx <= r; dx++)
            for (int dy = -r; dy <= r; dy++)
            {
                int nx = x + dx, ny = y + dy;
                if (nx >= 0 && nx < W && ny >= 0 && ny < H && !solid[nx, ny])
                    return r;
            }
            return 99;
        }

        // -------------------------------------------------------------- tiles

        static int Module(string name)
        {
            if (moduleIndex.TryGetValue(name, out int i))
                return i;
            Mesh mesh;
            Matrix4x4 local = Matrix4x4.identity;
            if (name == "Quad")
                mesh = Resources.GetBuiltinResource<Mesh>("Quad.fbx");
            else
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(Env + name + ".fbx");
                var mf = go != null ? go.GetComponentInChildren<MeshFilter>() : null;
                if (mf == null)
                    Debug.LogError("[DC] missing module " + name);
                mesh = mf != null ? mf.sharedMesh : null;
                // Child transform inside the FBX (identity when axis conversion is baked).
                if (mf != null)
                    local = go.transform.worldToLocalMatrix * mf.transform.localToWorldMatrix;
            }
            moduleMeshes.Add(mesh);
            moduleMatrices.Add(local);
            return moduleIndex[name] = moduleMeshes.Count - 1;
        }

        static LevelGeometry.Batch Batch(string name, Material material, bool castShadows = true)
        {
            var b = geo.batches.FirstOrDefault(x => x.name == name);
            if (b == null)
            {
                b = new LevelGeometry.Batch { name = name, material = material, castShadows = castShadows };
                geo.batches.Add(b);
            }
            return b;
        }

        static void Put(LevelGeometry.Batch batch, string module, Vector3 position, Vector3? scale = null)
        {
            batch.placements.Add(new LevelGeometry.Placement { module = Module(module), position = position, scale = scale ?? Vector3.one });
        }

        static string Pick(params string[] options) => options[rnd.Next(options.Length)];

        static void BuildTiles(Transform level)
        {
            var envMat = DCContentBuilder.LoadMat("M_ENV_Kit");
            var deep = Batch("DeepFill", envMat);
            // Dark cards just behind the brick faces hide hairline gaps between modules.
            var backing = Batch("TileBacking", DCContentBuilder.LoadMat("M_ENV_Wall"), false);
            for (int x = 0; x < W; x++)
            for (int y = 0; y < H; y++)
            {
                if (!solid[x, y])
                    continue;
                Put(backing, "Quad", new Vector3(x + 0.5f, y + 0.5f, -0.4f), new Vector3(1.04f, 1f, 1f));
                if (DistanceToAir(x, y) > 2)
                {
                    Put(deep, Pick("ENV_Stone_A", "ENV_Stone_B", "ENV_Stone_C"), new Vector3(x, y, 0f));
                    continue;
                }
                bool airAbove = !Solid(x, y + 1);
                bool airLeft = !Solid(x - 1, y) && airAbove;
                bool airRight = !Solid(x + 1, y) && airAbove;
                string module;
                if (airAbove && airLeft)
                    module = "ENV_StoneEdge_L";
                else if (airAbove && airRight)
                    module = "ENV_StoneEdge_R";
                else if (airAbove)
                    module = Pick("ENV_StoneTop_A", "ENV_StoneTop_B");
                else
                    module = Pick("ENV_Stone_A", "ENV_Stone_B", "ENV_Stone_C");
                var chunk = Batch($"Chunk_{x / 8}_{y / 8}", envMat);
                Put(chunk, module, new Vector3(x, y, 0f));
                // Second rank of floor behind, filling the gap up to the back wall.
                if (airAbove)
                    Put(chunk, Pick("ENV_StoneTop_A", "ENV_StoneTop_B"), new Vector3(x, y, 2.45f));
            }
        }

        // ---------------------------------------------------------- collision

        static void BuildCollision(Transform level)
        {
            var go = new GameObject("Collision");
            go.transform.SetParent(level, false);
            go.layer = DCLayers.Ground;
            var body = go.AddComponent<Rigidbody2D>();
            body.bodyType = RigidbodyType2D.Static;
            var composite = go.AddComponent<CompositeCollider2D>();
            composite.geometryType = CompositeCollider2D.GeometryType.Polygons;
            composite.generationType = CompositeCollider2D.GenerationType.Synchronous;
            for (int y = 0; y < H; y++)
            {
                int x = 0;
                while (x < W)
                {
                    if (!solid[x, y])
                    {
                        x++;
                        continue;
                    }
                    int start = x;
                    while (x < W && solid[x, y])
                        x++;
                    var box = go.AddComponent<BoxCollider2D>();
                    box.size = new Vector2(x - start, 1f);
                    box.offset = new Vector2(start + (x - start) * 0.5f, y + 0.5f);
                    box.compositeOperation = Collider2D.CompositeOperation.Merge;
                }
            }
            // Outer walls beyond the grid so nothing escapes.
            foreach (float wx in new[] { -2f, W + 2f })
            {
                var wall = go.AddComponent<BoxCollider2D>();
                wall.size = new Vector2(4f, H * 2f);
                wall.offset = new Vector2(wx, H * 0.5f);
                wall.compositeOperation = Collider2D.CompositeOperation.Merge;
            }
            composite.GenerateGeometry();
        }

        static void BuildPlatforms(Transform level)
        {
            var parent = new GameObject("OneWayPlatforms").transform;
            parent.SetParent(level, false);
            var wood = Batch("WoodPlatforms", DCContentBuilder.LoadMat("M_ENV_Kit"));
            foreach (var (x0, x1, top) in Platforms)
            {
                var go = new GameObject($"Platform_{x0}_{x1}");
                go.transform.SetParent(parent, false);
                go.layer = DCLayers.OneWay;
                var col = go.AddComponent<BoxCollider2D>();
                col.size = new Vector2(x1 - x0 + 1, 0.2f);
                col.offset = new Vector2(x0 + (x1 - x0 + 1) * 0.5f, top - 0.1f);
                col.usedByEffector = true;
                var eff = go.AddComponent<PlatformEffector2D>();
                eff.useOneWay = true;
                eff.surfaceArc = 170f;
                eff.useSideFriction = false;
                eff.useSideBounce = false;
                for (int x = x0; x <= x1; x++)
                    Put(wood, "ENV_WoodPlatform", new Vector3(x, top - 1, 0f));
            }
        }

        // ---------------------------------------------------------- back wall

        static bool WallCovers(float x, float y)
        {
            if (x < 22f) return y < 14f;
            if (x < 34f) return y < 6f;
            if (x < 58f) return y < 10f;
            return y < 16f;
        }

        static bool AirNear(int x, int y)
        {
            for (int cx = x - 1; cx <= x + 2; cx++)
            for (int cy = y - 1; cy <= y + 2; cy++)
                if (!Solid(cx, cy))
                    return true;
            return false;
        }

        static void BuildBackWall(Transform level)
        {
            // Half-scale panels: bricks read at the right size next to a 2 m character.
            var wall = Batch("BackWall", DCContentBuilder.LoadMat("M_ENV_Wall"));
            for (int x = -4; x < W + 4; x += 2)
            for (int y = -4; y < H + 2; y += 2)
            {
                if (!WallCovers(x + 1f, y + 0.01f) || !AirNear(x, y))
                    continue; // panels fully behind solid ground are never seen
                Put(wall, "ENV_BackWall", new Vector3(x, y, WallZ), new Vector3(0.5f, 0.5f, 1f));
            }
        }

        // -------------------------------------------------------------- decor

        static GameObject Place(string module, Transform parent, Vector3 pos, float yRot = 0f, float scale = 1f, Material mat = null)
        {
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(Env + module + ".fbx");
            var go = (GameObject)PrefabUtility.InstantiatePrefab(src);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = pos;
            go.transform.localRotation = Quaternion.Euler(0f, yRot, 0f);
            go.transform.localScale = Vector3.one * scale;
            foreach (var r in go.GetComponentsInChildren<MeshRenderer>())
                r.sharedMaterial = mat != null ? mat : DCContentBuilder.LoadMat(module.StartsWith("BG_") ? "M_BG_Kit" : "M_ENV_Kit");
            return go;
        }

        static void BuildDecor(Transform level)
        {
            var decor = new GameObject("Decor").transform;
            decor.SetParent(level, false);

            foreach (float x in new[] { 6f, 12f, 17.5f })
                Place("ENV_CellDoor", decor, new Vector3(x, 4f, 1.62f));
            foreach (float x in new[] { 61f, 68f })
                Place("ENV_CellDoor", decor, new Vector3(x, 6f, 1.62f));
            Place("ENV_Arch", decor, new Vector3(44.5f, 4f, 1.7f));
            Place("ENV_Arch", decor, new Vector3(27.5f, 1f, 1.7f));
            foreach (var (x, y) in new[] { (21f, 4f), (34.5f, 4f), (40f, 4f), (49.5f, 4f), (56.5f, 5f), (72f, 6f) })
                Place("ENV_Pillar", decor, new Vector3(x, y, 1.75f));
            foreach (var (x, y) in new[] { (38f, 8.0f), (46f, 8.0f), (54f, 8.0f), (9f, 9f), (65f, 10.5f) })
                Place("ENV_Grate", decor, new Vector3(x, y, WallZ - 0.12f));

            // Torches.
            var torchPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(DCContentBuilder.PrefabDir + "/Torch.prefab");
            foreach (var (x, y) in new[] { (3f, 7f), (9f, 7f), (15f, 7f), (36.5f, 7.5f), (53f, 7.5f), (59f, 9f), (64.5f, 9f), (71f, 9f) })
            {
                var t = (GameObject)PrefabUtility.InstantiatePrefab(torchPrefab);
                t.transform.SetParent(decor, false);
                t.transform.localPosition = new Vector3(x, y, WallZ - 0.05f);
            }

            // Chains (pendulums) and cages hanging from ceilings.
            foreach (var (x, top, z, scale) in new[] { (8f, 13f, 1.0f, 1f), (11.5f, 13f, 0.6f, 0.75f), (40.5f, 16f, 1.0f, 1.4f), (47.5f, 16f, 0.8f, 1.2f), (66f, 14f, 0.9f, 1f), (17f, 13f, -1.8f, 1.1f), (60f, 12f, -2.2f, 1f) })
            {
                var pivot = new GameObject("ChainPivot").transform;
                pivot.SetParent(decor, false);
                pivot.localPosition = new Vector3(x, top, z);
                Place("ENV_Chain", pivot, Vector3.zero, 90f, 1f);
                pivot.localScale = new Vector3(1f, scale, 1f);
                var sway = pivot.gameObject.AddComponent<ChainSway>();
                sway.length = 3f * scale;
            }
            foreach (var (x, top, z) in new[] { (24.5f, 11f, 1.0f), (57.5f, 12f, 1.0f), (45f, 16f, 1.2f) })
            {
                var pivot = new GameObject("CagePivot").transform;
                pivot.SetParent(decor, false);
                pivot.localPosition = new Vector3(x, top, z);
                Place("ENV_Chain", pivot, Vector3.zero, 0f, 0.6f);
                Place("ENV_Cage", pivot, new Vector3(0f, -1.7f, 0f), 20f);
                var sway = pivot.gameObject.AddComponent<ChainSway>();
                sway.length = 4f;
                sway.idleAmplitude = 0.8f;
            }
            foreach (var (x, top) in new[] { (5f, 12f), (14f, 12f), (42f, 9.6f), (62.5f, 13.5f) })
                Place("ENV_Banner", decor, new Vector3(x, top, WallZ - 0.2f));
            foreach (var (m, x, y, z, rot) in new[]
                     {
                         ("ENV_Barrel", 2.8f, 4f, 1.0f, 20f), ("ENV_Barrel", 19.4f, 4f, 1.1f, -10f), ("ENV_Crate", 18.3f, 4f, 0.9f, 8f),
                         ("ENV_BonePile", 25.5f, 1f, 0.7f, 0f), ("ENV_BonePile", 47.5f, 4f, 0.9f, 180f), ("ENV_BonePile", 69f, 6f, 1.0f, 0f),
                         ("ENV_Crate", 57.2f, 5f, 1.0f, -6f), ("ENV_Barrel", 58.3f, 6f, 1.2f, 0f),
                     })
                Place(m, decor, new Vector3(x, y, z), rot);

            BuildLightShafts(decor);
        }

        static void BuildLightShafts(Transform parent)
        {
            var mat = DCContentBuilder.LoadMat("M_LightShaft");
            foreach (var (x, y, len, width, tilt) in new[] { (38f, 9.6f, 7f, 2.0f, 14f), (46f, 9.6f, 7.5f, 2.2f, 12f), (54f, 9.6f, 7f, 2.0f, 15f), (9f, 10.5f, 7f, 1.8f, 10f), (65f, 12f, 7f, 1.8f, 12f) })
            {
                var go = new GameObject("LightShaft", typeof(MeshFilter), typeof(MeshRenderer));
                go.layer = DCLayers.Fx;
                go.transform.SetParent(parent, false);
                // Trapezoid hanging from the grate, tilted with the light.
                go.transform.localPosition = new Vector3(x, y, 1.3f);
                go.transform.localRotation = Quaternion.Euler(0f, 0f, tilt);
                var holder = go.transform;
                var shaft = go.AddComponent<LightShaftMesh>();
                shaft.length = len;
                shaft.bottomWidth = width;
                var r = go.GetComponent<MeshRenderer>();
                r.sharedMaterial = mat;
                r.shadowCastingMode = ShadowCastingMode.Off;
                r.receiveShadows = false;
                // Matching cool spot light down the shaft.
                var lgo = new GameObject("ShaftLight");
                lgo.transform.SetParent(holder, false);
                lgo.transform.localPosition = new Vector3(0f, 0f, -0.6f);
                lgo.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
                var l = lgo.AddComponent<Light>();
                l.type = LightType.Spot;
                l.color = new Color(0.55f, 0.95f, 1f);
                l.intensity = 3.5f;
                l.range = 11f;
                l.spotAngle = 38f;
                l.innerSpotAngle = 12f;
                l.shadows = LightShadows.None;
            }
        }

        // --------------------------------------------------------- background

        static void BuildBackground(Transform level)
        {
            var bg = new GameObject("Background").transform;
            bg.SetParent(level, false);
            // Mid layer z ~ 5.
            foreach (var (m, x, y) in new[] { ("BG_Ruins", 14f, -1f), ("BG_Ruins", 37f, 0f), ("BG_Ruins", 60f, -1f) })
                Place(m, bg, new Vector3(x, y, 5f), 0f, 1f);
            // Far layer z ~ 10.
            foreach (var (m, x, y, s) in new[] { ("BG_Tower_A", 26f, -6f, 1f), ("BG_Spires", 41f, -4f, 1.1f), ("BG_Tower_B", 52f, -7f, 1f), ("BG_Tower_A", 70f, -5f, 1.1f), ("BG_Spires", 6f, -4f, 1f) })
                Place(m, bg, new Vector3(x, y, 10f), 0f, s);
            foreach (var (m, x, y, s) in new[] { ("BG_Tower_B", 33f, -10f, 1.5f), ("BG_Tower_A", 48f, -12f, 1.6f), ("BG_Spires", 63f, -9f, 1.6f) })
                Place(m, bg, new Vector3(x, y, 16f), 0f, s);
        }

        // ----------------------------------------------------------- lighting

        static void BuildLighting(Transform level)
        {
            var lights = new GameObject("Lighting").transform;
            lights.SetParent(level, false);
            var key = new GameObject("Moonlight").AddComponent<Light>();
            key.transform.SetParent(lights, false);
            key.type = LightType.Directional;
            // Low, frontal key: fronts read, floor tops stay secondary, shadows fall on the back wall.
            key.transform.rotation = Quaternion.Euler(20f, 24f, 0f);
            key.color = new Color(0.62f, 0.82f, 1f);
            key.intensity = 0.65f;
            key.shadows = LightShadows.Soft;
            key.shadowStrength = 0.85f;
            var keyData = key.gameObject.AddComponent<UniversalAdditionalLightData>();
            keyData.usePipelineSettings = true;

            var rim = new GameObject("RimBacklight").AddComponent<Light>();
            rim.transform.SetParent(lights, false);
            rim.type = LightType.Directional;
            rim.transform.rotation = Quaternion.Euler(25f, 200f, 0f);
            rim.color = new Color(0.35f, 0.85f, 1f);
            rim.intensity = 0.9f;
            rim.shadows = LightShadows.None;

            var volume = new GameObject("GlobalVolume").AddComponent<Volume>();
            volume.transform.SetParent(lights, false);
            volume.isGlobal = true;
            volume.priority = 1;
            volume.sharedProfile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(DCProjectSetup.PostProfilePath);
        }

        // ------------------------------------------------------------- actors

        static PlayerController SpawnPlayer()
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(DCContentBuilder.PrefabDir + "/Player.prefab");
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            go.transform.position = new Vector3(PlayerSpawn.x, PlayerSpawn.y, 0f);
            return go.GetComponent<PlayerController>();
        }

        static void SpawnEnemies()
        {
            var parent = new GameObject("Enemies").transform;
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(DCContentBuilder.PrefabDir + "/Zombie.prefab");
            foreach (var p in ZombieSpawns)
            {
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
                go.transform.position = new Vector3(p.x, p.y, 0f);
            }
        }

        static Camera BuildCamera(PlayerController player)
        {
            var camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            var cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            // Empty sky = the depth-fog colour (fog values are linear; clear colour is sRGB).
            cam.backgroundColor = DCAtmosphere.DefaultFogColor.gamma;
            cam.fieldOfView = 30f;
            cam.nearClipPlane = 0.5f;
            cam.farClipPlane = 140f;
            cam.allowMSAA = false;
            cam.transform.position = new Vector3(PlayerSpawn.x, PlayerSpawn.y + 2f, -17f);
            var data = camGo.AddComponent<UniversalAdditionalCameraData>();
            data.renderPostProcessing = true;
            data.antialiasing = AntialiasingMode.None;
            data.renderShadows = true;
            var brain = camGo.AddComponent<CinemachineBrain>();
            brain.IgnoreTimeScale = true;
            var snap = camGo.AddComponent<PixelPerfectCamera>();
            snap.gameplayPlaneZ = 0f;

            var vcamGo = new GameObject("CM_Follow");
            var vcam = vcamGo.AddComponent<CinemachineCamera>();
            vcam.Lens = new LensSettings { FieldOfView = 30f, NearClipPlane = 0.5f, FarClipPlane = 140f, ModeOverride = LensSettings.OverrideModes.Perspective };
            Transform target = player.transform.Find("CameraTarget");
            vcam.Target.TrackingTarget = target != null ? target : player.transform;
            var composer = vcamGo.AddComponent<CinemachinePositionComposer>();
            composer.CameraDistance = 17f;
            composer.Damping = new Vector3(0.35f, 0.5f, 0f);
            composer.Lookahead = new LookaheadSettings { Enabled = true, Time = 0.28f, Smoothing = 6f, IgnoreY = true };
            var comp = composer.Composition;
            comp.ScreenPosition = new Vector2(0f, 0.08f);
            comp.DeadZone = new ScreenComposerSettings.DeadZoneSettings { Enabled = true, Size = new Vector2(0.1f, 0.16f) };
            composer.Composition = comp;
            var noise = vcamGo.AddComponent<CinemachineBasicMultiChannelPerlin>();
            noise.NoiseProfile = AssetDatabase.LoadAssetAtPath<NoiseSettings>(
                AssetDatabase.FindAssets("6D Shake t:NoiseSettings").Select(AssetDatabase.GUIDToAssetPath).FirstOrDefault() ?? "");
            noise.AmplitudeGain = 0f;
            noise.FrequencyGain = 3f;
            var listener = vcamGo.AddComponent<CinemachineImpulseListener>();
            listener.Gain = 1f;
            listener.Use2DDistance = true;
            var bounds = vcamGo.AddComponent<CameraBounds>();
            bounds.levelBounds = new Rect(1f, 0f, W - 3f, H);
            vcamGo.transform.position = cam.transform.position;
            return cam;
        }

        static void BuildSystems(PlayerController player, Camera cam)
        {
            var juiceGo = new GameObject("JuiceEngine");
            var impulse = juiceGo.AddComponent<CinemachineImpulseSource>();
            impulse.ImpulseDefinition.ImpulseShape = CinemachineImpulseDefinition.ImpulseShapes.Bump;
            impulse.ImpulseDefinition.ImpulseType = CinemachineImpulseDefinition.ImpulseTypes.Uniform;
            impulse.ImpulseDefinition.ImpulseDuration = 0.16f;
            impulse.DefaultVelocity = Vector3.down;
            var juice = juiceGo.AddComponent<JuiceEngine>();
            juice.kickSource = impulse;
            juice.traumaNoise = Object.FindAnyObjectByType<CinemachineBasicMultiChannelPerlin>();
            juice.additiveMaterial = DCContentBuilder.LoadMat("M_FX_Additive");
            juice.flashMaterial = DCContentBuilder.LoadMat("M_FX_Flash");
            juice.alphaMaterial = DCContentBuilder.LoadMat("M_FX_Alpha");
            juice.dustMaterial = DCContentBuilder.LoadMat("M_FX_Dust");
            juice.textMaterial = DCContentBuilder.LoadMat("M_PixelText");

            var gmGo = new GameObject("GameManager");
            var gm = gmGo.AddComponent<GameManager>();
            gm.player = player;
            var spawn = new GameObject("PlayerSpawn").transform;
            spawn.position = new Vector3(PlayerSpawn.x, PlayerSpawn.y, 0f);
            gm.spawnPoint = spawn;
            gm.flameMaterial = DCContentBuilder.LoadMat("M_BeheadedFlame");
            gm.bodyMaterial = DCContentBuilder.LoadMat("M_Beheaded");
            gm.smokeMaterial = DCContentBuilder.LoadMat("M_BeheadedSmoke");
            gm.flameLight = player.GetComponentsInChildren<Light>(true).FirstOrDefault(l => l.name == "FlameLight");
            var auto = gmGo.AddComponent<AutoplayDirector>();
            auto.player = player;

            new GameObject("Atmosphere").AddComponent<DCAtmosphere>();
            var ambient = new GameObject("AmbientParticles").AddComponent<AmbientParticles>();
            ambient.motesMaterial = DCContentBuilder.LoadMat("M_FX_Flash");
            ambient.embersMaterial = DCContentBuilder.LoadMat("M_FX_Additive");
            ambient.follow = cam.transform;
            ambient.gameObject.layer = DCLayers.Fx;

            var hud = new GameObject("HUD").AddComponent<GameHUD>();
            hud.player = player;
        }
    }
}
