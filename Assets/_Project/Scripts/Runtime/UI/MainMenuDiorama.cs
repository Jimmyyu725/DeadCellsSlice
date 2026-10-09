using DeadCells.Environment;
using DeadCells.Run;
using UnityEngine;

namespace DeadCells.UI
{
    /// <summary>Builds the Oubliette backdrop behind the title screen from the "menu" room template.</summary>
    public class MainMenuDiorama : MonoBehaviour
    {
        public BiomeDef biome;
        public DCAtmosphere atmosphere;
        public Camera cam;
        public Light keyLight;
        public Light rimLight;
        public AmbientParticles ambient;
        public Transform hero;

        void Awake()
        {
            if (biome == null)
                return;
            var data = LevelGenerator.Generate(biome, 7, "menu");
            var built = LevelBuilder.Build(data, biome, transform, 7);
            if (hero != null)
                hero.position = built.playerStart;
            if (atmosphere != null)
            {
                atmosphere.fogColor = biome.fogColor;
                atmosphere.fogDensity = biome.fogDensity;
                atmosphere.ambientFill = biome.ambient;
            }
            if (cam != null)
            {
                cam.backgroundColor = biome.fogColor.gamma;
                cam.transform.position = built.playerStart + new Vector3(-3.2f, 2.4f, -15f);
            }
            RenderSettings.ambientLight = biome.ambientLight;
            if (keyLight != null)
            {
                keyLight.color = biome.keyColor;
                keyLight.intensity = biome.keyIntensity;
                keyLight.transform.rotation = Quaternion.Euler(biome.keyEuler);
            }
            if (rimLight != null)
            {
                rimLight.color = biome.rimColor;
                rimLight.intensity = biome.rimIntensity;
            }
            ambient?.Apply(biome.motesA, biome.motesB, biome.embersA, biome.embersB, biome.rainUp);
        }
    }
}
