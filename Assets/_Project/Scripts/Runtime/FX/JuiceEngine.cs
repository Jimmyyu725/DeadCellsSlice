using System.Collections;
using System.Collections.Generic;
using Unity.Cinemachine;
using UnityEngine;

namespace DeadCells.FX
{
    /// <summary>
    /// Game-feel hub. Every hit goes through here:
    ///  * Hit-stop: Time.timeScale = 0 for 40-80 ms (longest request wins).
    ///  * Screen shake: a directional Cinemachine impulse "kick" plus a trauma
    ///    value driving Perlin noise (amplitude = trauma^2, linear falloff),
    ///    both running on unscaled time so they keep moving during hit-stop.
    ///  * Hit sparks, flash, ichor droplets, dust, embers, cells.
    ///  * Pixel-font damage popups.
    ///  * Squash &amp; stretch punches.
    /// </summary>
    [DefaultExecutionOrder(-100)]
    public class JuiceEngine : MonoBehaviour
    {
        public static JuiceEngine Instance { get; private set; }

        [Header("Hit-stop")]
        public float minHitStop = 0.04f;
        public float maxHitStop = 0.08f;

        [Header("Shake")]
        public CinemachineImpulseSource kickSource;
        public CinemachineBasicMultiChannelPerlin traumaNoise;
        [Tooltip("Trauma lost per second (linear falloff).")]
        public float traumaFalloff = 1.6f;
        public float maxNoiseAmplitude = 1.4f;
        public float noiseFrequency = 3.2f;
        [Range(0f, 1f)] public float trauma;

        [Header("Materials")]
        public Material additiveMaterial;   // DeadCells/Particle, One One, square
        public Material flashMaterial;      // DeadCells/Particle, One One, soft disc
        public Material alphaMaterial;      // DeadCells/Particle, alpha blend, hard disc
        public Material dustMaterial;       // DeadCells/Particle, alpha blend, soft disc
        public Material textMaterial;       // DeadCells/PixelSprite

        ParticleSystem sparks, flash, droplets, dust, embers, cells;
        ParticleSystem streaks, ring, smoke, flames, bubbles, drips, frost, debris, glints;
        readonly List<DamageNumber> numbers = new List<DamageNumber>();
        float stopUntil;
        Coroutine stopRoutine;
        float baseTimeScale = 1f;

        public bool InHitStop => stopRoutine != null;

        void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            sparks = FxLibrary.Create("FX_Sparks", transform, additiveMaterial, FxLibrary.Sparks);
            flash = FxLibrary.Create("FX_Flash", transform, flashMaterial, FxLibrary.Flash);
            droplets = FxLibrary.Create("FX_Ichor", transform, alphaMaterial, FxLibrary.Droplets);
            dust = FxLibrary.Create("FX_Dust", transform, dustMaterial, FxLibrary.Dust);
            embers = FxLibrary.Create("FX_Embers", transform, additiveMaterial, FxLibrary.Embers);
            cells = FxLibrary.Create("FX_Cells", transform, flashMaterial, FxLibrary.Cells);
            streaks = FxLibrary.Create("FX_Streaks", transform, additiveMaterial, FxLibrary.Streaks);
            ring = FxLibrary.Create("FX_Ring", transform, flashMaterial, FxLibrary.Ring);
            smoke = FxLibrary.Create("FX_Smoke", transform, dustMaterial, FxLibrary.Smoke);
            flames = FxLibrary.Create("FX_Flames", transform, additiveMaterial, FxLibrary.Flames);
            bubbles = FxLibrary.Create("FX_Bubbles", transform, alphaMaterial, FxLibrary.Bubbles);
            drips = FxLibrary.Create("FX_Drips", transform, alphaMaterial, FxLibrary.Drips);
            frost = FxLibrary.Create("FX_Frost", transform, additiveMaterial, FxLibrary.Frost);
            debris = FxLibrary.Create("FX_Debris", transform, alphaMaterial, FxLibrary.Debris);
            glints = FxLibrary.Create("FX_Glints", transform, flashMaterial, FxLibrary.Glints);
            if (textMaterial != null)
                textMaterial.mainTexture = UI.PixelFont.Atlas;
        }

