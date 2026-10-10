using System.Collections.Generic;
using System.IO;
using DeadCells.Core;
using DeadCells.Items;
using DeadCells.Run;
using UnityEditor;
using UnityEngine;

namespace DeadCells.EditorTools
{
    /// <summary>
    /// 0.6 content from Tools/Blender/sanctum_props.py: the Mutator, Blacksmith
    /// and Tailor NPCs, amulets, rune tablets and the secret / rune blocks, plus
    /// item colours (Brutality / Tactics / Survival) for every weapon.
    /// </summary>
    public static partial class DCContentBuilder
    {
        const string SanctumDir = PropsDir + "/Sanctum";
        const string RelicsDir = PropsDir + "/Relics";

        static bool SanctumReady => File.Exists($"{SanctumDir}/Mutator.fbx") && File.Exists($"{RelicsDir}/AmuletEmber.fbx");

        static void BuildSanctumMaterials()
        {
            foreach (var (kit, dir) in new[] { ("Sanctum", SanctumDir), ("Relics", RelicsDir) })
            {
                if (!Directory.Exists($"{dir}/Textures"))
                    continue;
                Mat("M_" + kit, "DeadCells/CharacterLit", m =>
                {
                    Textures(m, $"{dir}/Textures", kit);
                    m.SetColor("_EmissionColor", new Color(2.4f, 2.4f, 2.4f));
                    m.SetFloat("_EmissionPulseAmp", 0.25f);
                    m.SetFloat("_EmissionPulseSpeed", 3f);
                    m.SetFloat("_OutlinePixels", 0.75f);
                    m.SetFloat("_GlintThreshold", 0.35f);
                    m.SetFloat("_GlintIntensity", 1.6f);
                });
            }
        }

        static GameObject SanctumProp(string kit, string name)
        {
            string fbx = $"{PropsDir}/{kit}/{name}.fbx";
            if (!File.Exists(fbx))
                return null;
            var go = Instance(fbx);
            go.name = name;
            AssignAll(go, LoadMat("M_" + kit));
            return go;
        }

        /// <summary>Item prefabs for amulets and rune tablets (shown on pedestals and as pickups).</summary>
        static void BuildRelicVisuals()
        {
            if (!SanctumReady)
                return;
            foreach (var name in new[] { "AmuletEmber", "AmuletTide", "AmuletBone", "AmuletStar", "RuneVine", "RuneRam", "RuneSpider" })
            {
                var go = SanctumProp("Relics", name);
                if (go == null)
                    continue;
                // Pendants are hand-sized; on a pedestal they need to read at gameplay distance.
                go.transform.localScale = Vector3.one * (name.StartsWith("Amulet") ? 2.2f : 1.4f);
                var root = new GameObject(name);
                go.transform.SetParent(root.transform, false);
                go.name = "Model";
                Save(root, "Items/" + name);
            }
        }

