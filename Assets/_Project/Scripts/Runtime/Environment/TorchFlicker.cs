using UnityEngine;

namespace DeadCells.Environment
{
    /// <summary>Warm wall torch: Perlin-driven intensity and radius jitter plus a slight positional wobble.</summary>
    [RequireComponent(typeof(Light))]
    public class TorchFlicker : MonoBehaviour
    {
        public float baseIntensity = 4f;
        [Range(0f, 1f)] public float intensityJitter = 0.1f;
        public float baseRange = 7f;
        [Range(0f, 1f)] public float rangeJitter = 0.04f;
        public float speed = 3.5f;
        public float wobble = 0.03f;
        public Renderer flameRenderer;

        Light torchLight;
        Vector3 origin;
        float seed;

        void Awake()
        {
            torchLight = GetComponent<Light>();
            origin = transform.localPosition;
            seed = Random.value * 100f;
        }

        void Update()
        {
            float t = Time.time * speed + seed;
            float n = Mathf.PerlinNoise(t, seed) * 0.7f + Mathf.PerlinNoise(t * 2.7f, seed + 3f) * 0.3f;
            float k = (n - 0.5f) * 2f;
            torchLight.intensity = baseIntensity * (1f + k * intensityJitter);
            torchLight.range = baseRange * (1f + k * rangeJitter);
            transform.localPosition = origin + new Vector3(
                (Mathf.PerlinNoise(t * 0.8f, seed + 7f) - 0.5f) * wobble,
                (Mathf.PerlinNoise(t * 0.8f, seed + 11f) - 0.5f) * wobble, 0f);
        }
    }
}
