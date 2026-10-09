using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using UnityEngine.Rendering;

namespace DeadCells.EditorTools
{
    /// <summary>
    /// Generates materials, animator controllers, prefabs and data assets
    /// (items, biomes, world prefabs) from what the Blender pipeline exported.
    /// Idempotent: rerunning updates in place. Split across partial files:
    /// this one (helpers, materials, controllers), .Actors (items,
    /// projectiles, player, enemies) and .World (props, biomes, databases).
    /// </summary>
    public static partial class DCContentBuilder
    {
        public const string Root = "Assets/_Project";
        public const string MatDir = Root + "/Materials";
        public const string AnimDir = Root + "/Animation";
        public const string PrefabDir = Root + "/Prefabs";
        public const string ContentDir = Root + "/Content";
        public const string ResourcesDir = Root + "/Resources";
        const string ArtDir = Root + "/Art";
        const string CharDir = ArtDir + "/Characters";
        const string WeaponDir = ArtDir + "/Weapons";
        const string ArsenalDir = ArtDir + "/Weapons/Arsenal";
        const string PropsDir = ArtDir + "/Props";
        const string EnvDir = ArtDir + "/Environment";
        const string BiomeArtDir = ArtDir + "/Biomes";

        public static readonly string[] KitBiomes = { "Promenade", "Ossuary", "StiltVillage", "ClockLung" };
        public static readonly string[] RiggedCharacters = { "Beheaded", "Zombie", "Sentinel", "Monk", "Fisher", "RoyalGuardian", "TimeKeeper" };

        [MenuItem("Dead Cells/Setup/2 Build Content")]
        public static void BuildAll()
        {
            foreach (var d in new[] { MatDir, AnimDir, PrefabDir, PrefabDir + "/Items", PrefabDir + "/Projectiles", PrefabDir + "/Enemies",
                         PrefabDir + "/World", ContentDir + "/Items", ContentDir + "/Biomes", ContentDir + "/Meshes", ContentDir + "/Textures", ResourcesDir })
                Directory.CreateDirectory(d);
            AssetDatabase.Refresh();
            ReimportArt();
            BuildMaterials();
            BuildControllers();
            BuildItemVisuals();
            BuildProjectiles();
            BuildPlayerPrefab();
            BuildEnemyPrefabs();
            BuildWorldPrefabs();
            BuildItems();
            BuildBiomes();
            AssetDatabase.SaveAssets();
            Debug.Log("[DC] content built");
        }

