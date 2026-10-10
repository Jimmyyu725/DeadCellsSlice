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

        static Gradient FadeOut(float startAlpha = 1f, float hold = 0.2f)
        {
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                new[] { new GradientAlphaKey(startAlpha, 0f), new GradientAlphaKey(startAlpha, hold), new GradientAlphaKey(0f, 1f) });
            return g;
        }

        /// <summary>Speed lines bursting out of a heavy hit (crits, kills, parries).</summary>
        public static void Streaks(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.08f, 0.16f);
            main.startSpeed = Range(16f, 30f);
            main.startSize = Range(0.05f, 0.09f);
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Circle;
            shape.radius = 0.15f;
            shape.arc = 360f;
            var r = ps.GetComponent<ParticleSystemRenderer>();
            r.renderMode = ParticleSystemRenderMode.Stretch;
            r.velocityScale = 0.05f;
            r.lengthScale = 2f;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, Fall());
        }

        /// <summary>An expanding ring (one particle) for parries, explosions and big landings.</summary>
        public static void Ring(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = 0.28f;
            main.startSpeed = 0f;
            main.startSize = 1f;
            var shape = ps.shape;
            shape.enabled = false;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(4f, new AnimationCurve(new Keyframe(0f, 0.1f, 0f, 3f), new Keyframe(1f, 1f)));
            var col = ps.colorOverLifetime;
            col.enabled = true;
            col.color = FadeOut(1f, 0.05f);
        }

        /// <summary>Slow, soft smoke puffs that rise and spread.</summary>
        public static void Smoke(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.8f, 1.6f);
            main.startSpeed = Range(0.3f, 1.4f);
            main.startSize = Range(0.5f, 1.1f);
            main.startRotation = Range(0f, 6.28f);
            main.gravityModifier = -0.12f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Sphere;
            shape.radius = 0.3f;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 0.5f), new Keyframe(1f, 1.8f)));
            var col = ps.colorOverLifetime;
            col.enabled = true;
            col.color = FadeOut(0.55f, 0.1f);
            var noise = ps.noise;
            noise.enabled = true;
            noise.strength = 0.4f;
            noise.frequency = 0.8f;
        }

        /// <summary>Licking flame tongues for burning targets: rise fast, shrink, cool from yellow to red.</summary>
        public static void Flames(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.3f, 0.55f);
            main.startSpeed = Range(1.2f, 2.6f);
            main.startSize = Range(0.4f, 0.7f);
            main.gravityModifier = -0.6f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(0.6f, 0.15f, 0.4f);
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, Fall());
            var col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(new Color(1f, 0.95f, 0.6f), 0f), new GradientColorKey(new Color(1f, 0.45f, 0.1f), 0.5f),
                    new GradientColorKey(new Color(0.7f, 0.1f, 0.05f), 1f) },
                new[] { new GradientAlphaKey(1f, 0f), new GradientAlphaKey(0.9f, 0.6f), new GradientAlphaKey(0f, 1f) });
            col.color = g;
            var noise = ps.noise;
            noise.enabled = true;
            noise.strength = 0.7f;
            noise.frequency = 2.5f;
        }

        /// <summary>Little bubbles wobbling upward (poison).</summary>
        public static void Bubbles(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.6f, 1.1f);
            main.startSpeed = Range(0.4f, 1.1f);
            main.startSize = Range(0.1f, 0.2f);
            main.gravityModifier = -0.15f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(0.6f, 0.15f, 1.2f);
            var noise = ps.noise;
            noise.enabled = true;
            noise.strength = 0.5f;
            noise.frequency = 3f;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 0.6f), new Keyframe(0.85f, 1.1f), new Keyframe(1f, 0f)));
        }

        /// <summary>Heavy drops that fall straight down (bleeding, oil, sewer water).</summary>
        public static void Drips(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.5f, 0.9f);
            main.startSpeed = Range(0f, 0.6f);
            main.startSize = Range(0.09f, 0.14f);
            main.gravityModifier = 1.8f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(0.5f, 0.1f, 0.3f);
            var r = ps.GetComponent<ParticleSystemRenderer>();
            r.renderMode = ParticleSystemRenderMode.Stretch;
            r.velocityScale = 0.02f;
            r.lengthScale = 1.4f;
        }

        /// <summary>Glittering ice crystals and a pale mist (frozen targets).</summary>
        public static void Frost(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.5f, 1.0f);
            main.startSpeed = Range(0.1f, 0.6f);
            main.startSize = Range(0.08f, 0.16f);
            main.startRotation = Range(0f, 6.28f);
            main.gravityModifier = 0.08f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(0.8f, 0.2f, 1.6f);
            var col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.15f), new GradientAlphaKey(1f, 0.5f), new GradientAlphaKey(0f, 1f) });
            col.color = g;
        }

        /// <summary>Stone chunks and splinters thrown out of broken walls and heavy slams.</summary>
        public static void Debris(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.5f, 0.95f);
            main.startSpeed = Range(3f, 8f);
            main.startSize = Range(0.08f, 0.2f);
            main.startRotation = Range(0f, 6.28f);
            main.gravityModifier = 2.4f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Cone;
            shape.angle = 50f;
            shape.radius = 0.3f;
            var rot = ps.rotationOverLifetime;
            rot.enabled = true;
            rot.z = Range(-8f, 8f);
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 1f), new Keyframe(0.8f, 0.9f), new Keyframe(1f, 0f)));
        }

        /// <summary>Twinkles: a quick swell and fade, almost no motion (gold, items, magic).</summary>
        public static void Glints(ParticleSystem ps)
        {
            var main = ps.main;
            main.startLifetime = Range(0.25f, 0.45f);
            main.startSpeed = Range(0f, 0.3f);
            main.startSize = Range(0.08f, 0.16f);
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Sphere;
            shape.radius = 0.35f;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 0f), new Keyframe(0.3f, 1f), new Keyframe(1f, 0f)));
        }
    }
}
