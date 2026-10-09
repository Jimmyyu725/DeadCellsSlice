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
        static readonly HashSet<string> LoopClips = new HashSet<string> { "Idle", "Run", "Jump_Rise", "Jump_Fall" };

        void OnPreprocessTexture()
        {
            if (!assetPath.StartsWith(ArtRoot))
                return;
            var ti = (TextureImporter)assetImporter;
            string file = System.IO.Path.GetFileNameWithoutExtension(assetPath);
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

        void OnPreprocessModel()
        {
            if (!assetPath.StartsWith(ArtRoot))
                return;
            var mi = (ModelImporter)assetImporter;
            bool character = assetPath.Contains("/Characters/");
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
            // Environment kit meshes are merged at load time by LevelGeometry.
            mi.isReadable = assetPath.Contains("/Environment/");
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
            if (!assetPath.StartsWith(ArtRoot) || !assetPath.Contains("/Characters/"))
                return;
            var mi = (ModelImporter)assetImporter;
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
