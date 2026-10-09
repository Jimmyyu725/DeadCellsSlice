using System.Collections;
using DeadCells.Player;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.Core
{
    /// <summary>
    /// Session flow: spawn/respawn of the Beheaded, flame-colour presets (F),
    /// and frame-rate setup. Also hosts the autoplay demo when launched with
    /// -autoplay (see AutoplayDirector).
    /// </summary>
    public class GameManager : MonoBehaviour
    {
        [System.Serializable]
        public class FlamePreset
        {
            public string name;
            [ColorUsage(false, true)] public Color core;
            [ColorUsage(false, true)] public Color flame;
            [ColorUsage(false, true)] public Color tip;
            [ColorUsage(false, true)] public Color glow;   // neck/emission + point light
        }

        public PlayerController player;
        public Transform spawnPoint;
        public Material flameMaterial;
        public Material bodyMaterial;
        public Material smokeMaterial;
        public Light flameLight;
        public FlamePreset[] flamePresets =
        {
            new FlamePreset { name = "Occult Purple", core = new Color(4.2f, 3.6f, 4.6f), flame = new Color(2.4f, 1.1f, 4.2f), tip = new Color(0.55f, 0.12f, 1.1f), glow = new Color(0.61f, 0.36f, 0.9f) },
            new FlamePreset { name = "Toxic Green", core = new Color(3.8f, 4.6f, 3.2f), flame = new Color(0.9f, 3.4f, 0.35f), tip = new Color(0.12f, 0.75f, 0.05f), glow = new Color(0.22f, 0.69f, 0.0f) },
            new FlamePreset { name = "Classic Ember", core = new Color(4.8f, 4.0f, 2.6f), flame = new Color(4.0f, 1.5f, 0.35f), tip = new Color(1.2f, 0.18f, 0.05f), glow = new Color(1.0f, 0.45f, 0.15f) },
        };
        public int flameIndex;

        static readonly int CoreId = Shader.PropertyToID("_CoreColor");
        static readonly int FlameId = Shader.PropertyToID("_FlameColor");
        static readonly int TipId = Shader.PropertyToID("_TipColor");
        static readonly int EmissionId = Shader.PropertyToID("_EmissionColor");
        static readonly int GlowId = Shader.PropertyToID("_GlowColor");

        public static GameManager Instance { get; private set; }

        void Awake()
        {
            Instance = this;
            Application.targetFrameRate = 120;
            QualitySettings.vSyncCount = 1;
        }

        void Start()
        {
            if (player != null)
            {
                player.Died += () => StartCoroutine(RespawnRoutine());
                if (spawnPoint != null)
                    player.transform.position = spawnPoint.position;
            }
            ApplyFlame(flameIndex);
        }

        void Update()
        {
            if (player != null && player.Input.cycleFlamePressed)
            {
                ApplyFlame((flameIndex + 1) % flamePresets.Length);
                FX.JuiceEngine.Instance?.Popup(player.transform.position + Vector3.up * 2.5f,
                    flamePresets[flameIndex].name.ToUpperInvariant(), flamePresets[flameIndex].glow * 1.6f, false);
            }
        }

        public void ApplyFlame(int index)
        {
            flameIndex = Mathf.Clamp(index, 0, flamePresets.Length - 1);
            var p = flamePresets[flameIndex];
            if (flameMaterial != null)
            {
                flameMaterial.SetColor(CoreId, p.core);
                flameMaterial.SetColor(FlameId, p.flame);
                flameMaterial.SetColor(TipId, p.tip);
            }
            if (bodyMaterial != null)
                bodyMaterial.SetColor(EmissionId, p.glow * 2.2f);
            if (smokeMaterial != null)
                smokeMaterial.SetColor(GlowId, p.glow * 1.4f);
            if (flameLight != null)
                flameLight.color = p.glow;
        }

        IEnumerator RespawnRoutine()
        {
            yield return new WaitForSeconds(1.1f);
            GameHUD.Instance?.Fade(true);
            yield return new WaitForSeconds(0.7f);
            player.Respawn(spawnPoint != null ? spawnPoint.position : Vector3.zero);
            GameHUD.Instance?.Fade(false);
        }

        void OnDestroy()
        {
            if (Instance == this)
                Instance = null;
            // Materials are assets: leave them on the default preset in the editor.
            if (flamePresets.Length > 0)
                ApplyFlame(0);
        }
    }
}
