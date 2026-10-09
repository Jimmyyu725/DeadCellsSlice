using System.Collections.Generic;
using System.IO;
using System.Linq;
using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.Enemies;
using DeadCells.Environment;
using DeadCells.FX;
using DeadCells.Player;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using UnityEngine.Rendering;

namespace DeadCells.EditorTools
{
    /// <summary>
    /// Generates materials, animator controllers and prefabs from the assets
    /// the Blender pipeline exported. Idempotent: rerunning updates in place.
    /// </summary>
    public static class DCContentBuilder
    {
        public const string Root = "Assets/_Project";
        public const string MatDir = Root + "/Materials";
        public const string AnimDir = Root + "/Animation";
        public const string PrefabDir = Root + "/Prefabs";
        const string CharDir = Root + "/Art/Characters";
        const string WeaponDir = Root + "/Art/Weapons";
        const string EnvDir = Root + "/Art/Environment";

        [MenuItem("Dead Cells/Setup/2 Build Content")]
        public static void BuildAll()
        {
            Directory.CreateDirectory(MatDir);
            Directory.CreateDirectory(AnimDir);
            Directory.CreateDirectory(PrefabDir);
            AssetDatabase.Refresh();
            // Re-run the import rules on the characters so clip settings always match the postprocessor.
            foreach (var fbx in new[] { $"{CharDir}/Beheaded/Beheaded.fbx", $"{CharDir}/Zombie/Zombie.fbx" })
                AssetDatabase.ImportAsset(fbx, ImportAssetOptions.ForceUpdate);
            foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { $"{EnvDir}/Meshes" }))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                if (AssetImporter.GetAtPath(path) is ModelImporter mi && !mi.isReadable)
                    AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            }
            BuildMaterials();
            BuildControllers();
            BuildWeaponPrefabs();
            BuildPlayerPrefab();
            BuildZombiePrefab();
            BuildTorchPrefab();
            AssetDatabase.SaveAssets();
            Debug.Log("[DC] content built");
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

        static GameObject Model(string path) => AssetDatabase.LoadAssetAtPath<GameObject>(path);

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

        // ---------------------------------------------------------- materials

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
            Mat("M_Zombie", "DeadCells/CharacterLit", m =>
            {
                Textures(m, $"{CharDir}/Zombie/Textures", "Zombie");
                m.SetColor("_EmissionColor", new Color(3.2f, 1.5f, 0.35f));
                m.SetFloat("_EmissionPulseAmp", 0.3f);
                m.SetFloat("_EmissionPulseSpeed", 3f);
                m.SetColor("_ShadowTint", new Color(0.24f, 0.30f, 0.38f));
                m.SetColor("_RimColor", new Color(0.5f, 0.9f, 0.7f));
                m.SetFloat("_RimStrength", 0.45f);
                m.SetFloat("_OutlinePixels", 1f);
            });
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
            Mat("M_ENV_Kit", "DeadCells/EnvironmentLit", m =>
            {
                Textures(m, $"{EnvDir}/Textures", "ENV_Kit");
                m.SetColor("_EmissionColor", new Color(3.5f, 1.4f, 0.35f));
                m.SetFloat("_EmissionPulseAmp", 0.25f);
                EnvironmentLook(m, 1f);
            });
            Mat("M_ENV_Wall", "DeadCells/EnvironmentLit", m =>
            {
                Textures(m, $"{EnvDir}/Textures", "ENV_Kit");
                m.SetColor("_EmissionColor", new Color(3.5f, 1.4f, 0.35f));
                EnvironmentLook(m, 0.62f);
                m.SetFloat("_BumpScale", 0.55f);
            });
            Mat("M_SlashArc", "DeadCells/SlashArc", m => { });
            Mat("M_LightShaft", "DeadCells/LightShaft", m => { });
            Mat("M_PixelText", "DeadCells/PixelSprite", m => m.SetFloat("_ZTest", (float)CompareFunction.Always));
            Particle("M_FX_Additive", (float)BlendMode.One, (float)BlendMode.One, 0f);
            Particle("M_FX_Flash", (float)BlendMode.One, (float)BlendMode.One, 1f, 0.9f);
            Particle("M_FX_Alpha", (float)BlendMode.SrcAlpha, (float)BlendMode.OneMinusSrcAlpha, 2f);
            Particle("M_FX_Dust", (float)BlendMode.SrcAlpha, (float)BlendMode.OneMinusSrcAlpha, 1f, 1f);
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
            BuildController("Beheaded", $"{CharDir}/Beheaded/Beheaded.fbx", "Idle");
            BuildController("Zombie", $"{CharDir}/Zombie/Zombie.fbx", "Idle");
        }

        // ------------------------------------------------------------ weapons

        static GameObject SaveVariant(GameObject instance, string name)
        {
            string path = $"{PrefabDir}/{name}.prefab";
            var prefab = PrefabUtility.SaveAsPrefabAsset(instance, path);
            Object.DestroyImmediate(instance);
            return prefab;
        }

        static void AssignAll(GameObject go, Material m)
        {
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                r.sharedMaterial = m;
        }

        public static void BuildWeaponPrefabs()
        {
            var weapons = LoadMat("M_Weapons");
            foreach (var (name, tip) in new[] { ("RustySword", 0.78f), ("Broadsword", 1.32f), ("FrontlineShield", 0f) })
            {
                var go = (GameObject)PrefabUtility.InstantiatePrefab(Model($"{WeaponDir}/{name}.fbx"));
                PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.OutermostRoot, InteractionMode.AutomatedAction);
                go.name = name;
                AssignAll(go, weapons);
                foreach (var r in go.GetComponentsInChildren<MeshRenderer>())
                    r.shadowCastingMode = ShadowCastingMode.On;
                if (tip > 0f)
                {
                    new GameObject("BladeBase").transform.SetParent(go.transform, false);
                    go.transform.Find("BladeBase").localPosition = new Vector3(0f, 0.09f, 0f);
                    var t = new GameObject("BladeTip").transform;
                    t.SetParent(go.transform, false);
                    t.localPosition = new Vector3(0f, tip, 0f);
                }
                SaveVariant(go, name);
            }
        }

        // ------------------------------------------------------------- player

        static (GameObject root, Transform facing, Transform squash, Transform yaw, GameObject model) Rig(
            string name, string fbx, string controller, float modelScale)
        {
            var root = new GameObject(name);
            var facing = new GameObject("Visual").transform;
            facing.SetParent(root.transform, false);
            var squash = new GameObject("Squash").transform;
            squash.SetParent(facing, false);
            var yaw = new GameObject("Yaw").transform;
            yaw.SetParent(squash, false);
            var model = (GameObject)PrefabUtility.InstantiatePrefab(Model(fbx));
            PrefabUtility.UnpackPrefabInstance(model, PrefabUnpackMode.OutermostRoot, InteractionMode.AutomatedAction);
            model.transform.SetParent(yaw, false);
            model.transform.localScale = Vector3.one * modelScale;
            var animator = model.GetComponent<Animator>() ?? model.AddComponent<Animator>();
            animator.runtimeAnimatorController = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>($"{AnimDir}/{controller}.controller");
            animator.applyRootMotion = false;
            animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            animator.updateMode = AnimatorUpdateMode.Normal;
            return (root, facing, squash, yaw, model);
        }

        /// <summary>
        /// Parents `item` to `socket` so that, in the model's bind pose, the item's
        /// local axes point along the given model-space directions.
        /// </summary>
        static void Attach(Transform item, Transform socket, Transform modelRoot, Vector3 primaryModel, Vector3 secondaryModel, Vector3 offsetModel)
        {
            // Item convention: +Y primary (blade / shield facing), +X secondary.
            Vector3 zModel = Vector3.Cross(secondaryModel, primaryModel);
            Quaternion modelRot = Quaternion.LookRotation(zModel, primaryModel);
            item.SetPositionAndRotation(socket.position + modelRoot.TransformVector(offsetModel), modelRoot.rotation * modelRot);
            item.SetParent(socket, true);
        }

        public static void BuildPlayerPrefab()
        {
            var (root, facing, squash, yaw, model) = Rig("Player", $"{CharDir}/Beheaded/Beheaded.fbx", "Beheaded", 1f);
            root.layer = DCLayers.Player;
            yaw.localRotation = Quaternion.Euler(0f, -65f, 0f);

            // Materials per sub-mesh object.
            foreach (var r in model.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                r.updateWhenOffscreen = true;
                r.sharedMaterial = r.name switch
                {
                    "Beheaded_Flame" => LoadMat("M_BeheadedFlame"),
                    "Beheaded_Eye" => LoadMat("M_BeheadedEye"),
                    "Beheaded_Smoke" => LoadMat("M_BeheadedSmoke"),
                    _ => LoadMat("M_Beheaded"),
                };
                r.shadowCastingMode = r.name == "Beheaded_Body" ? ShadowCastingMode.On : ShadowCastingMode.Off;
            }

            // Weapons into the sockets (bind pose).
            Transform weaponSocket = Find(model.transform, "weapon_socket");
            Transform shieldSocket = Find(model.transform, "shield_socket");
            Transform headSocket = Find(model.transform, "head_socket");
            var rusty = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>($"{PrefabDir}/RustySword.prefab"));
            var broad = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>($"{PrefabDir}/Broadsword.prefab"));
            var shield = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>($"{PrefabDir}/FrontlineShield.prefab"));
            // Model space: character faces -Z, up +Y, its left is +X.
            Attach(rusty.transform, weaponSocket, model.transform, new Vector3(0, 0, -1), Vector3.up, Vector3.zero);
            Attach(broad.transform, weaponSocket, model.transform, new Vector3(0, 0, -1), Vector3.up, Vector3.zero);
            Attach(shield.transform, shieldSocket, model.transform, new Vector3(0, 0, 1), Vector3.right, new Vector3(0.03f, 0f, 0.03f));

            // Flame light.
            var flameLight = new GameObject("FlameLight").AddComponent<Light>();
            flameLight.transform.SetParent(headSocket, false);
            flameLight.transform.localPosition = Vector3.zero;
            flameLight.type = LightType.Point;
            flameLight.color = new Color(0.61f, 0.36f, 0.9f);
            flameLight.intensity = 2.2f;
            flameLight.range = 4.5f;
            flameLight.shadows = LightShadows.None;

            // Physics.
            var body = root.AddComponent<Rigidbody2D>();
            body.bodyType = RigidbodyType2D.Dynamic;
            body.gravityScale = 0f;
            body.freezeRotation = true;
            body.interpolation = RigidbodyInterpolation2D.Interpolate;
            body.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
            var col = root.AddComponent<CapsuleCollider2D>();
            col.size = new Vector2(0.56f, 1.72f);
            col.offset = new Vector2(0f, 0.86f);
            col.direction = CapsuleDirection2D.Vertical;
            col.sharedMaterial = NoFriction();

            var health = root.AddComponent<Health>();
            health.maxHealth = 228f;
            root.AddComponent<GameInput>();
            var anim = root.AddComponent<CharacterAnimator>();
            anim.animator = model.GetComponent<Animator>();
            anim.facingPivot = facing;
            anim.yawPivot = yaw;
            anim.yawFacingRight = -65f;
            var sq = squash.gameObject.AddComponent<SquashStretch>();
            var flash = root.AddComponent<HitFlash>();
            flash.renderers = model.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r => r.name == "Beheaded_Body").Cast<Renderer>()
                .Concat(new Renderer[] { rusty.GetComponentInChildren<Renderer>(), broad.GetComponentInChildren<Renderer>() }).ToArray();

            // Secondary motion on the scarf and tunic tails.
            var sec = model.AddComponent<SecondaryMotion>();
            sec.chains = new List<SecondaryMotion.Chain>
            {
                new SecondaryMotion.Chain { name = "Scarf", bones = Bones(model.transform, "scarf_01", "scarf_02", "scarf_03", "scarf_04"), stiffness = 0.16f, damping = 0.86f, gravity = 3f },
                new SecondaryMotion.Chain { name = "CoatL", bones = Bones(model.transform, "coat_L_01", "coat_L_02", "coat_L_03"), stiffness = 0.3f, damping = 0.8f, gravity = 3f },
                new SecondaryMotion.Chain { name = "CoatR", bones = Bones(model.transform, "coat_R_01", "coat_R_02", "coat_R_03"), stiffness = 0.3f, damping = 0.8f, gravity = 3f },
            };

            // Slash arc renderer (world space).
            var arcGo = new GameObject("SlashArc", typeof(MeshFilter), typeof(MeshRenderer));
            arcGo.transform.SetParent(root.transform, false);
            arcGo.layer = DCLayers.Fx;
            arcGo.GetComponent<MeshRenderer>().sharedMaterial = LoadMat("M_SlashArc");
            var arc = arcGo.AddComponent<SlashArc>();
            arc.pivot = Find(model.transform, "upper_arm.R");

            var controller = root.AddComponent<PlayerController>();
            controller.anim = anim;
            controller.squash = sq;
            controller.hitFlash = flash;
            controller.flameRenderer = model.GetComponentsInChildren<SkinnedMeshRenderer>(true).First(r => r.name == "Beheaded_Flame");
            controller.secondaryMotion = sec;

            var combat = root.AddComponent<PlayerCombat>();
            combat.slashArc = arc;
            combat.shieldVisual = shield;
            combat.weapons = new[]
            {
                new WeaponProfile
                {
                    displayName = "Rusty Sword",
                    visual = rusty,
                    bladeBase = rusty.transform.Find("BladeBase"),
                    bladeTip = rusty.transform.Find("BladeTip"),
                    animSpeed = 1.05f,
                    arcColor = new Color(0.9f, 2.4f, 3.2f),
                    arcCore = new Color(5f, 6f, 6.5f),
                    sparkColor = new Color(2.2f, 2.6f, 3f),
                    combo = new[]
                    {
                        new AttackStep { clip = "Slash_Combo_1", totalFrames = 18, activeFrames = new Vector2Int(4, 7), cancelFrame = 8, lungeFrames = new Vector2Int(3, 6), lungeSpeed = 4.5f, damage = 13, hitboxOffset = new Vector2(1.15f, 1.0f), hitboxSize = new Vector2(2.3f, 1.8f), knockback = 4f, stun = 0.15f, hitStopWeight = 0.25f, shake = 0.16f },
                        new AttackStep { clip = "Slash_Combo_2", totalFrames = 18, activeFrames = new Vector2Int(4, 7), cancelFrame = 8, lungeFrames = new Vector2Int(3, 6), lungeSpeed = 4.5f, damage = 15, hitboxOffset = new Vector2(1.1f, 1.3f), hitboxSize = new Vector2(2.2f, 2.3f), knockback = 4.5f, stun = 0.15f, hitStopWeight = 0.35f, shake = 0.2f },
                        new AttackStep { clip = "Slash_Combo_3", totalFrames = 24, activeFrames = new Vector2Int(5, 9), cancelFrame = 13, lungeFrames = new Vector2Int(4, 8), lungeSpeed = 7f, damage = 22, hitboxOffset = new Vector2(1.3f, 0.9f), hitboxSize = new Vector2(2.7f, 2.0f), knockback = 9f, stun = 0.35f, hitStopWeight = 1f, shake = 0.45f, critical = true },
                    },
                },
                new WeaponProfile
                {
                    displayName = "Broadsword",
                    visual = broad,
                    bladeBase = broad.transform.Find("BladeBase"),
                    bladeTip = broad.transform.Find("BladeTip"),
                    animSpeed = 0.72f,
                    arcColor = new Color(3.2f, 1.6f, 0.4f),
                    arcCore = new Color(6.5f, 5.5f, 3.5f),
                    sparkColor = new Color(3f, 2f, 0.8f),
                    combo = new[]
                    {
                        new AttackStep { clip = "Slash_Combo_1", totalFrames = 18, activeFrames = new Vector2Int(4, 8), cancelFrame = 9, lungeFrames = new Vector2Int(3, 6), lungeSpeed = 3.5f, damage = 30, hitboxOffset = new Vector2(1.5f, 1.0f), hitboxSize = new Vector2(3.0f, 2.2f), knockback = 7f, stun = 0.3f, hitStopWeight = 0.7f, shake = 0.35f },
                        new AttackStep { clip = "Slash_Combo_3", totalFrames = 24, activeFrames = new Vector2Int(5, 10), cancelFrame = 14, lungeFrames = new Vector2Int(4, 8), lungeSpeed = 5f, damage = 46, hitboxOffset = new Vector2(1.6f, 0.9f), hitboxSize = new Vector2(3.3f, 2.4f), knockback = 12f, stun = 0.5f, hitStopWeight = 1f, shake = 0.6f, critical = true },
                    },
                },
            };

            // Camera follow target.
            var camTarget = new GameObject("CameraTarget").transform;
            camTarget.SetParent(root.transform, false);
            camTarget.localPosition = new Vector3(0f, 1.3f, 0f);

            SaveVariant(root, "Player");
        }

        static Transform[] Bones(Transform root, params string[] names) => names.Select(n => Find(root, n)).Where(t => t != null).ToArray();

        static PhysicsMaterial2D NoFriction()
        {
            string path = $"{Root}/Rendering/PM_NoFriction.physicsMaterial2D";
            var m = AssetDatabase.LoadAssetAtPath<PhysicsMaterial2D>(path);
            if (m == null)
            {
                Directory.CreateDirectory($"{Root}/Rendering");
                m = new PhysicsMaterial2D("NoFriction") { friction = 0f, bounciness = 0f };
                AssetDatabase.CreateAsset(m, path);
            }
            return m;
        }

        // ------------------------------------------------------------- zombie

        public static void BuildZombiePrefab()
        {
            var (root, facing, squash, yaw, model) = Rig("Zombie", $"{CharDir}/Zombie/Zombie.fbx", "Zombie", 1.12f);
            root.layer = DCLayers.Enemy;
            yaw.localRotation = Quaternion.Euler(0f, -65f, 0f);
            foreach (var r in model.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                r.sharedMaterial = LoadMat("M_Zombie");
                r.updateWhenOffscreen = true;
                r.shadowCastingMode = ShadowCastingMode.On;
            }
            var body = root.AddComponent<Rigidbody2D>();
            body.bodyType = RigidbodyType2D.Dynamic;
            body.gravityScale = 3.2f;
            body.freezeRotation = true;
            body.interpolation = RigidbodyInterpolation2D.Interpolate;
            var col = root.AddComponent<CapsuleCollider2D>();
            col.size = new Vector2(0.62f, 1.62f);
            col.offset = new Vector2(0f, 0.81f);
            col.sharedMaterial = NoFriction();
            var health = root.AddComponent<Health>();
            health.maxHealth = 70f;
            var anim = root.AddComponent<CharacterAnimator>();
            anim.animator = model.GetComponent<Animator>();
            anim.facingPivot = facing;
            anim.yawPivot = yaw;
            var flash = root.AddComponent<HitFlash>();
            flash.renderers = model.GetComponentsInChildren<Renderer>(true);
            var sq = squash.gameObject.AddComponent<SquashStretch>();
            var sec = model.AddComponent<SecondaryMotion>();
            sec.chains = new List<SecondaryMotion.Chain>
            {
                new SecondaryMotion.Chain { name = "RagL", bones = Bones(model.transform, "coat_L_01", "coat_L_02", "coat_L_03"), stiffness = 0.25f, damping = 0.82f, gravity = 3f },
                new SecondaryMotion.Chain { name = "RagR", bones = Bones(model.transform, "coat_R_01", "coat_R_02", "coat_R_03"), stiffness = 0.25f, damping = 0.82f, gravity = 3f },
            };
            var z = root.AddComponent<ZombieEnemy>();
            z.anim = anim;
            z.hitFlash = flash;
            z.squash = sq;
            SaveVariant(root, "Zombie");
        }

        // -------------------------------------------------------------- torch

        public static void BuildTorchPrefab()
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(Model($"{EnvDir}/Meshes/ENV_Torch.fbx"));
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.OutermostRoot, InteractionMode.AutomatedAction);
            go.name = "Torch";
            AssignAll(go, LoadMat("M_ENV_Kit"));
            Transform socket = Find(go.transform, "FlameSocket");
            Vector3 flamePos = socket != null ? go.transform.InverseTransformPoint(socket.position) : new Vector3(0f, 0.795f, -0.495f);

            // Flame: the Beheaded's flame-cluster mesh reused at torch scale.
            var flameMesh = AssetDatabase.LoadAllAssetsAtPath($"{CharDir}/Beheaded/Beheaded.fbx").OfType<Mesh>().FirstOrDefault(m => m.name == "Beheaded_Flame");
            var flame = new GameObject("TorchFlame", typeof(MeshFilter), typeof(MeshRenderer));
            flame.transform.SetParent(go.transform, false);
            flame.GetComponent<MeshFilter>().sharedMesh = flameMesh;
            flame.GetComponent<MeshRenderer>().sharedMaterial = LoadMat("M_TorchFlame");
            flame.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
            // Flame mesh base sits ~1.5 m up in character space; recentre and shrink.
            flame.transform.localScale = Vector3.one * 0.62f;
            flame.transform.localPosition = flamePos - new Vector3(0f, 1.515f * 0.62f, 0f);

            var lightGo = new GameObject("TorchLight");
            lightGo.transform.SetParent(go.transform, false);
            lightGo.transform.localPosition = flamePos + new Vector3(0f, 0.15f, -0.25f);
            var l = lightGo.AddComponent<Light>();
            l.type = LightType.Point;
            l.color = new Color(1f, 0.55f, 0.22f);
            l.intensity = 4f;
            l.range = 6.5f;
            l.shadows = LightShadows.None;
            var flicker = lightGo.AddComponent<TorchFlicker>();
            flicker.baseIntensity = 4f;
            flicker.baseRange = 6.5f;
            flicker.intensityJitter = 0.1f;
            flicker.rangeJitter = 0.04f;
            flicker.speed = 3.5f;
            flicker.wobble = 0f;

            var embers = TorchEmbers(go.transform);
            embers.transform.localPosition = flamePos + Vector3.up * 0.1f;
            SaveVariant(go, "Torch");
        }

        static ParticleSystem TorchEmbers(Transform parent)
        {
            var go = new GameObject("TorchEmbers");
            go.transform.SetParent(parent, false);
            go.layer = DCLayers.Fx;
            var ps = go.AddComponent<ParticleSystem>();
            var main = ps.main;
            main.loop = true;
            main.playOnAwake = true;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.startLifetime = new ParticleSystem.MinMaxCurve(0.5f, 1.2f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.4f, 1.4f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.03f, 0.06f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(3.5f, 1.4f, 0.3f), new Color(4f, 2.4f, 0.6f));
            main.gravityModifier = -0.35f;
            main.maxParticles = 64;
            var emission = ps.emission;
            emission.rateOverTime = 9f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Sphere;
            shape.radius = 0.08f;
            var noise = ps.noise;
            noise.enabled = true;
            noise.strength = 0.7f;
            noise.frequency = 1.6f;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 1f), new Keyframe(1f, 0f)));
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = LoadMat("M_FX_Additive");
            r.renderMode = ParticleSystemRenderMode.Stretch;
            r.velocityScale = 0.08f;
            r.lengthScale = 1.4f;
            r.shadowCastingMode = ShadowCastingMode.Off;
            return ps;
        }
    }
}
