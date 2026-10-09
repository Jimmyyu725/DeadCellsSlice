using System.Collections.Generic;
using UnityEngine;

namespace DeadCells.FX
{
    /// <summary>
    /// Emissive ribbon trail following the blade. Samples hilt/tip every frame
    /// after animation and fills the gaps by slerping around the shoulder
    /// pivot, so a strike that jumps 150 degrees in a single animation frame
    /// still sweeps a clean crescent instead of a straight chord.
    /// </summary>
    [RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
    public class SlashArc : MonoBehaviour
    {
        public Transform pivot;
        public Transform bladeBase;
        public Transform bladeTip;
        [Tooltip("Seconds a sample stays visible.")]
        public float lifetime = 0.11f;
        [Tooltip("Max degrees between generated sub-samples.")]
        public float stepDegrees = 6f;
        [Tooltip("Blade portion covered by the ribbon (0 = hilt, 1 = tip; >1 overshoots).")]
        public Vector2 bladeSpan = new Vector2(0.05f, 1.18f);

        struct Sample
        {
            public Vector3 pivot, hilt, tip;
            public float time;
        }

        readonly List<Sample> samples = new List<Sample>();
        readonly List<Vector3> verts = new List<Vector3>();
        readonly List<Vector2> uvs = new List<Vector2>();
        readonly List<Color> colors = new List<Color>();
        readonly List<int> tris = new List<int>();
        Mesh mesh;
        MeshRenderer meshRenderer;
        MaterialPropertyBlock block;
        bool emitting;
        float clock;

        static readonly int ArcColorId = Shader.PropertyToID("_ArcColor");
        static readonly int CoreColorId = Shader.PropertyToID("_CoreColor");

        void Awake()
        {
            mesh = new Mesh { name = "SlashArc" };
            mesh.MarkDynamic();
            GetComponent<MeshFilter>().sharedMesh = mesh;
            meshRenderer = GetComponent<MeshRenderer>();
            meshRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            meshRenderer.receiveShadows = false;
            block = new MaterialPropertyBlock();
        }

        public void Begin(Color arcColor, Color coreColor)
        {
            emitting = true;
            block.SetColor(ArcColorId, arcColor);
            block.SetColor(CoreColorId, coreColor);
            meshRenderer.SetPropertyBlock(block);
            samples.Clear();
            Record();
        }

        public void End()
        {
            emitting = false;
        }

        void LateUpdate()
        {
            // World-space mesh: keep this object at the origin.
            transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            transform.localScale = Vector3.one;
            clock += Time.deltaTime;
            if (emitting)
                Record();
            while (samples.Count > 0 && clock - samples[0].time > lifetime)
                samples.RemoveAt(0);
            Rebuild();
        }

        void Record()
        {
            if (pivot == null || bladeBase == null || bladeTip == null)
                return;
            Vector3 hilt = bladeBase.position;
            Vector3 tip = bladeTip.position;
            Vector3 axis = tip - hilt;
            samples.Add(new Sample
            {
                pivot = pivot.position,
                hilt = hilt + axis * bladeSpan.x,
                tip = hilt + axis * bladeSpan.y,
                time = clock,
            });
        }

        void Rebuild()
        {
            mesh.Clear();
            if (samples.Count < 2)
                return;
            verts.Clear();
            uvs.Clear();
            colors.Clear();
            tris.Clear();

            // Expand samples with pivot-relative slerps.
            var dense = new List<Sample>(samples.Count * 4) { samples[0] };
            for (int i = 1; i < samples.Count; i++)
            {
                Sample a = samples[i - 1], b = samples[i];
                Vector3 ta = a.tip - a.pivot, tb = b.tip - b.pivot;
                float angle = Vector3.Angle(ta, tb);
                int steps = Mathf.Clamp(Mathf.CeilToInt(angle / stepDegrees), 1, 40);
                Vector3 ha = a.hilt - a.pivot, hb = b.hilt - b.pivot;
                for (int k = 1; k <= steps; k++)
                {
                    float t = k / (float)steps;
                    Vector3 p = Vector3.Lerp(a.pivot, b.pivot, t);
                    dense.Add(new Sample
                    {
                        pivot = p,
                        tip = p + Vector3.Slerp(ta, tb, t),
                        hilt = p + Vector3.Slerp(ha, hb, t),
                        time = Mathf.Lerp(a.time, b.time, t),
                    });
                }
            }

            float newest = dense[dense.Count - 1].time;
            for (int i = 0; i < dense.Count; i++)
            {
                Sample s = dense[i];
                float age = Mathf.Clamp01((clock - s.time) / lifetime);
                // Older sub-samples within the same frame read as further along the sweep.
                float along = dense.Count > 1 ? 1f - i / (float)(dense.Count - 1) : 0f;
                float u = Mathf.Clamp01(Mathf.Max(age, along * 0.85f));
                float fade = emitting ? 1f : Mathf.Clamp01(1f - (clock - newest) / lifetime);
                verts.Add(s.hilt);
                verts.Add(s.tip);
                uvs.Add(new Vector2(u, 0f));
                uvs.Add(new Vector2(u, 1f));
                colors.Add(new Color(1f, 1f, 1f, fade));
                colors.Add(new Color(1f, 1f, 1f, fade));
                if (i > 0)
                {
                    int b = i * 2;
                    tris.Add(b - 2); tris.Add(b - 1); tris.Add(b + 1);
                    tris.Add(b - 2); tris.Add(b + 1); tris.Add(b);
                }
            }
            mesh.SetVertices(verts);
            mesh.SetUVs(0, uvs);
            mesh.SetColors(colors);
            mesh.SetTriangles(tris, 0);
            mesh.RecalculateBounds();
        }
    }
}
