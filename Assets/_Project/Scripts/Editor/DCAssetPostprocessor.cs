using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace DeadCells.EditorTools
{
    /// <summary>
    /// Import rules for everything the Blender pipeline writes into
    /// Assets/_Project/Art (see Tools/PIPELINE.md):
    ///  * *_Normal -> normal map, *_ORM -> linear data, others sRGB.
    ///  * FBX: metric scale, axis conversion baked, no imported materials,
    ///    Mikk tangents (matches the Cycles bake).
    ///  * Character takes "Rig|Action" become clean clip names; locomotion
    ///    clips loop (and drop the duplicated closing frame).
    /// </summary>
    public class DCAssetPostprocessor : AssetPostprocessor
    {
        const string ArtRoot = "Assets/_Project/Art/";
        const string AudioRoot = "Assets/_Project/Audio/";
        static readonly HashSet<string> LoopClips = new HashSet<string> { "Idle", "Run", "Jump_Rise", "Jump_Fall" };
        // Static props that live next to a character's FBX (boss weapons) and the rig-less creatures.
        static readonly HashSet<string> StaticInCharacters = new HashSet<string> { "Greatsword", "Shovel" };

        void OnPreprocessTexture()
        {
            if (!assetPath.StartsWith(ArtRoot))
                return;
            var ti = (TextureImporter)assetImporter;
            string file = System.IO.Path.GetFileNameWithoutExtension(assetPath);
            if (assetPath.Contains("/Icons/"))
            {
                // Inventory icons rendered by Tools/Blender/render_icons.py: crisp pixel sprites.
                ti.textureType = TextureImporterType.Sprite;
                ti.spriteImportMode = SpriteImportMode.Single;
                ti.alphaIsTransparency = true;
                ti.mipmapEnabled = false;
                ti.filterMode = FilterMode.Point;
                ti.textureCompression = TextureImporterCompression.Uncompressed;
                ti.spritePixelsPerUnit = 64;
                return;
            }
            ti.textureType = file.EndsWith("_Normal") ? TextureImporterType.NormalMap : TextureImporterType.Default;
            ti.sRGBTexture = !(file.EndsWith("_Normal") || file.EndsWith("_ORM"));
            ti.mipmapEnabled = true;
            ti.filterMode = FilterMode.Bilinear;
            ti.anisoLevel = 4;
            ti.wrapMode = TextureWrapMode.Clamp;
            ti.maxTextureSize = 2048;
            ti.textureCompression = TextureImporterCompression.CompressedHQ;
            ti.alphaSource = TextureImporterAlphaSource.None;
        }

        /// <summary>
        /// Audio written by Tools/Audio/make_audio.py: effects decompress on load
        /// (mono, low latency); music and ambience stream as Vorbis.
        /// </summary>
        void OnPreprocessAudio()
        {
            if (!assetPath.StartsWith(AudioRoot))
                return;
            var ai = (AudioImporter)assetImporter;
            bool bed = assetPath.Contains("/Music/") || assetPath.Contains("/Ambience/");
            var settings = ai.defaultSampleSettings;
            if (bed)
            {
                settings.loadType = AudioClipLoadType.Streaming;
                settings.compressionFormat = AudioCompressionFormat.Vorbis;
                settings.quality = 0.6f;
                ai.forceToMono = false;
                ai.loadInBackground = true;
            }
            else
            {
                settings.loadType = AudioClipLoadType.DecompressOnLoad;
                settings.compressionFormat = AudioCompressionFormat.ADPCM;
                ai.forceToMono = true;
                ai.loadInBackground = false;
            }
            settings.preloadAudioData = !bed;
            ai.defaultSampleSettings = settings;
        }

        void OnPreprocessModel()
        {
            if (!assetPath.StartsWith(ArtRoot))
                return;
            var mi = (ModelImporter)assetImporter;
            string file = System.IO.Path.GetFileNameWithoutExtension(assetPath);
            bool character = assetPath.Contains("/Characters/") && !assetPath.Contains("/Creatures/") && !StaticInCharacters.Contains(file);
            mi.globalScale = 1f;
            mi.useFileScale = true;
            mi.bakeAxisConversion = true;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importVisibility = false;
            mi.importBlendShapes = false;
            mi.materialImportMode = ModelImporterMaterialImportMode.None;
            mi.importNormals = ModelImporterNormals.Import;
            mi.importTangents = ModelImporterTangents.CalculateMikk;
            mi.meshCompression = ModelImporterMeshCompression.Off;
            // Environment and biome kit meshes are merged at runtime by the level builder.
            mi.isReadable = assetPath.Contains("/Environment/") || assetPath.Contains("/Biomes/");
            mi.sortHierarchyByName = false;
            if (character)
            {
                mi.animationType = ModelImporterAnimationType.Generic;
                mi.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
                mi.importAnimation = true;
                mi.animationCompression = ModelImporterAnimationCompression.Off;
                mi.resampleCurves = true;
                mi.optimizeGameObjects = false;
            }
            else
            {
                mi.animationType = ModelImporterAnimationType.None;
                mi.importAnimation = false;
            }
        }

        void OnPreprocessAnimation()
        {
            if (!assetPath.StartsWith(ArtRoot) || !assetPath.Contains("/Characters/") || assetPath.Contains("/Creatures/"))
                return;
            var mi = (ModelImporter)assetImporter;
            if (mi.animationType == ModelImporterAnimationType.None)
                return;
            var clips = mi.defaultClipAnimations;
            if (clips == null || clips.Length == 0)
                return;
            string owner = System.IO.Path.GetFileNameWithoutExtension(assetPath) + "_";
            var result = new List<ModelImporterClipAnimation>();
            foreach (var c in clips)
            {
                string name = CleanName(c.takeName, owner);
                c.name = name;
                bool loop = LoopClips.Contains(name);
                c.loopTime = loop;
                c.loopPose = false; // Blender loops already end on their first pose.
                c.lockRootRotation = false;
                c.lockRootHeightY = false;
                c.lockRootPositionXZ = false;
                c.keepOriginalOrientation = true;
                c.keepOriginalPositionY = true;
                c.keepOriginalPositionXZ = true;
                result.Add(c);
            }
            mi.clipAnimations = result.OrderBy(c => c.name).ToArray();
        }

        public static string CleanName(string take, string ownerPrefix)
        {
            int bar = take.LastIndexOf('|');
            string name = bar >= 0 ? take.Substring(bar + 1) : take;
            if (name.StartsWith(ownerPrefix))
                name = name.Substring(ownerPrefix.Length);
            int dot = name.IndexOf('.');
            if (dot > 0)
                name = name.Substring(0, dot);
            return name;
        }
    }
}
