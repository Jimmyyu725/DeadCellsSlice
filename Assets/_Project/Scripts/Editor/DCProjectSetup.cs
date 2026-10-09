using System.Linq;
using DeadCells.Core;
using DeadCells.Rendering;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace DeadCells.EditorTools
{
    /// <summary>
    /// Project-level configuration: layers and 2D collision matrix, player
    /// settings, URP asset (HDR, Forward+, shadows), renderer (pixelate
    /// feature, no depth priming) and the post-processing profile
    /// (ACES, graded colour, bloom 0.9 / scatter 0.7, warm highlights).
    /// </summary>
    public static class DCProjectSetup
    {
        public const string RenderingDir = "Assets/_Project/Rendering";
        public const string PostProfilePath = RenderingDir + "/DC_PostProfile.asset";
        const string PipelineAssetPath = "Assets/Settings/PC_RPAsset.asset";
        const string RendererPath = "Assets/Settings/PC_Renderer.asset";

        [MenuItem("Dead Cells/Setup/1 Configure Project")]
        public static void ConfigureAll()
        {
            ConfigureLayers();
            ConfigurePhysics();
            ConfigurePlayer();
            ConfigurePipeline();
            CreatePostProfile();
            AssetDatabase.SaveAssets();
            Debug.Log("[DC] project configured");
        }

        public static void ConfigureLayers()
        {
            var tagManager = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
            var layers = tagManager.FindProperty("layers");
            for (int i = 8; i < DCLayers.Names.Length; i++)
                layers.GetArrayElementAtIndex(i).stringValue = DCLayers.Names[i];
            tagManager.ApplyModifiedPropertiesWithoutUndo();
        }

        public static void ConfigurePhysics()
        {
            Physics2D.gravity = new Vector2(0f, -9.81f);
            int[] custom = { DCLayers.Ground, DCLayers.OneWay, DCLayers.Player, DCLayers.Enemy, DCLayers.PlayerDodge, DCLayers.Pickup, DCLayers.Fx };
            // Start from "everything collides", then carve out.
            for (int a = 0; a < 32; a++)
                for (int b = 0; b < 32; b++)
                    Physics2D.IgnoreLayerCollision(a, b, false);
            void Ignore(int a, int b) => Physics2D.IgnoreLayerCollision(a, b, true);
            Ignore(DCLayers.PlayerDodge, DCLayers.Enemy);
            Ignore(DCLayers.Enemy, DCLayers.Enemy);
            foreach (int l in custom)
            {
                if (l != DCLayers.Ground && l != DCLayers.OneWay)
                {
                    Ignore(DCLayers.Fx, l);
                    Ignore(DCLayers.Pickup, l);
                }
            }
            Ignore(DCLayers.Ground, DCLayers.OneWay);
            Ignore(DCLayers.OneWay, DCLayers.OneWay);
            Ignore(DCLayers.Ground, DCLayers.Ground);
            Ignore(DCLayers.Player, DCLayers.PlayerDodge);
            for (int l = 0; l < 8; l++)
            {
                // Builtin layers (Default etc.) never touch gameplay bodies.
                foreach (int c in custom)
                    Ignore(l, c);
            }
            var settings = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/Physics2DSettings.asset").FirstOrDefault();
            if (settings != null)
                EditorUtility.SetDirty(settings);
        }

        public static void ConfigurePlayer()
        {
            PlayerSettings.companyName = "DeadCellsSlice";
            PlayerSettings.productName = "Dead Cells Slice";
            PlayerSettings.colorSpace = ColorSpace.Linear;
            PlayerSettings.defaultScreenWidth = 1920;
            PlayerSettings.defaultScreenHeight = 1080;
            PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
            PlayerSettings.resizableWindow = true;
            PlayerSettings.runInBackground = true;
            PlayerSettings.visibleInBackground = true;
            PlayerSettings.SplashScreen.show = false;
            PlayerSettings.SetApiCompatibilityLevel(UnityEditor.Build.NamedBuildTarget.Standalone, ApiCompatibilityLevel.NET_Standard);
            QualitySettings.SetQualityLevel(1, true);
        }

        public static void ConfigurePipeline()
        {
            var asset = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(PipelineAssetPath);
            var so = new SerializedObject(asset);
            void Set(string name, System.Action<SerializedProperty> apply)
            {
                var p = so.FindProperty(name);
                if (p != null)
                    apply(p);
                else
                    Debug.LogWarning("[DC] URP asset field not found: " + name);
            }
            Set("m_SupportsHDR", p => p.boolValue = true);
            Set("m_MSAA", p => p.intValue = 1);
            Set("m_RenderScale", p => p.floatValue = 1f);
            Set("m_MainLightRenderingMode", p => p.intValue = 1);
            Set("m_MainLightShadowsSupported", p => p.boolValue = true);
            Set("m_MainLightShadowmapResolution", p => p.intValue = 2048);
            Set("m_AdditionalLightsRenderingMode", p => p.intValue = 1);
            Set("m_AdditionalLightsPerObjectLimit", p => p.intValue = 8);
            Set("m_AdditionalLightShadowsSupported", p => p.boolValue = false);
            Set("m_ShadowDistance", p => p.floatValue = 45f);
            Set("m_ShadowCascadeCount", p => p.intValue = 2);
            Set("m_SoftShadowsSupported", p => p.boolValue = true);
            Set("m_ColorGradingMode", p => p.intValue = 1); // HDR grading
            Set("m_ColorGradingLutSize", p => p.intValue = 32);
            Set("m_UseSRPBatcher", p => p.boolValue = true);
            so.ApplyModifiedPropertiesWithoutUndo();
            GraphicsSettings.defaultRenderPipeline = asset;
            QualitySettings.renderPipeline = asset;
            EditorUtility.SetDirty(asset);

            var data = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(RendererPath);
            data.renderingMode = RenderingMode.ForwardPlus;
            data.depthPrimingMode = DepthPrimingMode.Disabled;
            // Replace features with our pixelate pass.
            foreach (var f in data.rendererFeatures.ToArray())
            {
                if (f != null && !(f is PixelateRenderFeature))
                {
                    data.rendererFeatures.Remove(f);
                    Object.DestroyImmediate(f, true);
                }
            }
            var pixelate = data.rendererFeatures.OfType<PixelateRenderFeature>().FirstOrDefault();
            if (pixelate == null)
            {
                pixelate = ScriptableObject.CreateInstance<PixelateRenderFeature>();
                pixelate.name = "DeadCells Pixelate";
                AssetDatabase.AddObjectToAsset(pixelate, data);
                data.rendererFeatures.Add(pixelate);
            }
            var fso = new SerializedObject(pixelate);
            fso.FindProperty("shader").objectReferenceValue = Shader.Find("Hidden/DeadCells/Pixelate");
            fso.ApplyModifiedPropertiesWithoutUndo();
            pixelate.settings.targetHeight = PixelGrid.DefaultTargetHeight;
            pixelate.settings.passEvent = RenderPassEvent.BeforeRenderingTransparents;
            pixelate.SetActive(true);
            SyncFeatureMap(data);
            EditorUtility.SetDirty(pixelate);
            EditorUtility.SetDirty(data);
        }

        static void SyncFeatureMap(ScriptableRendererData data)
        {
            var so = new SerializedObject(data);
            var features = so.FindProperty("m_RendererFeatures");
            var map = so.FindProperty("m_RendererFeatureMap");
            map.arraySize = features.arraySize;
            for (int i = 0; i < features.arraySize; i++)
            {
                var obj = features.GetArrayElementAtIndex(i).objectReferenceValue;
                if (obj != null && AssetDatabase.TryGetGUIDAndLocalFileIdentifier(obj, out _, out long localId))
                    map.GetArrayElementAtIndex(i).longValue = localId;
            }
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        public static VolumeProfile CreatePostProfile()
        {
            System.IO.Directory.CreateDirectory(RenderingDir);
            var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(PostProfilePath);
            if (profile == null)
            {
                profile = ScriptableObject.CreateInstance<VolumeProfile>();
                AssetDatabase.CreateAsset(profile, PostProfilePath);
            }
            foreach (var c in profile.components.ToArray())
            {
                profile.components.Remove(c);
                Object.DestroyImmediate(c, true);
            }

            var tone = profile.Add<Tonemapping>(true);
            tone.mode.Override(TonemappingMode.ACES);

            var bloom = profile.Add<Bloom>(true);
            bloom.threshold.Override(0.9f);
            bloom.intensity.Override(1.15f);
            bloom.scatter.Override(0.7f);
            bloom.highQualityFiltering.Override(true);
            bloom.tint.Override(new Color(1f, 0.93f, 0.98f));

            var color = profile.Add<ColorAdjustments>(true);
            color.postExposure.Override(0.35f);
            color.contrast.Override(24f);
            color.saturation.Override(26f);
            color.colorFilter.Override(new Color(1f, 0.98f, 0.96f));

            var smh = profile.Add<ShadowsMidtonesHighlights>(true);
            smh.shadows.Override(new Vector4(0.92f, 0.98f, 1.12f, -0.02f));
            smh.midtones.Override(new Vector4(1f, 1f, 1f, 0f));
            smh.highlights.Override(new Vector4(1.12f, 1.02f, 0.9f, 0.03f));

            var split = profile.Add<SplitToning>(true);
            split.shadows.Override(new Color(0.24f, 0.38f, 0.55f));
            split.highlights.Override(new Color(1f, 0.72f, 0.45f));
            split.balance.Override(-15f);

            var vignette = profile.Add<Vignette>(true);
            vignette.intensity.Override(0.3f);
            vignette.smoothness.Override(0.45f);
            vignette.color.Override(new Color(0.02f, 0.03f, 0.06f));

            foreach (var c in profile.components)
            {
                c.name = c.GetType().Name;
                if (!AssetDatabase.Contains(c))
                    AssetDatabase.AddObjectToAsset(c, profile);
            }
            EditorUtility.SetDirty(profile);
            return profile;
        }
    }
}
