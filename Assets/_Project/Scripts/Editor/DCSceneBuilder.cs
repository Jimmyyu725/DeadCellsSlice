using System.IO;
using System.Linq;
using DeadCells.CameraRig;
using DeadCells.Core;
using DeadCells.Environment;
using DeadCells.FX;
using DeadCells.Player;
using DeadCells.Rendering;
using DeadCells.Run;
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
    /// Builds the two scenes: MainMenu (title diorama + menus) and Game (camera
    /// rig, player, run manager, map, HUD and in-game UI). Levels themselves
    /// are generated at runtime from the room templates and biome kits.
    /// </summary>
    public static class DCSceneBuilder
    {
        public const string MenuScenePath = "Assets/_Project/Scenes/MainMenu.unity";
        public const string GameScenePath = "Assets/_Project/Scenes/Game.unity";
        const string LegacyScene = "Assets/_Project/Scenes/PrisonersQuarters.unity";
        const string ContentDir = DCContentBuilder.ContentDir;

        public static string[] Scenes => new[] { MenuScenePath, GameScenePath };

        [UnityEditor.MenuItem("Dead Cells/Setup/3 Build Scenes")]
        public static void BuildScene()
        {
            Directory.CreateDirectory(Path.GetDirectoryName(MenuScenePath));
            AssetDatabase.DeleteAsset(LegacyScene);
            BuildMenu();
            BuildGame();
            EditorBuildSettings.scenes = Scenes.Select(s => new EditorBuildSettingsScene(s, true)).ToArray();
            Debug.Log("[DC] scenes built: " + string.Join(", ", Scenes));
        }

        static BiomeDef Biome(string id) => AssetDatabase.LoadAssetAtPath<BiomeDef>($"{ContentDir}/Biomes/{id}.asset");

        static (Light key, Light rim) BuildLights()
        {
            var lights = new GameObject("Lighting").transform;
            var key = new GameObject("KeyLight").AddComponent<Light>();
            key.transform.SetParent(lights, false);
            key.type = LightType.Directional;
            key.transform.rotation = Quaternion.Euler(20f, 24f, 0f);
            key.color = new Color(0.62f, 0.82f, 1f);
            key.intensity = 0.65f;
            key.shadows = LightShadows.Soft;
            key.shadowStrength = 0.85f;
            key.gameObject.AddComponent<UniversalAdditionalLightData>().usePipelineSettings = true;

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
            volume.gameObject.AddComponent<PostFx>();

            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.06f, 0.11f, 0.14f);
            RenderSettings.fog = false;
            RenderSettings.skybox = null;
            return (key, rim);
        }

        static Camera BuildCamera(Vector3 position)
        {
            var camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            var cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = DCAtmosphere.DefaultFogColor.gamma;
            cam.fieldOfView = 30f;
            cam.nearClipPlane = 0.5f;
            cam.farClipPlane = 140f;
            cam.allowMSAA = false;
            cam.transform.position = position;
            var data = camGo.AddComponent<UniversalAdditionalCameraData>();
            data.renderPostProcessing = true;
            data.antialiasing = AntialiasingMode.None;
            data.renderShadows = true;
            var snap = camGo.AddComponent<PixelPerfectCamera>();
            snap.gameplayPlaneZ = 0f;
            return cam;
        }

        static (DCAtmosphere atmosphere, AmbientParticles ambient) BuildAtmosphere(Camera cam)
        {
            var atmosphere = new GameObject("Atmosphere").AddComponent<DCAtmosphere>();
            var ambient = new GameObject("AmbientParticles").AddComponent<AmbientParticles>();
            ambient.motesMaterial = DCContentBuilder.LoadMat("M_FX_Flash");
            ambient.embersMaterial = DCContentBuilder.LoadMat("M_FX_Additive");
            ambient.follow = cam.transform;
            ambient.gameObject.layer = DCLayers.Fx;
            return (atmosphere, ambient);
        }

        static GameManager BuildGameManager(PlayerController player, GameObject flameLightOwner)
        {
            var gmGo = new GameObject("GameManager");
            var gm = gmGo.AddComponent<GameManager>();
            gm.player = player;
            gm.flameMaterial = DCContentBuilder.LoadMat("M_BeheadedFlame");
            gm.bodyMaterial = DCContentBuilder.LoadMat("M_Beheaded");
            gm.smokeMaterial = DCContentBuilder.LoadMat("M_BeheadedSmoke");
            gm.flameLight = flameLightOwner != null ? flameLightOwner.GetComponentsInChildren<Light>(true).FirstOrDefault(l => l.name == "FlameLight") : null;
            return gm;
        }

        // ---------------------------------------------------------------- menu

        static void BuildMenu()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var (key, rim) = BuildLights();
            var cam = BuildCamera(new Vector3(20f, 5f, -15f));
            var (atmosphere, ambient) = BuildAtmosphere(cam);

            var heroPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(DCContentBuilder.PrefabDir + "/MenuHero.prefab");
            var hero = (GameObject)PrefabUtility.InstantiatePrefab(heroPrefab);
            BuildGameManager(null, hero);

            var diorama = new GameObject("Diorama").AddComponent<MainMenuDiorama>();
            diorama.biome = Biome("Oubliette");
            diorama.atmosphere = atmosphere;
            diorama.cam = cam;
            diorama.keyLight = key;
            diorama.rimLight = rim;
            diorama.ambient = ambient;
            diorama.hero = hero.transform;

            var menu = new GameObject("MainMenu").AddComponent<MainMenu>();
            menu.hero = hero.GetComponent<CharacterAnimator>();

            EditorSceneManager.SaveScene(scene, MenuScenePath);
        }

        // ---------------------------------------------------------------- game

        static void BuildGame()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var (key, rim) = BuildLights();

            var playerPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(DCContentBuilder.PrefabDir + "/Player.prefab");
            var playerGo = (GameObject)PrefabUtility.InstantiatePrefab(playerPrefab);
            playerGo.transform.position = new Vector3(10f, 10f, 0f);
            var player = playerGo.GetComponent<PlayerController>();

            var cam = BuildCamera(new Vector3(10f, 12f, -17f));
            cam.gameObject.AddComponent<CinemachineBrain>().IgnoreTimeScale = true;
            var vcamGo = new GameObject("CM_Follow");
            var vcam = vcamGo.AddComponent<CinemachineCamera>();
            vcam.Lens = new LensSettings { FieldOfView = 30f, NearClipPlane = 0.5f, FarClipPlane = 140f, ModeOverride = LensSettings.OverrideModes.Perspective };
            Transform target = playerGo.transform.Find("CameraTarget");
            vcam.Target.TrackingTarget = target != null ? target : playerGo.transform;
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
            bounds.levelBounds = new Rect(0f, 0f, 100f, 40f);
            vcamGo.transform.position = cam.transform.position;

            var juiceGo = new GameObject("JuiceEngine");
            var impulse = juiceGo.AddComponent<CinemachineImpulseSource>();
            impulse.ImpulseDefinition.ImpulseShape = CinemachineImpulseDefinition.ImpulseShapes.Bump;
            impulse.ImpulseDefinition.ImpulseType = CinemachineImpulseDefinition.ImpulseTypes.Uniform;
            impulse.ImpulseDefinition.ImpulseDuration = 0.16f;
            impulse.DefaultVelocity = Vector3.down;
            var juice = juiceGo.AddComponent<JuiceEngine>();
            juice.kickSource = impulse;
            juice.traumaNoise = noise;
            juice.additiveMaterial = DCContentBuilder.LoadMat("M_FX_Additive");
            juice.flashMaterial = DCContentBuilder.LoadMat("M_FX_Flash");
            juice.alphaMaterial = DCContentBuilder.LoadMat("M_FX_Alpha");
            juice.dustMaterial = DCContentBuilder.LoadMat("M_FX_Dust");
            juice.textMaterial = DCContentBuilder.LoadMat("M_PixelText");

            BuildGameManager(player, playerGo);
            var (atmosphere, ambient) = BuildAtmosphere(cam);

            var runGo = new GameObject("Run");
            var map = runGo.AddComponent<MapSystem>();
            var levelRoot = new GameObject("LevelRoot").transform;
            var rm = runGo.AddComponent<RunManager>();
            rm.biomes = new[] { Biome("Oubliette"), Biome("Promenade"), Biome("Ossuary"), Biome("StiltVillage"), Biome("ClockLung") };
            rm.passage = Biome("Passage");
            rm.player = player;
            rm.levelRoot = levelRoot;
            rm.cam = cam;
            rm.vcam = vcam;
            rm.cameraBounds = bounds;
            rm.keyLight = key;
            rm.rimLight = rim;
            rm.atmosphere = atmosphere;
            rm.ambient = ambient;
            rm.map = map;

            var hud = new GameObject("HUD").AddComponent<GameHUD>();
            hud.player = player;
            var ui = new GameObject("GameUI").AddComponent<GameUI>();
            ui.player = player;

            EditorSceneManager.SaveScene(scene, GameScenePath);
        }
    }
}
