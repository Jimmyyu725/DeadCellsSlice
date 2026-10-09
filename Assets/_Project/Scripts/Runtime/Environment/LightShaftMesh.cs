using UnityEngine;

namespace DeadCells.Environment
{
    /// <summary>Builds the trapezoid card for a fake volumetric light shaft (top at the origin).</summary>
    [ExecuteAlways]
    [RequireComponent(typeof(MeshFilter))]
    public class LightShaftMesh : MonoBehaviour
    {
        public float length = 7f;
        public float bottomWidth = 2f;
        [Range(0.1f, 1f)] public float topWidthRatio = 0.7f;

        Mesh mesh;

        void OnEnable() => Build();
        void OnValidate() => Build();

        void OnDisable()
        {
            if (mesh != null)
            {
                if (Application.isPlaying)
                    Destroy(mesh);
                else
                    DestroyImmediate(mesh);
            }
        }

        void Build()
        {
            if (mesh == null)
                mesh = new Mesh { name = "LightShaft", hideFlags = HideFlags.DontSave };
            float b = bottomWidth * 0.5f;
            float t = b * topWidthRatio;
            mesh.Clear();
            mesh.vertices = new[] { new Vector3(-b, -length, 0f), new Vector3(-t, 0f, 0f), new Vector3(t, 0f, 0f), new Vector3(b, -length, 0f) };
            mesh.uv = new[] { new Vector2(0f, 0f), new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(1f, 0f) };
            mesh.triangles = new[] { 0, 1, 2, 0, 2, 3 };
            mesh.RecalculateBounds();
            GetComponent<MeshFilter>().sharedMesh = mesh;
        }
    }
}
