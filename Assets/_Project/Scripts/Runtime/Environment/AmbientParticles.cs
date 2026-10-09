using DeadCells.FX;
using UnityEngine;

namespace DeadCells.Environment
{
    /// <summary>
    /// Camera-following volume of floating dust motes and drifting dungeon
    /// embers spread across the gameplay and background depths.
    /// </summary>
    public class AmbientParticles : MonoBehaviour
    {
        public Material motesMaterial;   // additive soft disc
        public Material embersMaterial;  // additive square
        public Transform follow;
        public Vector3 volume = new Vector3(30f, 16f, 10f);
        public float motesPerSecond = 26f;
        public float embersPerSecond = 7f;

        ParticleSystem motes, embers;

        void Start()
        {
            motes = FxLibrary.Create("AmbientMotes", transform, motesMaterial, ps =>
            {
                var main = ps.main;
                main.loop = true;
                main.startLifetime = new ParticleSystem.MinMaxCurve(5f, 9f);
                main.startSpeed = new ParticleSystem.MinMaxCurve(0.05f, 0.25f);
                main.startSize = new ParticleSystem.MinMaxCurve(0.025f, 0.07f);
                main.startColor = new ParticleSystem.MinMaxGradient(new Color(0.55f, 0.95f, 1.1f, 0.5f), new Color(0.9f, 1.1f, 1.2f, 0.9f));
                main.maxParticles = 600;
                var emission = ps.emission;
                emission.rateOverTime = motesPerSecond;
                var shape = ps.shape;
                shape.shapeType = ParticleSystemShapeType.Box;
                shape.scale = volume;
                var noise = ps.noise;
                noise.enabled = true;
                noise.strength = 0.25f;
                noise.frequency = 0.3f;
                var col = ps.colorOverLifetime;
                col.enabled = true;
                var g = new Gradient();
                g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                    new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.2f), new GradientAlphaKey(1f, 0.8f), new GradientAlphaKey(0f, 1f) });
                col.color = g;
            });
            embers = FxLibrary.Create("AmbientEmbers", transform, embersMaterial, ps =>
            {
                var main = ps.main;
                main.loop = true;
                main.startLifetime = new ParticleSystem.MinMaxCurve(3f, 6f);
                main.startSpeed = new ParticleSystem.MinMaxCurve(0.2f, 0.8f);
                main.startSize = new ParticleSystem.MinMaxCurve(0.03f, 0.06f);
                main.startColor = new ParticleSystem.MinMaxGradient(new Color(3f, 1.1f, 0.3f, 1f), new Color(3.5f, 1.8f, 0.5f, 1f));
                main.gravityModifier = -0.04f;
                main.maxParticles = 200;
                var emission = ps.emission;
                emission.rateOverTime = embersPerSecond;
                var shape = ps.shape;
                shape.shapeType = ParticleSystemShapeType.Box;
                shape.scale = new Vector3(volume.x, 2f, volume.z * 0.6f);
                shape.position = new Vector3(0f, -volume.y * 0.4f, 0f);
                var noise = ps.noise;
                noise.enabled = true;
                noise.strength = 0.8f;
                noise.frequency = 0.6f;
                var col = ps.colorOverLifetime;
                col.enabled = true;
                var g = new Gradient();
                g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(new Color(1f, 0.4f, 0.2f), 1f) },
                    new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.1f), new GradientAlphaKey(0.8f, 0.7f), new GradientAlphaKey(0f, 1f) });
                col.color = g;
            });
            var r = embers.GetComponent<ParticleSystemRenderer>();
            r.renderMode = ParticleSystemRenderMode.Stretch;
            r.velocityScale = 0.12f;
            r.lengthScale = 1.5f;
            motes.Play();
            embers.Play();
        }

        void LateUpdate()
        {
            if (follow != null)
            {
                Vector3 p = follow.position;
                transform.position = new Vector3(p.x, p.y, volume.z * 0.5f - 1.5f);
            }
        }
    }
}
