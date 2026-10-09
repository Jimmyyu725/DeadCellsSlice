using UnityEngine;

namespace DeadCells.FX
{
    /// <summary>
    /// Builds the world-space particle systems used for hit sparks, dust, ichor,
    /// slam shockwaves, death bursts and cells. One persistent system per effect:
    /// spawning moves the emitter and calls Emit, so there is nothing to pool.
    /// </summary>
    public static class FxLibrary
    {
        public static ParticleSystem Create(string name, Transform parent, Material material, System.Action<ParticleSystem> configure)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.playOnAwake = false;
            main.loop = false;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.scalingMode = ParticleSystemScalingMode.Hierarchy;
            main.maxParticles = 512;
            var emission = ps.emission;
            emission.rateOverTime = 0f;
            var renderer = go.GetComponent<ParticleSystemRenderer>();
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            configure(ps);
            ps.Play();
            return ps;
        }

        static ParticleSystem.MinMaxCurve Range(float a, float b) => new ParticleSystem.MinMaxCurve(a, b);

        static AnimationCurve Fall(float start = 1f) => new AnimationCurve(new Keyframe(0f, start), new Keyframe(1f, 0f));

        /// <summary>Pixel sparks streaking away from the impact.</summary>
        public static void Sparks(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.10f, 0.26f);
            main.startSpeed = Range(7f, 17f);
            main.startSize = Range(0.05f, 0.11f);
            main.gravityModifier = 1.6f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Cone;
            shape.angle = 38f;
            shape.radius = 0.04f;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, Fall());
            var r = ps.GetComponent<ParticleSystemRenderer>();
            r.renderMode = ParticleSystemRenderMode.Stretch;
            r.velocityScale = 0.035f;
            r.lengthScale = 1.2f;
        }

        /// <summary>Single bright disc at the point of impact.</summary>
        public static void Flash(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = 0.07f;
            main.startSpeed = 0f;
            main.startSize = Range(0.9f, 1.3f);
            var shape = ps.shape;
            shape.enabled = false;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 0.6f), new Keyframe(0.3f, 1f), new Keyframe(1f, 0f)));
        }

        /// <summary>Ichor / blood droplets with gravity.</summary>
        public static void Droplets(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.35f, 0.7f);
            main.startSpeed = Range(2.5f, 8f);
            main.startSize = Range(0.06f, 0.13f);
            main.gravityModifier = 2.6f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Cone;
            shape.angle = 55f;
            shape.radius = 0.08f;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 1f), new Keyframe(0.7f, 0.8f), new Keyframe(1f, 0f)));
        }

        /// <summary>Soft dust puffs for footsteps, landings and rolls.</summary>
        public static void Dust(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.35f, 0.6f);
            main.startSpeed = Range(0.6f, 2.4f);
            main.startSize = Range(0.22f, 0.45f);
            main.gravityModifier = -0.05f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(0.4f, 0.05f, 0.4f);
            var vel = ps.limitVelocityOverLifetime;
            vel.enabled = true;
            vel.dampen = 0.15f;
            vel.limit = 0.5f;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 0.5f), new Keyframe(1f, 1.4f)));
            var col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                new[] { new GradientAlphaKey(0.7f, 0f), new GradientAlphaKey(0f, 1f) });
            col.color = g;
        }

        /// <summary>Glowing embers that float upward and flicker out.</summary>
        public static void Embers(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.6f, 1.4f);
            main.startSpeed = Range(0.5f, 2.2f);
            main.startSize = Range(0.03f, 0.07f);
            main.gravityModifier = -0.25f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Sphere;
            shape.radius = 0.15f;
            var noise = ps.noise;
            noise.enabled = true;
            noise.strength = 0.6f;
            noise.frequency = 1.4f;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, Fall());
        }

        /// <summary>Blue "cells" that burst out of dead enemies.</summary>
        public static void Cells(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.8f, 1.2f);
            main.startSpeed = Range(3f, 6.5f);
            main.startSize = Range(0.1f, 0.16f);
            main.gravityModifier = 0.9f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Cone;
            shape.angle = 40f;
            shape.radius = 0.2f;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 1f), new Keyframe(0.8f, 1f), new Keyframe(1f, 0f)));
        }
    }
}
