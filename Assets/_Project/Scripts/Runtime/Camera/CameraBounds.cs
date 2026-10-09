using Unity.Cinemachine;
using UnityEngine;

namespace DeadCells.CameraRig
{
    /// <summary>
    /// Keeps the perspective camera's view of the gameplay plane inside the
    /// level rectangle (Cinemachine's 2D confiner assumes orthographic).
    /// </summary>
    [ExecuteAlways]
    [AddComponentMenu("Cinemachine/Dead Cells Camera Bounds")]
    public class CameraBounds : CinemachineExtension
    {
        public Rect levelBounds = new Rect(-10f, -6f, 80f, 26f);
        public float gameplayPlaneZ;

        protected override void PostPipelineStageCallback(CinemachineVirtualCameraBase vcam,
            CinemachineCore.Stage stage, ref CameraState state, float deltaTime)
        {
            if (stage != CinemachineCore.Stage.Body)
                return;
            Vector3 pos = state.GetCorrectedPosition();
            float dist = Mathf.Abs(gameplayPlaneZ - pos.z);
            float halfH = dist * Mathf.Tan(state.Lens.FieldOfView * 0.5f * Mathf.Deg2Rad);
            float halfW = halfH * state.Lens.Aspect;
            float minX = levelBounds.xMin + halfW, maxX = levelBounds.xMax - halfW;
            float minY = levelBounds.yMin + halfH, maxY = levelBounds.yMax - halfH;
            float x = minX > maxX ? levelBounds.center.x : Mathf.Clamp(pos.x, minX, maxX);
            float y = minY > maxY ? levelBounds.center.y : Mathf.Clamp(pos.y, minY, maxY);
            state.PositionCorrection += new Vector3(x - pos.x, y - pos.y, 0f);
        }

        void OnDrawGizmosSelected()
        {
            Gizmos.color = Color.cyan;
            Gizmos.DrawWireCube(new Vector3(levelBounds.center.x, levelBounds.center.y, gameplayPlaneZ),
                new Vector3(levelBounds.width, levelBounds.height, 0.1f));
        }
    }
}
