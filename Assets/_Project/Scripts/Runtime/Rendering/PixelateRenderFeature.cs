using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.RenderGraphModule;
using UnityEngine.Rendering.RenderGraphModule.Util;
using UnityEngine.Rendering.Universal;

namespace DeadCells.Rendering
{
    /// <summary>
    /// Integer-scaled pixel quantisation of the opaque scene.
    /// Runs before transparents, so particles, slash arcs, smoke and the bloom
    /// in post-processing stay at full resolution on top of crisp pixel art.
    /// </summary>
    public class PixelateRenderFeature : ScriptableRendererFeature
    {
        [System.Serializable]
        public class Settings
        {
            [Tooltip("Vertical resolution of the pixel-art buffer; the integer scale is derived from the screen height.")]
            public int targetHeight = PixelGrid.DefaultTargetHeight;

            [Tooltip("Per-channel colour levels (0 = off).")]
            [Range(0, 64)] public int colorSteps = 0;

            public RenderPassEvent passEvent = RenderPassEvent.BeforeRenderingTransparents;
            public bool applyInSceneView;
        }

        public Settings settings = new Settings();

        [SerializeField] Shader shader;

        Material material;
        PixelatePass pass;

        public override void Create()
        {
            if (shader == null)
                shader = Shader.Find("Hidden/DeadCells/Pixelate");
            if (shader != null && material == null)
                material = CoreUtils.CreateEngineMaterial(shader);
            pass = new PixelatePass(settings) { renderPassEvent = settings.passEvent };
            PixelGrid.TargetHeight = settings.targetHeight;
        }

        public override void AddRenderPasses(ScriptableRenderer renderer, ref RenderingData renderingData)
        {
            var cameraType = renderingData.cameraData.cameraType;
            if (material == null || cameraType == CameraType.Preview || cameraType == CameraType.Reflection)
                return;
            if (cameraType == CameraType.SceneView && !settings.applyInSceneView)
                return;
            PixelGrid.TargetHeight = settings.targetHeight;
            pass.material = material;
            renderer.EnqueuePass(pass);
        }

        protected override void Dispose(bool disposing)
        {
            CoreUtils.Destroy(material);
            material = null;
            Shader.SetGlobalVector(PixelGrid.ParamsId, Vector4.zero);
        }

        class PixelatePass : ScriptableRenderPass
        {
            static readonly int LowResTexelId = Shader.PropertyToID("_DC_LowResTexel");
            static readonly int ScreenSizeId = Shader.PropertyToID("_DC_ScreenSize");
            static readonly int ColorStepsId = Shader.PropertyToID("_DC_ColorSteps");

            readonly Settings settings;
            public Material material;

            public PixelatePass(Settings settings)
            {
                this.settings = settings;
                profilingSampler = new ProfilingSampler("DeadCells Pixelate");
                requiresIntermediateTexture = true;
            }

            public override void RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData)
            {
                var resources = frameData.Get<UniversalResourceData>();
                if (resources.isActiveTargetBackBuffer)
                    return;

                TextureHandle source = resources.activeColorTexture;
                TextureDesc desc = renderGraph.GetTextureDesc(source);
                int screenW = desc.width;
                int screenH = desc.height;
                PixelGrid.Compute(screenW, screenH, settings.targetHeight, out int lowW, out int lowH, out int scale);

                desc.name = "_DC_PixelArtTarget";
                desc.width = lowW;
                desc.height = lowH;
                desc.filterMode = FilterMode.Point;
                desc.wrapMode = TextureWrapMode.Clamp;
                desc.msaaSamples = MSAASamples.None;
                desc.clearBuffer = false;
                TextureHandle lowRes = renderGraph.CreateTexture(desc);

                Shader.SetGlobalVector(LowResTexelId, new Vector4(1f / lowW, 1f / lowH, lowW, lowH));
                Shader.SetGlobalVector(ScreenSizeId, new Vector4(screenW, screenH, scale, 0f));
                Shader.SetGlobalFloat(ColorStepsId, settings.colorSteps);
                Shader.SetGlobalVector(PixelGrid.ParamsId, new Vector4(lowW, lowH, scale, 1f));

                renderGraph.AddBlitPass(new RenderGraphUtils.BlitMaterialParameters(source, lowRes, material, 0), "DC Pixelate Down");
                renderGraph.AddBlitPass(new RenderGraphUtils.BlitMaterialParameters(lowRes, source, material, 1), "DC Pixelate Up");
            }
        }
    }

    /// <summary>Shared integer pixel-grid maths for the render feature and the camera snapper.</summary>
    public static class PixelGrid
    {
        public const int DefaultTargetHeight = 360;
        public static readonly int ParamsId = Shader.PropertyToID("_DC_PixelParams");
        public static readonly int OffsetId = Shader.PropertyToID("_DC_PixelOffset");
        public static int TargetHeight = DefaultTargetHeight;

        public static void Compute(int screenW, int screenH, int targetHeight, out int lowW, out int lowH, out int scale)
        {
            scale = Mathf.Max(1, Mathf.RoundToInt(screenH / (float)Mathf.Max(1, targetHeight)));
            lowW = Mathf.Max(1, Mathf.CeilToInt(screenW / (float)scale));
            lowH = Mathf.Max(1, Mathf.CeilToInt(screenH / (float)scale));
        }
    }
}