        static void BuildSanctumWorld(WorldPrefabs wp)
        {
            if (!SanctumReady)
            {
                Debug.LogWarning("[DC] Sanctum/Relics kits not exported yet: skipping the 0.6 props");
                return;
            }
            GameObject Npc(string name, NpcInteractable.Role role, Vector3 light, Color color)
            {
                var vis = SanctumProp("Sanctum", name);
                var root = Wrap(name, vis);
                vis.name = "Visual";
                var n = root.AddComponent<NpcInteractable>();
                n.role = role;
                n.range = 2.2f;
                PointLight(root.transform, light, color, 2.2f, 4.5f, "Lamp");
                return Save(root, "World/" + name);
            }
            wp.mutator = Npc("Mutator", NpcInteractable.Role.Mutator, new Vector3(0f, 1.3f, 0.2f), new Color(0.55f, 1f, 0.4f));
            wp.blacksmith = Npc("Blacksmith", NpcInteractable.Role.Blacksmith, new Vector3(0.95f, 1f, -0.4f), new Color(1f, 0.55f, 0.2f));
            wp.tailor = Npc("Tailor", NpcInteractable.Role.Tailor, new Vector3(-0.3f, 1.8f, -0.6f), new Color(0.75f, 0.55f, 1f));

            // Timed vault: the leaves swing on their hinges, the clock hand counts down.
            var tdVis = SanctumProp("Sanctum", "TimedDoor");
            var td = Wrap("TimedDoor", tdVis);
            tdVis.name = "Visual";
            var tdc = td.AddComponent<TimedDoor>();
            tdc.leafLeft = Find(tdVis.transform, "TimedDoor_Left");
            tdc.leafRight = Find(tdVis.transform, "TimedDoor_Right");
            tdc.hand = Find(tdVis.transform, "TimedDoor_Hand");
            tdc.glow = PointLight(td.transform, new Vector3(0f, 2.8f, -0.8f), new Color(1f, 0.82f, 0.45f), 2f, 5f, "ClockGlow");
            tdc.range = 2.2f;
            wp.timedDoor = Save(td, "World/TimedDoor");

            // Curse overlay dropped over a normal chest.
            var shVis = SanctumProp("Sanctum", "CurseShroud");
            var sh = Wrap("CurseShroud", shVis);
            shVis.name = "Visual";
            PointLight(sh.transform, new Vector3(0f, 0.6f, -0.7f), new Color(0.75f, 0.4f, 1f), 2.4f, 3.5f, "CurseGlow");
            wp.curseShroud = Save(sh, "World/CurseShroud");

            // Secret blocks: one tile, solid, breakable.
            GameObject Block(string name, bool ram)
            {
                var vis = SanctumProp("Relics", name);
                var root = Wrap(name, vis);
                vis.name = "Visual";
                root.layer = DCLayers.Ground;
                var col = root.AddComponent<BoxCollider2D>();
                col.size = new Vector2(1f, 1f);
                col.offset = new Vector2(0f, 0.5f);
                var b = root.AddComponent<Breakable>();
                b.ram = ram;
                b.hits = ram ? 1 : 2;
                return Save(root, "World/" + name);
            }
            wp.crackedBlock = Block("CrackedBlock", false);
            wp.ramSlab = Block("RamSlab", true);

            // Vine bulb (models for the stalk / leaves are kept inactive inside the prefab).
            var bulbVis = SanctumProp("Relics", "VineBulb");
            var bulb = Wrap("VineBulb", bulbVis);
            bulbVis.name = "Visual";
            var vb = bulb.AddComponent<VineBulb>();
            vb.range = 1.8f;
            var stalk = SanctumProp("Relics", "VineStalk");
            stalk.transform.SetParent(bulb.transform, false);
            stalk.SetActive(false);
            vb.stalkModel = stalk;
            var leaf = SanctumProp("Relics", "VineLeaf");
            leaf.transform.SetParent(bulb.transform, false);
            leaf.SetActive(false);
            vb.leafModel = leaf;
            PointLight(bulb.transform, new Vector3(0f, 0.8f, -0.6f), new Color(0.6f, 1f, 0.4f), 1.6f, 3f, "Glow");
            wp.vineBulb = Save(bulb, "World/VineBulb");

            // Branch door: the exit door in a cooler light, a rune tablet over it (added at spawn).
            var vdVis = Prop("ExitDoor", "Visual");
            var vd = Wrap("VariantDoor", vdVis);
            var ved = vd.AddComponent<ExitDoor>();
            ved.leaf = Find(vdVis.transform, "Door_Left");
            ved.leafRight = Find(vdVis.transform, "Door_Right");
            ved.variant = true;
            var vdl = Find(vdVis.transform, "ExitDoor_Light");
            if (vdl != null)
                foreach (var r in vdl.GetComponentsInChildren<Renderer>())
                {
                    r.sharedMaterial = LoadMat("M_FX_Crystal");
                    r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                }
            PointLight(vd.transform, new Vector3(0f, 1.8f, -0.4f), new Color(0.55f, 1f, 0.75f), 2.2f, 5f, "DoorLight");
            ved.range = 2.2f;
            wp.variantDoor = Save(vd, "World/VariantDoor");

            // Rune tablets: pickups dropped by guardians, plus bare models for the branch doors.
            GameObject RunePrefab(string name)
            {
                var root = new GameObject(name + "Pickup");
                var display = new GameObject("Display").transform;
                display.SetParent(root.transform, false);
                PrefabUtility.InstantiatePrefab(ItemPrefab(name), display);
                var rp = root.AddComponent<RunePickup>();
                rp.display = display;
                rp.range = 1.8f;
                PointLight(root.transform, new Vector3(0f, 1.2f, -0.6f), name == "RuneVine" ? new Color(0.6f, 1f, 0.4f)
                    : name == "RuneRam" ? new Color(1f, 0.6f, 0.3f) : new Color(0.75f, 0.5f, 1f), 2.4f, 3.5f, "Glow");
                return Save(root, "World/" + name + "Pickup");
            }
            wp.runeVine = RunePrefab("RuneVine");
            wp.runeRam = RunePrefab("RuneRam");
            wp.runeSpider = RunePrefab("RuneSpider");
            wp.runeModelVine = ItemPrefab("RuneVine");
            wp.runeModelRam = ItemPrefab("RuneRam");
            wp.runeModelSpider = ItemPrefab("RuneSpider");
            EditorUtility.SetDirty(wp);
        }

