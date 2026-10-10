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

        /// <summary>Generate every biome in edit mode and log geometry/light statistics.</summary>
        public static void LevelStats()
        {
            UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene);
            foreach (var id in new[] { "Oubliette", "Promenade", "Ossuary", "StiltVillage", "ClockLung", "Passage" })
            {
                var biome = AssetDatabase.LoadAssetAtPath<DeadCells.Run.BiomeDef>($"{DCContentBuilder.ContentDir}/Biomes/{id}.asset");
                var data = DeadCells.Run.LevelGenerator.Generate(biome, 12345);
                var built = DeadCells.Run.LevelBuilder.Build(data, biome, null, 12345);
                Object.DestroyImmediate(built.root);
            }
        }

        /// <summary>Dump generated levels (many seeds) as text for Tools/Rooms/validate_levels.py.</summary>
        /// <summary>
        /// Rebuild one reported level and print it with coordinate rulers:
        ///   -executeMethod DeadCells.EditorTools.DCBatch.DumpOne -dcArea Oubliette -dcSeed 12345 [-dcX 120 -dcY 33]
        /// Writes Tools/_out/levels/one.txt (map, '@' at X/Y) and one.rooms.
        /// </summary>
        public static void DumpOne()
        {
            var args = System.Environment.GetCommandLineArgs();
            string Arg(string name, string fallback)
            {
                int i = System.Array.IndexOf(args, name);
                return i >= 0 && i + 1 < args.Length ? args[i + 1] : fallback;
            }
            string id = Arg("-dcArea", "Oubliette");
            int seed = int.Parse(Arg("-dcSeed", "7919"));
            int mx = int.Parse(Arg("-dcX", "-1")), my = int.Parse(Arg("-dcY", "-1"));
            var biome = AssetDatabase.LoadAssetAtPath<DeadCells.Run.BiomeDef>($"{DCContentBuilder.ContentDir}/Biomes/{id}.asset");
            var d = DeadCells.Run.LevelGenerator.Generate(biome, seed);
            var sb = new System.Text.StringBuilder();
            sb.Append($"{id} seed {seed}  {d.width}x{d.height}  (x right, y up; '@' = {mx},{my})\n      ");
            for (int x = 0; x < d.width; x++)
                sb.Append(x % 10 == 0 ? (char)('0' + (x / 10) % 10) : ' ');
            sb.Append("\n      ");
            for (int x = 0; x < d.width; x++)
                sb.Append((char)('0' + x % 10));
            sb.Append('\n');
            for (int y = d.height - 1; y >= 0; y--)
            {
                sb.Append($"{y,4}  ");
                for (int x = 0; x < d.width; x++)
                {
                    char c = d.tiles[x, y] switch
                    {
                        DeadCells.Run.Tile.Solid => '#',
                        DeadCells.Run.Tile.OneWay => '=',
                        DeadCells.Run.Tile.Liquid => '~',
                        DeadCells.Run.Tile.Spikes => 'X',
                        _ => '.',
                    };
                    foreach (var sp in d.spawns)
                        if (sp.cell.x == x && sp.cell.y == y && "PTDKMp".IndexOf(sp.code) >= 0)
                            c = sp.code;
                    if (x == mx && y == my)
                        c = '@';
                    sb.Append(c);
                }
                sb.Append('\n');
            }
            System.IO.Directory.CreateDirectory("Tools/_out/levels");
            System.IO.File.WriteAllText("Tools/_out/levels/one.txt", sb.ToString());
            var rooms = new System.Text.StringBuilder();
            foreach (var r in d.rooms)
                rooms.AppendLine($"{r.template} {r.kind} x {r.rect.xMin}..{r.rect.xMax - 1} y {r.rect.yMin}..{r.rect.yMax - 1}" +
                                 (r.rect.Contains(new Vector2Int(mx, my)) ? "   <== @" : ""));
            System.IO.File.WriteAllText("Tools/_out/levels/one.rooms", rooms.ToString());
            Debug.Log($"[DC] dumped {id} seed {seed}");
        }

        public static void DumpLevels()
        {
            string dir = "Tools/_out/levels";
            System.IO.Directory.CreateDirectory(dir);
            foreach (var f in System.IO.Directory.GetFiles(dir, "*.txt"))
                System.IO.File.Delete(f);
            foreach (var id in new[] { "Oubliette", "Promenade", "Ossuary", "StiltVillage", "ClockLung", "Passage" })
            {
                var biome = AssetDatabase.LoadAssetAtPath<DeadCells.Run.BiomeDef>($"{DCContentBuilder.ContentDir}/Biomes/{id}.asset");
                for (int seed = 1; seed <= 40; seed++)
                {
                    var d = DeadCells.Run.LevelGenerator.Generate(biome, seed * 7919);
                    var sb = new System.Text.StringBuilder();
                    for (int y = d.height - 1; y >= 0; y--)
                    {
                        for (int x = 0; x < d.width; x++)
                        {
                            char c = d.tiles[x, y] switch
                            {
                                DeadCells.Run.Tile.Solid => '#',
                                DeadCells.Run.Tile.OneWay => '=',
                                DeadCells.Run.Tile.Liquid => '~',
                                DeadCells.Run.Tile.Spikes => 'X',
                                _ => '.',
                            };
                            foreach (var s in d.spawns)
                                if (s.cell.x == x && s.cell.y == y && "PTDKMp".IndexOf(s.code) >= 0)
                                    c = s.code;
                            sb.Append(c);
                        }
                        sb.Append('\n');
                    }
                    System.IO.File.WriteAllText($"{dir}/{id}_{seed:00}.txt", sb.ToString());
                    var rooms = new System.Text.StringBuilder();
                    foreach (var r in d.rooms)
                        rooms.AppendLine($"{r.template} {r.kind} {r.rect.xMin} {r.rect.yMin} {r.rect.width} {r.rect.height}");
                    System.IO.File.WriteAllText($"{dir}/{id}_{seed:00}.rooms", rooms.ToString());
                }
            }
            Debug.Log("[DC] levels dumped");
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