        /// <summary>Re-run the import rules so clip names and readability always match the postprocessor.</summary>
        static void ReimportArt()
        {
            foreach (var c in RiggedCharacters)
            {
                string fbx = $"{CharDir}/{c}/{c}.fbx";
                if (File.Exists(fbx))
                    AssetDatabase.ImportAsset(fbx, ImportAssetOptions.ForceUpdate);
            }
            foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { $"{EnvDir}/Meshes", BiomeArtDir }))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                if (AssetImporter.GetAtPath(path) is ModelImporter mi && !mi.isReadable)
                    AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            }
        }

        // ------------------------------------------------------------ helpers

        public static Material Mat(string name, string shader, System.Action<Material> setup)
        {
            string path = $"{MatDir}/{name}.mat";
            var sh = Shader.Find(shader);
            if (sh == null)
            {
                Debug.LogError($"[DC] shader not found: {shader}");
                return null;
            }
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null)
            {
                m = new Material(sh);
                AssetDatabase.CreateAsset(m, path);
            }
            m.shader = sh;
            setup(m);
            EditorUtility.SetDirty(m);
            return m;
        }

        public static Material LoadMat(string name) => AssetDatabase.LoadAssetAtPath<Material>($"{MatDir}/{name}.mat");

        static Texture2D Tex(string path) => AssetDatabase.LoadAssetAtPath<Texture2D>(path);

        static void Textures(Material m, string dir, string prefix)
        {
            m.SetTexture("_BaseMap", Tex($"{dir}/{prefix}_Albedo.png"));
            m.SetTexture("_BumpMap", Tex($"{dir}/{prefix}_Normal.png"));
            m.SetTexture("_ORMMap", Tex($"{dir}/{prefix}_ORM.png"));
            m.SetTexture("_EmissionMap", Tex($"{dir}/{prefix}_Emission.png"));
            if (Tex($"{dir}/{prefix}_Albedo.png") == null)
                Debug.LogError($"[DC] missing textures {dir}/{prefix}_*");
        }

        /// <summary>Small solid-colour texture asset (e.g. a neutral ORM for untextured metal).</summary>
        static Texture2D SolidTexture(string name, Color c, bool linear)
        {
            string path = $"{ContentDir}/Textures/{name}.png";
            if (!File.Exists(path))
            {
                var t = new Texture2D(4, 4, TextureFormat.RGBA32, false);
                var px = Enumerable.Repeat(c, 16).ToArray();
                t.SetPixels(px);
                t.Apply();
                File.WriteAllBytes(path, t.EncodeToPNG());
                Object.DestroyImmediate(t);
                AssetDatabase.ImportAsset(path);
                var ti = (TextureImporter)AssetImporter.GetAtPath(path);
                ti.sRGBTexture = !linear;
                ti.mipmapEnabled = false;
                ti.filterMode = FilterMode.Point;
                ti.SaveAndReimport();
            }
            return Tex(path);
        }

        public static Transform Find(Transform root, string name)
        {
            if (root.name == name)
                return root;
            foreach (Transform c in root)
            {
                var r = Find(c, name);
                if (r != null)
                    return r;
            }
            return null;
        }

        static GameObject Model(string path)
        {
            var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (go == null)
                Debug.LogError("[DC] missing model " + path);
            return go;
        }

        static GameObject Instance(string fbxPath)
        {
            var src = Model(fbxPath);
            if (src == null)
                return new GameObject(Path.GetFileNameWithoutExtension(fbxPath));
            var go = (GameObject)PrefabUtility.InstantiatePrefab(src);
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.OutermostRoot, InteractionMode.AutomatedAction);
            return go;
        }

        static GameObject Save(GameObject instance, string relPath)
        {
            string path = $"{PrefabDir}/{relPath}.prefab";
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            var prefab = PrefabUtility.SaveAsPrefabAsset(instance, path);
            Object.DestroyImmediate(instance);
            return prefab;
        }

        static GameObject LoadPrefab(string relPath) => AssetDatabase.LoadAssetAtPath<GameObject>($"{PrefabDir}/{relPath}.prefab");

        static void AssignAll(GameObject go, Material m, bool shadows = true)
        {
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                r.sharedMaterial = m;
                r.shadowCastingMode = shadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
            }
        }

        static void SetLayer(GameObject go, int layer)
        {
            foreach (var t in go.GetComponentsInChildren<Transform>(true))
                t.gameObject.layer = layer;
        }

        static Light PointLight(Transform parent, Vector3 local, Color color, float intensity, float range, string name = "Light")
        {
            var l = new GameObject(name).AddComponent<Light>();
            l.transform.SetParent(parent, false);
            l.transform.localPosition = local;
            l.type = LightType.Point;
            l.color = color;
            l.intensity = intensity;
            l.range = range;
            l.shadows = LightShadows.None;
            return l;
        }

        static Mesh SaveMesh(Mesh mesh, string name)
        {
            string path = $"{ContentDir}/Meshes/{name}.asset";
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            mesh.name = name;
            if (existing != null)
            {
                EditorUtility.CopySerialized(mesh, existing);
                Object.DestroyImmediate(mesh);
                return existing;
            }
            AssetDatabase.CreateAsset(mesh, path);
            return mesh;
        }

        static Material Particle(string name, float src, float dst, float shape, float softness = 0.6f)
        {
            return Mat(name, "DeadCells/Particle", m =>
            {
                m.SetFloat("_SrcBlend", src);
                m.SetFloat("_DstBlend", dst);
                m.SetFloat("_Shape", shape);
                m.SetFloat("_Softness", softness);
                m.SetColor("_Color", Color.white);
                m.SetFloat("_Intensity", 1f);
                m.renderQueue = (int)RenderQueue.Transparent;
            });
        }

        static Material Unlit(string name, Color c, float pulse = 0f, float pulseSpeed = 4f) => Mat(name, "DeadCells/UnlitHDR", m =>
        {
            m.SetColor("_Color", c);
            m.SetFloat("_PulseAmp", pulse);
            m.SetFloat("_PulseSpeed", pulseSpeed);
        });

        // ---------------------------------------------------------- materials

        static Material CharacterMat(string name, string dir, string prefix, Color emission, Color shadowTint, Color rim, float rimStrength = 0.5f, float outline = 1f)
        {
            return Mat(name, "DeadCells/CharacterLit", m =>
            {
                Textures(m, dir, prefix);
                m.SetColor("_EmissionColor", emission);
                m.SetFloat("_EmissionPulseAmp", 0.3f);
                m.SetFloat("_EmissionPulseSpeed", 3f);
                m.SetColor("_ShadowTint", shadowTint);
                m.SetColor("_RimColor", rim);
                m.SetFloat("_RimStrength", rimStrength);
                m.SetFloat("_OutlinePixels", outline);
                m.SetColor("_OutlineColor", new Color(0.03f, 0.02f, 0.05f));
            });
        }

        public static void BuildMaterials()
        {
            Color purpleGlow = new Color(0.61f, 0.36f, 0.9f);
            Mat("M_Beheaded", "DeadCells/CharacterLit", m =>
            {
                Textures(m, $"{CharDir}/Beheaded/Textures", "Beheaded");
                m.SetColor("_EmissionColor", purpleGlow * 2.2f);
                m.SetFloat("_EmissionPulseAmp", 0.35f);
                m.SetFloat("_EmissionPulseSpeed", 5f);
                m.SetColor("_ShadowTint", new Color(0.30f, 0.27f, 0.50f));
                m.SetColor("_RimColor", new Color(0.55f, 0.85f, 1.05f));
                m.SetFloat("_RimStrength", 0.7f);
                m.SetFloat("_RimLightStrength", 1.6f);
                m.SetFloat("_OutlinePixels", 1f);
                m.SetColor("_OutlineColor", new Color(0.03f, 0.02f, 0.07f));
                m.SetFloat("_GlintThreshold", 0.45f);
                m.SetFloat("_GlintIntensity", 1.6f);
            });
            Mat("M_BeheadedFlame", "DeadCells/Flame", m =>
            {
                m.SetColor("_CoreColor", new Color(4.2f, 3.6f, 4.6f));
                m.SetColor("_FlameColor", new Color(2.4f, 1.1f, 4.2f));
                m.SetColor("_TipColor", new Color(0.55f, 0.12f, 1.1f));
                m.SetFloat("_Intensity", 1.5f);
            });
            Mat("M_BeheadedEye", "DeadCells/UnlitHDR", m => m.SetColor("_Color", new Color(6f, 5.4f, 4.2f)));
            Mat("M_BeheadedSmoke", "DeadCells/Smoke", m =>
            {
                m.SetColor("_GlowColor", purpleGlow * 1.4f);
                m.SetFloat("_Opacity", 0.42f);
            });

            var cool = new Color(0.24f, 0.30f, 0.38f);
            CharacterMat("M_Zombie", $"{CharDir}/Zombie/Textures", "Zombie", new Color(3.2f, 1.5f, 0.35f), cool, new Color(0.5f, 0.9f, 0.7f), 0.45f);
            CharacterMat("M_Sentinel", $"{CharDir}/Sentinel/Textures", "Sentinel", new Color(2.6f, 1.9f, 0.7f), cool, new Color(0.6f, 0.8f, 1f));
            CharacterMat("M_Monk", $"{CharDir}/Monk/Textures", "Monk", new Color(1.3f, 3f, 1.0f), new Color(0.22f, 0.3f, 0.24f), new Color(0.7f, 1f, 0.6f));
            CharacterMat("M_Fisher", $"{CharDir}/Fisher/Textures", "Fisher", new Color(1.1f, 2.1f, 3.4f), new Color(0.26f, 0.22f, 0.36f), new Color(0.6f, 0.8f, 1.1f));
            CharacterMat("M_RoyalGuardian", $"{CharDir}/RoyalGuardian/Textures", "RoyalGuardian", new Color(3f, 2.2f, 0.8f), new Color(0.26f, 0.24f, 0.32f), new Color(1f, 0.85f, 0.6f), 0.6f, 1.25f);
            CharacterMat("M_TimeKeeper", $"{CharDir}/TimeKeeper/Textures", "TimeKeeper", new Color(3.4f, 3f, 1.7f), new Color(0.22f, 0.22f, 0.38f), new Color(1f, 0.9f, 0.6f), 0.6f, 1.25f);
            CharacterMat("M_Creatures", $"{CharDir}/Creatures/Textures", "Creatures", new Color(1.5f, 2.8f, 0.9f), new Color(0.24f, 0.28f, 0.3f), new Color(0.7f, 1f, 0.7f));
            CharacterMat("M_Greatsword", $"{CharDir}/RoyalGuardian/Textures", "Greatsword", new Color(2.8f, 2f, 0.8f), cool, new Color(1f, 0.9f, 0.7f), 0.5f, 0.75f);
            CharacterMat("M_Shovel", $"{CharDir}/TimeKeeper/Textures", "Shovel", new Color(3.4f, 3f, 1.8f), cool, new Color(1f, 0.9f, 0.6f), 0.5f, 0.75f);
            Mat("M_Weapons", "DeadCells/CharacterLit", m =>
            {
                Textures(m, $"{WeaponDir}/Textures", "Weapons");
                m.SetColor("_EmissionColor", new Color(0.5f, 2.6f, 2.4f));
                m.SetFloat("_EmissionPulseAmp", 0.4f);
                m.SetFloat("_EmissionPulseSpeed", 7f);
                m.SetFloat("_OutlinePixels", 0.75f);
                m.SetFloat("_GlintThreshold", 0.35f);
                m.SetFloat("_GlintIntensity", 2.2f);
            });
            Mat("M_Arsenal", "DeadCells/CharacterLit", m =>
            {
                Textures(m, $"{ArsenalDir}/Textures", "Arsenal");
                m.SetColor("_EmissionColor", new Color(2.6f, 1.5f, 0.6f));
                m.SetFloat("_EmissionPulseAmp", 0.35f);
                m.SetFloat("_EmissionPulseSpeed", 6f);
                m.SetFloat("_OutlinePixels", 0.75f);
                m.SetFloat("_GlintThreshold", 0.35f);
                m.SetFloat("_GlintIntensity", 2.2f);
            });
            CharacterMat("M_Props", $"{PropsDir}/Textures", "Props", new Color(1.6f, 1.0f, 2.8f), new Color(0.24f, 0.26f, 0.36f), new Color(0.6f, 0.8f, 1f), 0.35f, 0.75f);

            // Environment: the Oubliette kit plus one set per biome kit.
            Mat("M_ENV_Kit", "DeadCells/EnvironmentLit", m =>
            {
                Textures(m, $"{EnvDir}/Textures", "ENV_Kit");
                m.SetColor("_EmissionColor", new Color(3.5f, 1.4f, 0.35f));
                EnvironmentLook(m, 1f);
            });
            Mat("M_ENV_Wall", "DeadCells/EnvironmentLit", m =>
            {
                Textures(m, $"{EnvDir}/Textures", "ENV_Kit");
                m.SetColor("_EmissionColor", new Color(3.5f, 1.4f, 0.35f));
                EnvironmentLook(m, 0.62f);
                m.SetFloat("_BumpScale", 0.55f);
            });
            BackgroundMat("M_BG_Kit", $"{EnvDir}/Textures", "BG_Kit", new Color(0.6f, 2.2f, 2f));
            Unlit("M_ENV_Deep", new Color(0.012f, 0.02f, 0.026f));
            var kitEmission = new Dictionary<string, Color>
            {
                ["Promenade"] = new Color(1.3f, 1.8f, 2.6f),
                ["Ossuary"] = new Color(1.2f, 2.6f, 0.9f),
                ["StiltVillage"] = new Color(2.6f, 1.2f, 2.2f),
                ["ClockLung"] = new Color(3.2f, 2.2f, 0.8f),
            };
            var deep = new Dictionary<string, Color>
            {
                ["Promenade"] = new Color(0.014f, 0.014f, 0.035f),
                ["Ossuary"] = new Color(0.022f, 0.022f, 0.018f),
                ["StiltVillage"] = new Color(0.03f, 0.012f, 0.032f),
                ["ClockLung"] = new Color(0.03f, 0.018f, 0.01f),
            };
            foreach (var id in KitBiomes)
            {
                string tex = $"{BiomeArtDir}/{id}/Textures";
                Mat($"M_{id}_Kit", "DeadCells/EnvironmentLit", m =>
                {
                    Textures(m, tex, $"{id}_Kit");
                    m.SetColor("_EmissionColor", kitEmission[id]);
                    EnvironmentLook(m, 1f);
                });
                Mat($"M_{id}_Wall", "DeadCells/EnvironmentLit", m =>
                {
                    Textures(m, tex, $"{id}_Kit");
                    m.SetColor("_EmissionColor", kitEmission[id]);
                    EnvironmentLook(m, 0.62f);
                    m.SetFloat("_BumpScale", 0.55f);
                });
                BackgroundMat($"M_{id}_BG", tex, $"{id}_BG", kitEmission[id] * 0.9f);
                Unlit($"M_{id}_Deep", deep[id]);
            }

            // Liquids.
            Unlit("M_Liquid_Water", new Color(0.05f, 0.13f, 0.14f), 0.12f, 1.5f);
            Unlit("M_Liquid_Wine", new Color(1.0f, 0.28f, 1.35f), 0.2f, 2.2f);
            Unlit("M_Liquid_Void", new Color(0.02f, 0.025f, 0.08f), 0.3f, 0.8f);
            Unlit("M_Liquid_Brass", new Color(3.4f, 1.5f, 0.35f), 0.25f, 3f);
            Unlit("M_Liquid_Tallow", new Color(0.7f, 1.9f, 0.35f), 0.2f, 1.8f);

            // FX.
            Mat("M_SlashArc", "DeadCells/SlashArc", m => { });
            Mat("M_LightShaft", "DeadCells/LightShaft", m => { });
            Mat("M_PixelText", "DeadCells/PixelSprite", m => m.SetFloat("_ZTest", (float)CompareFunction.Always));
            Particle("M_FX_Additive", (float)BlendMode.One, (float)BlendMode.One, 0f);
            Particle("M_FX_Flash", (float)BlendMode.One, (float)BlendMode.One, 1f, 0.9f);
            Particle("M_FX_Alpha", (float)BlendMode.SrcAlpha, (float)BlendMode.OneMinusSrcAlpha, 2f);
            Particle("M_FX_Dust", (float)BlendMode.SrcAlpha, (float)BlendMode.OneMinusSrcAlpha, 1f, 1f);
            Unlit("M_FX_OrbGreen", new Color(1.6f, 3.6f, 1.3f), 0.25f, 10f);
            Unlit("M_FX_Star", new Color(4.2f, 3.8f, 2.4f), 0.2f, 12f);
            Unlit("M_FX_Ring", new Color(2.4f, 1.1f, 3.6f), 0.2f, 9f);
            Unlit("M_FX_Shock", new Color(3.4f, 2.3f, 0.9f), 0.2f, 14f);
            Unlit("M_FX_Crystal", new Color(1.6f, 2.3f, 3.4f), 0.15f, 6f);
            Unlit("M_FX_Cell", new Color(0.6f, 2.6f, 3.6f), 0.3f, 7f);
            Unlit("M_FX_Blueprint", new Color(0.7f, 1.6f, 3.4f), 0.35f, 5f);
            Mat("M_Spikes", "DeadCells/EnvironmentLit", m =>
            {
                m.SetTexture("_ORMMap", SolidTexture("T_ORM_Iron", new Color(1f, 0.5f, 0.85f), true));
                m.SetTexture("_BaseMap", null);
                EnvironmentLook(m, 0.42f);
                m.SetColor("_BaseColor", new Color(0.34f, 0.31f, 0.3f));
                m.SetColor("_EmissionColor", Color.black);
            });
            Mat("M_Coals", "DeadCells/UnlitHDR", m =>
            {
                m.SetColor("_Color", new Color(4f, 1.5f, 0.3f));
                m.SetFloat("_PulseAmp", 0.25f);
                m.SetFloat("_PulseSpeed", 9f);
            });
            Mat("M_TorchFlame", "DeadCells/Flame", m =>
            {
                m.SetColor("_CoreColor", new Color(5f, 4.2f, 2.4f));
                m.SetColor("_FlameColor", new Color(4.2f, 1.6f, 0.35f));
                m.SetColor("_TipColor", new Color(1.4f, 0.22f, 0.05f));
                m.SetFloat("_Intensity", 1.4f);
                m.SetFloat("_WobbleAmp", 0.03f);
            });
        }

        /// <summary>
        /// Shared environment grading: grazing-angle rims and glints stay low so
        /// floor tops and brick bevels don't flare under the key light, and
        /// light falloff stays smooth (banding is reserved for characters).
        /// </summary>
        static void EnvironmentLook(Material m, float brightness)
        {
            m.SetColor("_BaseColor", new Color(brightness, brightness * 1.02f, brightness * 1.06f));
            m.SetFloat("_EmissionPulseAmp", 0.25f);
            m.SetColor("_ShadowTint", new Color(0.20f, 0.27f, 0.40f));
            m.SetColor("_RimColor", new Color(0.35f, 0.75f, 0.85f));
            // No view-dependent hard-stepped terms on static scenery: rims and
            // glints on brick bevels toggle on/off as the camera moves (jumps
            // made the wall lighting flash). Characters keep them.
            m.SetFloat("_RimStrength", 0f);
            m.SetFloat("_RimThreshold", 0.55f);
            m.SetFloat("_RimLightStrength", 0f);
            m.SetFloat("_GlintIntensity", 0f);
            m.SetFloat("_GlintThreshold", 0.7f);
            m.SetFloat("_BumpScale", 0.75f);
            m.SetFloat("_AttenBands", 0f);
            m.SetFloat("_RampSmooth", 0.15f); // soft terminator: moving lights glide over bevels instead of popping
            m.SetFloat("_LightGlow", 0.05f);
            m.SetFloat("_AmbientStrength", 0.5f);
            m.SetFloat("_FogAmount", 1f);
            m.SetFloat("_TopShade", 0.55f);
        }

        static Material BackgroundMat(string name, string dir, string prefix, Color emission) => Mat(name, "DeadCells/EnvironmentLit", m =>
        {
            Textures(m, dir, prefix);
            EnvironmentLook(m, 1f);
            m.SetColor("_EmissionColor", emission);
            m.SetFloat("_AmbientStrength", 0.4f);
            m.SetFloat("_RimStrength", 0.2f);
            m.SetFloat("_OutlinePixels", 0f);
        });

        // -------------------------------------------------------- controllers

        public static AnimatorController BuildController(string name, string fbxPath, string defaultState)
        {
            string path = $"{AnimDir}/{name}.controller";
            AssetDatabase.DeleteAsset(path);
            var controller = AnimatorController.CreateAnimatorControllerAtPath(path);
            var sm = controller.layers[0].stateMachine;
            var clips = AssetDatabase.LoadAllAssetsAtPath(fbxPath).OfType<AnimationClip>()
                .Where(c => !c.name.StartsWith("__preview__")).OrderBy(c => c.name).ToArray();
            int i = 0;
            foreach (var clip in clips)
            {
                var st = sm.AddState(clip.name, new Vector3(300f, 60f * i++, 0f));
                st.motion = clip;
                st.writeDefaultValues = true;
                if (clip.name == defaultState)
                    sm.defaultState = st;
            }
            EditorUtility.SetDirty(controller);
            Debug.Log($"[DC] controller {name}: {string.Join(", ", clips.Select(c => $"{c.name}({c.length * 60f:F0}f{(c.isLooping ? ",loop" : "")})"))}");
            return controller;
        }

        public static void BuildControllers()
        {
            foreach (var c in RiggedCharacters)
                BuildController(c, $"{CharDir}/{c}/{c}.fbx", "Idle");
        }
    }
}