        void OnDestroy()
        {
            if (Instance == this)
                Instance = null;
            Time.timeScale = 1f;
        }

        void Update()
        {
            trauma = Mathf.Max(0f, trauma - traumaFalloff * Time.unscaledDeltaTime);
            if (traumaNoise != null)
            {
                traumaNoise.AmplitudeGain = trauma * trauma * maxNoiseAmplitude;
                traumaNoise.FrequencyGain = noiseFrequency;
            }
        }

        // ------------------------------------------------------------- hit-stop

        public void HitStop(float seconds)
        {
            seconds = Mathf.Clamp(seconds, 0f, 0.25f);
            if (seconds <= 0f)
                return;
            float until = Time.realtimeSinceStartup + seconds;
            if (until > stopUntil)
                stopUntil = until;
            if (stopRoutine == null)
                stopRoutine = StartCoroutine(StopRoutine());
        }

        IEnumerator StopRoutine()
        {
            baseTimeScale = Time.timeScale > 0f ? Time.timeScale : 1f;
            Time.timeScale = 0f;
            while (Time.realtimeSinceStartup < stopUntil)
                yield return null;
            // A pause opened during the freeze keeps the game stopped.
            Time.timeScale = Core.GamePause.Paused ? 0f : baseTimeScale;
            stopRoutine = null;
        }

        /// <summary>Hit-stop scaled between the configured min/max by hit weight 0..1.</summary>
        public void HitStopWeighted(float weight) => HitStop(Mathf.Lerp(minHitStop, maxHitStop, Mathf.Clamp01(weight)));

        // ---------------------------------------------------------------- shake

        /// <summary>Directional kick (impulse) + trauma (noise). strength ~0.1 light .. 1 huge.</summary>
        public void Shake(Vector2 direction, float strength)
        {
            strength *= Meta.SaveSystem.Data.settings.screenShake;
            if (strength <= 0f)
                return;
            if (kickSource != null)
            {
                Vector2 d = direction.sqrMagnitude > 1e-4f ? direction.normalized : Vector2.down;
                kickSource.GenerateImpulseWithVelocity(new Vector3(d.x, d.y, 0f) * strength * 0.45f);
            }
            trauma = Mathf.Clamp01(trauma + strength * 0.5f);
        }

        // ------------------------------------------------------------- particles

        static void Emit(ParticleSystem ps, Vector3 position, Vector2 direction, int count, Color color)
        {
            if (ps == null || count <= 0)
                return;
            var t = ps.transform;
            t.position = position;
            Vector3 dir = direction.sqrMagnitude > 1e-4f ? (Vector3)direction.normalized : Vector3.up;
            t.rotation = Quaternion.LookRotation(dir, Vector3.forward);
            var ep = new ParticleSystem.EmitParams { startColor = color, applyShapeToPosition = true };
            ps.Emit(ep, count);
        }

        public void HitSparks(Vector3 position, Vector2 direction, Color color, float weight = 0.5f)
        {
            Emit(sparks, position, direction, Mathf.RoundToInt(Mathf.Lerp(8, 22, weight)), color);
            Emit(flash, position, direction, 1, Color.Lerp(color, Color.white, 0.6f));
        }

        public void Ichor(Vector3 position, Vector2 direction, Color color, int count = 10)
        {
            Emit(droplets, position, direction, count, color);
        }

        public void Dust(Vector3 position, Vector2 direction, int count = 6, Color? color = null)
        {
            Emit(dust, position, direction, count, color ?? new Color(0.62f, 0.72f, 0.78f, 0.55f));
        }

