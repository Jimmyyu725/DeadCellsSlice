using UnityEngine;

namespace DeadCells.Environment
{
    /// <summary>
    /// Pushes the global art-direction values read by the toon shaders:
    /// depth fog that melts the Z=5 / Z=10 silhouettes into the haze, a floor
    /// glow, and a flat ambient fill colour.
    /// </summary>
    [ExecuteAlways]
    public class DCAtmosphere : MonoBehaviour
    {
        public static readonly Color DefaultFogColor = new Color(0.10f, 0.26f, 0.32f);

        [ColorUsage(false, true)] public Color fogColor = DefaultFogColor;
        [Range(0f, 1f)] public float fogMax = 0.9f;
        public float fogStartZ = 0.6f;
        [Tooltip("Exponential fog density per metre of depth behind the start plane.")]
        public float fogDensity = 0.15f;
        public float floorGlowHeight = -1f;
        [Range(0f, 1f)] public float floorGlow = 0.35f;
        [ColorUsage(false, true)] public Color ambientFill = new Color(0.035f, 0.05f, 0.075f);

        static readonly int FogColorId = Shader.PropertyToID("_DC_FogColor");
        static readonly int FogParamsId = Shader.PropertyToID("_DC_FogParams");
        static readonly int AmbientId = Shader.PropertyToID("_DC_AmbientColor");

        void OnEnable() => Push();
        void OnValidate() => Push();
        void Update() => Push();

        void Push()
        {
            Shader.SetGlobalVector(FogColorId, new Vector4(fogColor.r, fogColor.g, fogColor.b, fogMax));
            Shader.SetGlobalVector(FogParamsId, new Vector4(fogStartZ, fogDensity, floorGlowHeight, floorGlow));
            Shader.SetGlobalVector(AmbientId, new Vector4(ambientFill.r, ambientFill.g, ambientFill.b, 0f));
        }
    }
}
