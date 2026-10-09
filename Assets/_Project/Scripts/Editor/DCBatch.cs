using System.Linq;
using UnityEditor;
using UnityEngine;

namespace DeadCells.EditorTools
{
    /// <summary>Command-line entry points (unity run . -- -executeMethod DeadCells.EditorTools.DCBatch.X).</summary>
    public static class DCBatch
    {
        /// <summary>
        /// Compiles every pass of every project shader for Metal (vertex +
        /// fragment, default keywords) and reports real HLSL errors.
        /// </summary>
        public static void CheckShaders()
        {
            int errors = 0;
            var guids = AssetDatabase.FindAssets("t:Shader", new[] { "Assets/_Project/Shaders" });
            foreach (var guid in guids)
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var shader = AssetDatabase.LoadAssetAtPath<Shader>(path);
                var data = ShaderUtil.GetShaderData(shader);
                int passes = 0;
                int shaderErrors = 0;
                for (int s = 0; s < data.SubshaderCount; s++)
                {
                    var sub = data.GetSubshader(s);
                    for (int p = 0; p < sub.PassCount; p++)
                    {
                        var pass = sub.GetPass(p);
                        passes++;
                        foreach (var stage in new[] { UnityEditor.Rendering.ShaderType.Vertex, UnityEditor.Rendering.ShaderType.Fragment })
                        {
                            if (!pass.HasShaderStage(stage))
                                continue;
                            foreach (var keywords in KeywordSets(pass.Name))
                            {
                            var result = pass.CompileVariant(stage, keywords, UnityEditor.Rendering.ShaderCompilerPlatform.Metal, BuildTarget.StandaloneOSX);
                            foreach (var m in result.Messages)
                            {
                                if (m.severity == UnityEditor.Rendering.ShaderCompilerMessageSeverity.Error)
                                {
                                    shaderErrors++;
                                    Debug.Log($"[DC][shader]   ERROR {shader.name}/{pass.Name}/{stage}: {m.message} ({m.file}:{m.line})");
                                }
                                else
                                    Debug.Log($"[DC][shader]   warn {shader.name}/{pass.Name}/{stage}: {m.message}");
                            }
                            if (!result.Success && result.Messages.Length == 0)
                                shaderErrors++;
                            }
                        }
                    }
                }
                errors += shaderErrors;
                Debug.Log($"[DC][shader] {(shaderErrors > 0 ? "ERROR" : "ok")} {shader.name} passes={passes}");
            }
            Debug.Log($"[DC] shader check done, errors={errors}");
        }

        static string[][] KeywordSets(string passName)
        {
            if (passName != "ForwardLit")
                return new[] { new string[0] };
            return new[]
            {
                new string[0],
                new[] { "_MAIN_LIGHT_SHADOWS_CASCADE", "_ADDITIONAL_LIGHTS", "_CLUSTER_LIGHT_LOOP", "_SHADOWS_SOFT" },
                new[] { "_MAIN_LIGHT_SHADOWS", "_ADDITIONAL_LIGHTS", "_ADDITIONAL_LIGHT_SHADOWS" },
            };
        }

        public static void Setup()
        {
            DCProjectSetup.ConfigureAll();
            CheckShaders();
        }

        public static void BuildContent()
        {
            DCProjectSetup.ConfigureAll();
            DCContentBuilder.BuildAll();
            DCSceneBuilder.BuildScene();
            CheckShaders();
            AssetDatabase.SaveAssets();
        }

        public static void BuildPlayer()
        {
            DCPlayerBuild.BuildMac();
        }

        public static void All()
        {
            BuildContent();
            DCPlayerBuild.BuildMac();
        }
    }
}