        public void Embers(Vector3 position, int count, Color color)
        {
            Emit(embers, position, Vector2.up, count, color);
        }

        public void CellBurst(Vector3 position, int count)
        {
            Emit(cells, position, Vector2.up, count, new Color(0.45f, 1.6f, 2.6f, 1f));
        }

        /// <summary>Speed lines radiating from a big hit (crits, kills, parries).</summary>
        public void ImpactStreaks(Vector3 position, Color color, int count = 10) => Emit(streaks, position, Vector2.up, count, color);

        /// <summary>An expanding ring of light: `size` is its final diameter in metres.</summary>
        public void Ring(Vector3 position, Color color, float size = 3f)
        {
            if (ring == null)
                return;
            ring.transform.position = position + Vector3.back * 0.2f;
            ring.Emit(new ParticleSystem.EmitParams { startColor = color, startSize = size * 0.25f, position = position + Vector3.back * 0.2f,
                applyShapeToPosition = false }, 1);
        }

        public void Smoke(Vector3 position, int count, Color? color = null) =>
            Emit(smoke, position, Vector2.up, count, color ?? new Color(0.22f, 0.2f, 0.24f, 0.7f));

        public void Flames(Vector3 position, int count) => Emit(flames, position, Vector2.up, count, new Color(4f, 2.2f, 0.7f, 1f));

        public void Bubbles(Vector3 position, int count, Color color) => Emit(bubbles, position, Vector2.up, count, color);

        public void Drips(Vector3 position, int count, Color color) => Emit(drips, position, Vector2.down, count, color);

        public void Frost(Vector3 position, int count) => Emit(frost, position, Vector2.up, count, new Color(1.4f, 2.2f, 3.2f, 1f));

        public void Debris(Vector3 position, Vector2 direction, int count, Color color) => Emit(debris, position, direction, count, color);

        public void Glints(Vector3 position, int count, Color color) => Emit(glints, position, Vector2.up, count, color);

        /// <summary>Ground-slam shockwave: dust both ways along the floor plus sparks upward.</summary>
        public void SlamWave(Vector3 position, float radius)
        {
            Emit(dust, position + Vector3.left * 0.2f, Vector2.left + Vector2.up * 0.15f, 14, new Color(0.7f, 0.8f, 0.85f, 0.6f));
            Emit(dust, position + Vector3.right * 0.2f, Vector2.right + Vector2.up * 0.15f, 14, new Color(0.7f, 0.8f, 0.85f, 0.6f));
            Emit(sparks, position, Vector2.up, 24, new Color(1.8f, 1.4f, 0.8f, 1f));
            Emit(flash, position + Vector3.up * 0.3f, Vector2.up, 1, new Color(1.5f, 1.4f, 1.6f, 1f));
        }

        // --------------------------------------------------------------- numbers

        public void DamagePopup(Vector3 position, float amount, bool critical, Color? colorOverride = null)
        {
            Color c = colorOverride ?? (critical ? new Color(1f, 0.85f, 0.2f) : Color.white);
            string label = Mathf.RoundToInt(amount).ToString();
            if (critical)
                label += "!";
            Popup(position, label, c, critical);
        }

        public void Popup(Vector3 position, string text, Color color, bool big)
        {
            DamageNumber n = null;
            foreach (var d in numbers)
            {
                if (!d.Alive)
                {
                    n = d;
                    break;
                }
            }
            if (n == null)
            {
                var go = new GameObject("DamageNumber", typeof(MeshFilter), typeof(MeshRenderer));
                go.transform.SetParent(transform, false);
                go.GetComponent<MeshRenderer>().sharedMaterial = textMaterial;
                n = go.AddComponent<DamageNumber>();
                numbers.Add(n);
            }
            n.Show(position, text, color, big);
        }

        // ---------------------------------------------------------------- squash

        public static void Squash(SquashStretch target, Vector2 scale)
        {
            if (target != null)
                target.Punch(scale);
        }
    }
}