        static void BuildSanctumItems(List<ItemDef> list)
        {
            if (SanctumReady)
            {
                foreach (var (id, visual, price) in new[]
                         {
                             ("amulet_ember", "AmuletEmber", 160), ("amulet_tide", "AmuletTide", 160),
                             ("amulet_bone", "AmuletBone", 160), ("amulet_star", "AmuletStar", 200),
                         })
                {
                    var a = Item(id, ItemKind.Amulet, visual, MountPoint.Weapon, 0, price, 1, CritRule.None, 1f);
                    a.colors = ItemColor.None;
                    a.icon = AssetDatabase.LoadAssetAtPath<Sprite>($"{ArtDir}/Icons/{visual}.png");
                    list.Add(a);
                }
            }

            // Colours: melee red, ranged / skills purple, shields green; hybrids carry two.
            var colors = new Dictionary<string, ItemColor>
            {
                ["melee_broadsword"] = ItemColor.Brutality | ItemColor.Survival,
                ["melee_daggers"] = ItemColor.Brutality | ItemColor.Tactics,
                ["melee_flail"] = ItemColor.Brutality | ItemColor.Survival,
                ["melee_spear"] = ItemColor.Brutality | ItemColor.Tactics,
                ["melee_rapier"] = ItemColor.Brutality | ItemColor.Tactics,
                ["melee_baton"] = ItemColor.Brutality | ItemColor.Survival,
                ["melee_bellmaul"] = ItemColor.Brutality | ItemColor.Survival,
                ["melee_shovel"] = ItemColor.Brutality | ItemColor.Survival,
                ["melee_oar"] = ItemColor.Brutality | ItemColor.Survival,
                ["melee_wardenkey"] = ItemColor.Brutality | ItemColor.Survival,
                ["melee_moonsickle"] = ItemColor.Brutality | ItemColor.Tactics,
                ["melee_leviathanrib"] = ItemColor.Brutality | ItemColor.Survival,
                ["melee_pendulumaxe"] = ItemColor.Brutality | ItemColor.Survival,
                ["melee_lavenderbottle"] = ItemColor.Brutality | ItemColor.Tactics,
                ["melee_anchor"] = ItemColor.Brutality | ItemColor.Survival,
                ["melee_moonsilkwhip"] = ItemColor.Brutality | ItemColor.Tactics,
                ["melee_gearsaw"] = ItemColor.Brutality | ItemColor.Tactics,
                ["melee_clockhand"] = ItemColor.Brutality | ItemColor.Tactics,
                ["melee_eelwhip"] = ItemColor.Brutality | ItemColor.Tactics,
                ["melee_scepter"] = ItemColor.Brutality | ItemColor.Survival,
                ["melee_crook"] = ItemColor.Brutality | ItemColor.Survival,
                ["bow_blunderbuss"] = ItemColor.Brutality | ItemColor.Tactics,
                ["bow_harpoongun"] = ItemColor.Brutality | ItemColor.Tactics,
                ["bow_knifefan"] = ItemColor.Brutality | ItemColor.Tactics,
                ["skill_fire_grenade"] = ItemColor.Brutality | ItemColor.Tactics,
                ["skill_ice_grenade"] = ItemColor.Tactics | ItemColor.Survival,
                ["skill_frostnova"] = ItemColor.Tactics | ItemColor.Survival,
                ["skill_mendinglantern"] = ItemColor.Survival,
                ["skill_ragevial"] = ItemColor.Brutality,
                ["skill_emberdash"] = ItemColor.Brutality | ItemColor.Survival,
                ["skill_stopwatch"] = ItemColor.Tactics | ItemColor.Survival,
                ["skill_starfall"] = ItemColor.Brutality | ItemColor.Tactics,
                ["skill_sawdisc"] = ItemColor.Brutality | ItemColor.Tactics,
                ["skill_clusterbell"] = ItemColor.Brutality | ItemColor.Tactics,
                ["shield_spikedshell"] = ItemColor.Survival | ItemColor.Brutality,
                ["shield_embertarge"] = ItemColor.Survival | ItemColor.Brutality,
                ["shield_clockface"] = ItemColor.Survival | ItemColor.Tactics,
                ["shield_mirrormoon"] = ItemColor.Survival | ItemColor.Tactics,
            };
            foreach (var d in list)
            {
                if (d.kind == ItemKind.Amulet)
                    continue;
                d.colors = colors.TryGetValue(d.id, out var c) ? c : d.kind switch
                {
                    ItemKind.Melee => ItemColor.Brutality,
                    ItemKind.Shield => ItemColor.Survival,
                    _ => ItemColor.Tactics,
                };
            }

            // The new statuses on the weapons that suit them.
            foreach (var d in list)
            {
                switch (d.id)
                {
                    case "melee_gearsaw":
                    case "melee_sawshark":
                        Effect(d, SkillEffect.Bleed, 4f, 0.5f);
                        break;
                    case "bow_inksquirter":
                        Effect(d, SkillEffect.Oil, 8f);
                        break;
                    case "skill_beartrap":
                        Effect(d, SkillEffect.Root, 2.5f);
                        break;
                }
            }
        }
    }
}
