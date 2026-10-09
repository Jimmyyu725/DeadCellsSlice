using System.Collections.Generic;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.FX
{
    /// <summary>
    /// Pixel-font damage popup: pops up with an arc, holds, then fades. Built as
    /// a world-space mesh facing the camera; drawn on top with the PixelSprite
    /// shader at a size that matches the low-res pixel grid.
    /// </summary>
    [RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
    public class DamageNumber : MonoBehaviour
    {
        public float lifetime = 0.75f;
        public float worldPixel = 0.032f;

        Mesh mesh;
        Vector3 velocity;
        float age;
        float scale;
        Color32 color;
        string text;
        readonly List<Vector3> verts = new List<Vector3>();
        readonly List<Vector2> uvs = new List<Vector2>();
        readonly List<Color32> colors = new List<Color32>();
        readonly List<int> tris = new List<int>();

        public bool Alive => gameObject.activeSelf;

        void Awake()
        {
            mesh = new Mesh { name = "DamageNumber" };
            mesh.MarkDynamic();
            GetComponent<MeshFilter>().sharedMesh = mesh;
            var r = GetComponent<MeshRenderer>();
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
        }

        public void Show(Vector3 position, string label, Color32 tint, bool big)
        {
            gameObject.SetActive(true);
            transform.position = position;
            velocity = new Vector3(Random.Range(-1.2f, 1.2f), big ? 6.5f : 5f, 0f);
            age = 0f;
            scale = big ? 2f : 1.4f;
            color = tint;
            text = label;
            Build(1f);
        }

        void Build(float alpha)
        {
            verts.Clear();
            uvs.Clear();
            colors.Clear();
            tris.Clear();
            var c = color;
            c.a = (byte)(alpha * 255f);
            float px = worldPixel * scale;
            float w = PixelFont.Width(text, 1f) * px;
            PixelFont.AppendQuads(text, new Vector2(-w * 0.5f, 0f), px, c, verts, uvs, colors, tris);
            mesh.Clear();
            mesh.SetVertices(verts);
            mesh.SetUVs(0, uvs);
            mesh.SetColors(colors);
            mesh.SetTriangles(tris, 0);
            mesh.RecalculateBounds();
        }

        void LateUpdate()
        {
            float dt = Time.unscaledDeltaTime;
            age += dt;
            velocity.y -= 18f * dt;
            transform.position += velocity * dt;
            velocity.x *= 1f - 4f * dt;
            var cam = Camera.main;
            if (cam != null)
                transform.rotation = cam.transform.rotation;
            // Pop: overshoot then settle.
            float pop = age < 0.08f ? Mathf.Lerp(0.4f, 1.35f, age / 0.08f) : Mathf.Lerp(1.35f, 1f, Mathf.Clamp01((age - 0.08f) / 0.1f));
            transform.localScale = Vector3.one * pop;
            float fade = Mathf.Clamp01((lifetime - age) / 0.25f);
            Build(fade);
            if (age >= lifetime)
                gameObject.SetActive(false);
        }
    }
}
