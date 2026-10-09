using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace DeadCells.EditorTools
{
    /// <summary>Builds the macOS player to Builds/DeadCellsSlice.app.</summary>
    public static class DCPlayerBuild
    {
        public const string OutputPath = "Builds/DeadCellsSlice.app";

        [MenuItem("Dead Cells/Build macOS Player")]
        public static void BuildMac()
        {
            Directory.CreateDirectory("Builds");
            var options = new BuildPlayerOptions
            {
                scenes = DCSceneBuilder.Scenes,
                locationPathName = OutputPath,
                target = BuildTarget.StandaloneOSX,
                options = BuildOptions.None,
            };
            BuildReport report = BuildPipeline.BuildPlayer(options);
            var summary = report.summary;
            Debug.Log($"[DC] build {summary.result}: {summary.outputPath} size={summary.totalSize / (1024 * 1024)}MB errors={summary.totalErrors} warnings={summary.totalWarnings} time={summary.totalTime}");
            if (Application.isBatchMode && summary.result != BuildResult.Succeeded)
                EditorApplication.Exit(1);
        }
    }
}
