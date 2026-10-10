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
            // -dcBuildPath <path>: test builds go elsewhere so a running copy of the
            // game (Builds/DeadCellsSlice.app) never has its data swapped underneath it.
            string path = OutputPath;
            var args = System.Environment.GetCommandLineArgs();
            int ai = System.Array.IndexOf(args, "-dcBuildPath");
            if (ai >= 0 && ai + 1 < args.Length)
                path = args[ai + 1];
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path)));
            var options = new BuildPlayerOptions
            {
                scenes = DCSceneBuilder.Scenes,
                locationPathName = path,
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
