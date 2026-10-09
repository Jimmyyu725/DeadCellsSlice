using UnityEngine;
using UnityEngine.Rendering;

namespace DeadCells.Rendering
{
    /// <summary>
    /// Snaps the camera to the low-res pixel grid of the gameplay plane while it
    /// renders (so static pixels never crawl), then hands the remainder to the
    /// upscale pass as a sub-pixel offset so scrolling stays smooth. The camera
    /// transform is restored after rendering, leaving Cinemachine untouched.
    /// </summary>
    [ExecuteAlways]
    [RequireComponent(typeof(Camera))]
    public class PixelPerfectCamera : MonoBehaviour
    {
        [Tooltip("World Z of the gameplay plane the pixel grid is locked to.")]
        public float gameplayPlaneZ;

        [Tooltip("Shift the upscaled image by the sub-pixel remainder (smooth scrolling).")]
        public bool subPixelSmoothing = true;

        Camera cam;
        Vector3 savedPosition;
        bool snapped;

        public float WorldUnitsPerPixel { get; private set; }

        void OnEnable()
        {
            cam = GetComponent<Camera>();
            RenderPipelineManager.beginCameraRendering += OnBeginCamera;
            RenderPipelineManager.endCameraRendering += OnEndCamera;
        }

        void OnDisable()
        {
            RenderPipelineManager.beginCameraRendering -= OnBeginCamera;
            RenderPipelineManager.endCameraRendering -= OnEndCamera;
            Shader.SetGlobalVector(PixelGrid.OffsetId, Vector4.zero);
        }

        void OnBeginCamera(ScriptableRenderContext context, Camera c)
        {
            if (c != cam)
                return;
            PixelGrid.Compute(c.pixelWidth, c.pixelHeight, PixelGrid.TargetHeight, out _, out int lowH, out _);
            float dist = Mathf.Max(0.01f, Mathf.Abs(gameplayPlaneZ - transform.position.z));
            WorldUnitsPerPixel = c.orthographic
                ? 2f * c.orthographicSize / lowH
                : 2f * dist * Mathf.Tan(c.fieldOfView * 0.5f * Mathf.Deg2Rad) / lowH;

            savedPosition = transform.position;
            Vector3 right = transform.right;
            Vector3 up = transform.up;
            float rx = Vector3.Dot(savedPosition, right) / WorldUnitsPerPixel;
            float uy = Vector3.Dot(savedPosition, up) / WorldUnitsPerPixel;
            float sx = Mathf.Round(rx);
            float sy = Mathf.Round(uy);
            transform.position = savedPosition + (right * (sx - rx) + up * (sy - uy)) * WorldUnitsPerPixel;
            snapped = true;

            Vector4 offset = subPixelSmoothing ? new Vector4(rx - sx, uy - sy, 0f, 0f) : Vector4.zero;
            Shader.SetGlobalVector(PixelGrid.OffsetId, offset);
        }

        void OnEndCamera(ScriptableRenderContext context, Camera c)
        {
            if (c != cam || !snapped)
                return;
            transform.position = savedPosition;
            snapped = false;
        }
    }
}
