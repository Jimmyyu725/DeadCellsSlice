using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace DeadCells.Rendering
{
    /// <summary>
    /// Owns the global post-processing profile at runtime. The profile is built
    /// in code once per session and never unloaded, so scene reloads cannot hand
    /// URP a half-unloaded profile asset (its component list came back null after
    /// "Retry", URP threw every frame and the screen froze). If the list is ever
    /// lost anyway, the profile is rebuilt before the next frame renders.
    /// </summary>
    [RequireComponent(typeof(Volume))]
    public class PostFx : MonoBehaviour
    {
        static VolumeProfile runtimeProfile;
        Volume volume;

        public static VolumeProfile Profile
        {
            get
            {
                if (runtimeProfile == null || runtimeProfile.components == null)
                {
                    runtimeProfile = ScriptableObject.CreateInstance<VolumeProfile>();
                    runtimeProfile.name = "PostFx (runtime)";
                    Fill(runtimeProfile);
                    runtimeProfile.hideFlags = HideFlags.DontUnloadUnusedAsset;
                    foreach (var c in runtimeProfile.components)
                        c.hideFlags = HideFlags.DontUnloadUnusedAsset;
                }
                return runtimeProfile;
            }
        }

        void Awake()
        {
            volume = GetComponent<Volume>();
            volume.sharedProfile = Profile;
        }

        void LateUpdate()
        {
            var p = volume.sharedProfile;
            if (p == null || p.components == null)
            {
                Debug.LogWarning("[DC] post profile lost its components; rebuilding");
                volume.sharedProfile = Profile;
            }
        }

        /// <summary>The game's grade: ACES, soft bloom, warm highlights over cool shadows.</summary>
        public static void Fill(VolumeProfile profile)
        {
            var tone = profile.Add<Tonemapping>(true);
            tone.mode.Override(TonemappingMode.ACES);

            var bloom = profile.Add<Bloom>(true);
            bloom.threshold.Override(0.9f);
            bloom.intensity.Override(1.15f);
            bloom.scatter.Override(0.7f);
            bloom.highQualityFiltering.Override(true);
            bloom.tint.Override(new Color(1f, 0.93f, 0.98f));

            var color = profile.Add<ColorAdjustments>(true);
            color.postExposure.Override(0.35f);
            color.contrast.Override(24f);
            color.saturation.Override(26f);
            color.colorFilter.Override(new Color(1f, 0.98f, 0.96f));

            var smh = profile.Add<ShadowsMidtonesHighlights>(true);
            smh.shadows.Override(new Vector4(0.92f, 0.98f, 1.12f, -0.02f));
            smh.midtones.Override(new Vector4(1f, 1f, 1f, 0f));
            smh.highlights.Override(new Vector4(1.12f, 1.02f, 0.9f, 0.03f));

            var split = profile.Add<SplitToning>(true);
            split.shadows.Override(new Color(0.24f, 0.38f, 0.55f));
            split.highlights.Override(new Color(1f, 0.72f, 0.45f));
            split.balance.Override(-15f);

            var vignette = profile.Add<Vignette>(true);
            vignette.intensity.Override(0.3f);
            vignette.smoothness.Override(0.45f);
            vignette.color.Override(new Color(0.02f, 0.03f, 0.06f));
        }
    }
}
