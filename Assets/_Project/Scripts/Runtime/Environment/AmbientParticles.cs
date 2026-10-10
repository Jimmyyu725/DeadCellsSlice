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
                // A thin slab in front of the back wall (the follow point sits deeper).
                shape.scale = new Vector3(volume.x, volume.y, 3f);
                shape.position = new Vector3(0f, 0f, -(volume.z * 0.5f - 1.5f) + 0.3f);
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

        /// <summary>Recolour for a biome; `rainUp` turns the embers into rain falling upwards.</summary>
        public void Apply(Color motesA, Color motesB, Color embersA, Color embersB, bool rainUp)
        {
            if (motes == null || embers == null)
            {
                pending = () => Apply(motesA, motesB, embersA, embersB, rainUp);
                return;
            }
            var mm = motes.main;
            mm.startColor = new ParticleSystem.MinMaxGradient(motesA, motesB);
            var em = embers.main;
            em.startColor = new ParticleSystem.MinMaxGradient(embersA, embersB);
            em.startSpeed = rainUp ? new ParticleSystem.MinMaxCurve(7f, 11f) : new ParticleSystem.MinMaxCurve(0.2f, 0.8f);
            em.startLifetime = rainUp ? new ParticleSystem.MinMaxCurve(1.2f, 2f) : new ParticleSystem.MinMaxCurve(3f, 6f);
            em.startSize = rainUp ? new ParticleSystem.MinMaxCurve(0.015f, 0.03f) : new ParticleSystem.MinMaxCurve(0.03f, 0.06f);
            var emission = embers.emission;
            emission.rateOverTime = rainUp ? 110f : embersPerSecond;
            var shape = embers.shape;
            shape.rotation = rainUp ? new Vector3(-90f, 0f, 0f) : Vector3.zero;
            var noise = embers.noise;
            noise.strength = rainUp ? 0.15f : 0.8f;
            var r = embers.GetComponent<ParticleSystemRenderer>();
            r.velocityScale = rainUp ? 0.05f : 0.12f;
            r.lengthScale = rainUp ? 3f : 1.5f;
        }

        /// <summary>A third, biome-specific layer.</summary>
        public enum Special { None, Fireflies, Spores, Ash, Stars, Drips }

        ParticleSystem special;
        Special currentSpecial = Special.None;

        public void ApplySpecial(Special kind)
        {
            if (kind == currentSpecial && special != null)
                return;
            currentSpecial = kind;
            if (special != null)
                Destroy(special.gameObject);
            special = null;
            if (kind == Special.None || motesMaterial == null)
                return;
            bool square = kind == Special.Ash || kind == Special.Drips;
            special = FxLibrary.Create("Ambient" + kind, transform, square ? embersMaterial : motesMaterial, ps =>
            {
                var main = ps.main;
                main.loop = true;
                main.maxParticles = 300;
                var emission = ps.emission;
                var shape = ps.shape;
                shape.shapeType = ParticleSystemShapeType.Box;
                shape.scale = volume;
                var noise = ps.noise;
                var col = ps.colorOverLifetime;
                col.enabled = true;
                var g = new Gradient();
                switch (kind)
                {
                    case Special.Fireflies:
                        main.startLifetime = new ParticleSystem.MinMaxCurve(4f, 7f);
                        main.startSpeed = new ParticleSystem.MinMaxCurve(0.1f, 0.4f);
                        main.startSize = new ParticleSystem.MinMaxCurve(0.14f, 0.22f);
                        main.startColor = new ParticleSystem.MinMaxGradient(new Color(2.6f, 3.6f, 0.8f, 1f), new Color(3.6f, 3.2f, 1f, 1f));
                        emission.rateOverTime = 14f;
                        noise.enabled = true;
                        noise.strength = 0.9f;
                        noise.frequency = 0.45f;
                        // Blink on and off.
                        g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                            new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.15f), new GradientAlphaKey(0.15f, 0.35f),
                                new GradientAlphaKey(1f, 0.55f), new GradientAlphaKey(0.2f, 0.78f), new GradientAlphaKey(0f, 1f) });
                        break;
                    case Special.Spores:
                        main.startLifetime = new ParticleSystem.MinMaxCurve(5f, 9f);
                        main.startSpeed = new ParticleSystem.MinMaxCurve(0.05f, 0.2f);
                        main.startSize = new ParticleSystem.MinMaxCurve(0.09f, 0.16f);
                        main.startColor = new ParticleSystem.MinMaxGradient(new Color(1.2f, 2.4f, 0.7f, 0.7f), new Color(1.6f, 3f, 1f, 1f));
                        main.gravityModifier = -0.01f;
                        emission.rateOverTime = 30f;
                        noise.enabled = true;
                        noise.strength = 0.35f;
                        noise.frequency = 0.25f;
                        g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                            new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.25f), new GradientAlphaKey(1f, 0.75f), new GradientAlphaKey(0f, 1f) });
                        break;
                    case Special.Ash:
                        main.startLifetime = new ParticleSystem.MinMaxCurve(5f, 8f);
                        main.startSpeed = new ParticleSystem.MinMaxCurve(0.1f, 0.3f);
                        main.startSize = new ParticleSystem.MinMaxCurve(0.07f, 0.12f);
                        main.startRotation = new ParticleSystem.MinMaxCurve(0f, 6.28f);
                        main.startColor = new ParticleSystem.MinMaxGradient(new Color(0.7f, 0.66f, 0.64f, 0.8f), new Color(1.1f, 1.02f, 0.98f, 1f));
                        main.gravityModifier = 0.03f;
                        emission.rateOverTime = 40f;
                        noise.enabled = true;
                        noise.strength = 0.6f;
                        noise.frequency = 0.4f;
                        g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                            new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.1f), new GradientAlphaKey(1f, 0.85f), new GradientAlphaKey(0f, 1f) });
                        break;
                    case Special.Stars:
                        main.startLifetime = new ParticleSystem.MinMaxCurve(2f, 4f);
                        main.startSpeed = new ParticleSystem.MinMaxCurve(0f, 0.05f);
                        main.startSize = new ParticleSystem.MinMaxCurve(0.08f, 0.15f);
                        main.startColor = new ParticleSystem.MinMaxGradient(new Color(2.4f, 3f, 4f, 1f), new Color(3.6f, 3.6f, 4f, 1f));
                        emission.rateOverTime = 30f;
                        g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                            new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.2f), new GradientAlphaKey(0.3f, 0.5f),
                                new GradientAlphaKey(1f, 0.7f), new GradientAlphaKey(0f, 1f) });
                        break;
                    case Special.Drips:
                        main.startLifetime = new ParticleSystem.MinMaxCurve(1.2f, 1.8f);
                        main.startSpeed = new ParticleSystem.MinMaxCurve(0f, 0.2f);
                        main.startSize = new ParticleSystem.MinMaxCurve(0.045f, 0.07f);
                        main.startColor = new ParticleSystem.MinMaxGradient(new Color(0.9f, 1.3f, 1.8f, 0.8f), new Color(1.2f, 1.6f, 2.2f, 1f));
                        main.gravityModifier = 0.9f;
                        emission.rateOverTime = 14f;
                        shape.scale = new Vector3(volume.x, 0.5f, 3f);
                        shape.position = new Vector3(0f, volume.y * 0.5f, -(volume.z * 0.5f - 1.5f) + 0.3f);
                        g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                            new[] { new GradientAlphaKey(1f, 0f), new GradientAlphaKey(1f, 0.9f), new GradientAlphaKey(0f, 1f) });
                        break;
                }
                col.color = g;
            });
            if (kind == Special.Drips)
            {
                var r = special.GetComponent<ParticleSystemRenderer>();
                r.renderMode = ParticleSystemRenderMode.Stretch;
                r.velocityScale = 0.03f;
                r.lengthScale = 2f;
            }
            special.Play();
        }

        System.Action pending;

        void LateUpdate()
        {
            if (pending != null && motes != null)
            {
                var p = pending;
                pending = null;
                p();
            }
            if (follow != null)
            {
                Vector3 p = follow.position;
                transform.position = new Vector3(p.x, p.y, volume.z * 0.5f - 1.5f);
            }
        }
    }
}
