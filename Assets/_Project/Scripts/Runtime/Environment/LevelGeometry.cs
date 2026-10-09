using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace DeadCells.Environment
{
    /// <summary>
    /// Level geometry stored as placements of the environment kit modules and
    /// merged into chunk meshes when the scene loads (play mode and edit mode).
    /// Keeps the scene file small: the combined meshes never hit disk.
    /// </summary>
    [ExecuteAlways]
    public class LevelGeometry : MonoBehaviour
    {
        [System.Serializable]
        public struct Placement
        {
            public int module;
            public Vector3 position;
            public Vector3 scale;
        }

        [System.Serializable]
        public class Batch
        {
            public string name;
            public Material material;
            public bool castShadows = true;
            public List<Placement> placements = new List<Placement>();
        }

        [Tooltip("Kit meshes referenced by Placement.module (import with Read/Write enabled).")]
        public Mesh[] modules = new Mesh[0];
        [Tooltip("Per-module transform of the mesh inside its FBX (identity when axis conversion is baked).")]
        public Matrix4x4[] moduleMatrices = new Matrix4x4[0];
        public List<Batch> batches = new List<Batch>();

        readonly List<GameObject> built = new List<GameObject>();

        public int PlacementCount
        {
            get
            {
                int n = 0;
                foreach (var b in batches)
                    n += b.placements.Count;
                return n;
            }
        }

        void OnEnable() => Build();
        void OnDisable() => Clear();

        public void Rebuild()
        {
            Clear();
            Build();
        }

        void Build()
        {
            if (built.Count > 0)
                return;
            var combine = new List<CombineInstance>();
            foreach (var batch in batches)
            {
                combine.Clear();
                foreach (var p in batch.placements)
                {
                    if (p.module < 0 || p.module >= modules.Length || modules[p.module] == null)
                        continue;
                    Matrix4x4 local = p.module < moduleMatrices.Length ? moduleMatrices[p.module] : Matrix4x4.identity;
                    Vector3 s = p.scale == Vector3.zero ? Vector3.one : p.scale;
                    combine.Add(new CombineInstance
                    {
                        mesh = modules[p.module],
                        transform = Matrix4x4.TRS(p.position, Quaternion.identity, s) * local,
                    });
                }
                if (combine.Count == 0)
                    continue;
                var mesh = new Mesh { name = batch.name, indexFormat = IndexFormat.UInt32, hideFlags = HideFlags.DontSave };
                mesh.CombineMeshes(combine.ToArray(), true, true);
                mesh.RecalculateBounds();
                mesh.UploadMeshData(true);
                var go = new GameObject(batch.name, typeof(MeshFilter), typeof(MeshRenderer))
                {
                    hideFlags = HideFlags.DontSave | HideFlags.NotEditable,
                };
                go.layer = gameObject.layer;
                go.transform.SetParent(transform, false);
                go.GetComponent<MeshFilter>().sharedMesh = mesh;
                var r = go.GetComponent<MeshRenderer>();
                r.sharedMaterial = batch.material;
                r.shadowCastingMode = batch.castShadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
                built.Add(go);
            }
        }

        void Clear()
        {
            foreach (var go in built)
            {
                if (go == null)
                    continue;
                var mesh = go.GetComponent<MeshFilter>().sharedMesh;
                if (Application.isPlaying)
                {
                    Destroy(mesh);
                    Destroy(go);
                }
                else
                {
                    DestroyImmediate(mesh);
                    DestroyImmediate(go);
                }
            }
            built.Clear();
        }
    }
}
