using System.Collections.Generic;
using System.IO;
using DeadCells.Core;
using DeadCells.Items;
using UnityEditor;
using UnityEngine;

namespace DeadCells.EditorTools
{
    /// <summary>
    /// The 60-weapon expansion: item visuals from the three Armory2 kits
    /// (Tools/Blender/armory_*.py), their projectiles and item definitions.
    /// </summary>
    public static partial class DCContentBuilder
    {
        const string Armory2Dir = ArtDir + "/Weapons/Armory2";
        static readonly string[] Armory2Kits = { "ArmoryMelee", "ArmoryRanged", "ArmoryGear" };

        static string KitOf(string visual)
        {
            foreach (var kit in Armory2Kits)
                if (File.Exists($"{Armory2Dir}/{kit}/{visual}.fbx"))
                    return kit;
            return null;
        }

        static void BuildArmoryMaterials()
        {
            foreach (var kit in Armory2Kits)
            {
                Mat("M_" + kit, "DeadCells/CharacterLit", m =>
                {
                    Textures(m, $"{Armory2Dir}/{kit}/Textures", kit);
                    // The emission map is baked in colour: a neutral HDR white keeps each glow's hue.
                    m.SetColor("_EmissionColor", new Color(2.4f, 2.4f, 2.4f));
                    m.SetFloat("_EmissionPulseAmp", 0.3f);
                    m.SetFloat("_EmissionPulseSpeed", 5f);
                    m.SetFloat("_OutlinePixels", 0.75f);
                    m.SetFloat("_GlintThreshold", 0.35f);
                    m.SetFloat("_GlintIntensity", 2.2f);
                });
            }
            Unlit("M_FX_Fire", new Color(4f, 1.8f, 0.5f), 0.2f, 10f);
            Unlit("M_FX_Moon", new Color(3.2f, 3.4f, 3.8f), 0.2f, 8f);
            Unlit("M_FX_Ink", new Color(1.4f, 0.5f, 2.6f), 0.25f, 6f);
            Unlit("M_FX_Stone", new Color(0.7f, 0.68f, 0.64f), 0.1f, 2f);
        }

        /// <summary>Item prefabs; the slash trail runs from 30% to 92% of the vertex farthest from the grip.</summary>
        static void BuildArmoryVisuals()
        {
            foreach (var kit in Armory2Kits)
            {
                var mat = LoadMat("M_" + kit);
                foreach (var fbx in Directory.GetFiles($"{Armory2Dir}/{kit}", "*.fbx"))
                {
                    string name = Path.GetFileNameWithoutExtension(fbx);
                    var go = Instance(fbx.Replace('\\', '/'));
                    go.name = name;
                    AssignAll(go, mat);
                    if (kit == "ArmoryMelee")
                    {
                        Vector3 far = Vector3.zero;
                        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
                            foreach (var v in mf.sharedMesh.vertices)
                            {
                                var p = go.transform.InverseTransformPoint(mf.transform.TransformPoint(v));
                                if (p.y > 0f && p.sqrMagnitude > far.sqrMagnitude)
                                    far = p;
                            }
                        var b = new GameObject("BladeBase").transform;
                        b.SetParent(go.transform, false);
                        b.localPosition = new Vector3(far.x * 0.3f, far.y * 0.3f, 0f);
                        var t = new GameObject("BladeTip").transform;
                        t.SetParent(go.transform, false);
                        t.localPosition = new Vector3(far.x * 0.92f, far.y * 0.92f, 0f);
                    }
                    Save(go, "Items/" + name);
                }
            }
        }

        static void BuildArmoryProjectiles()
        {
            var sphere = Resources.GetBuiltinResource<Mesh>("Sphere.fbx");
            void Shape(string name, Mesh mesh, string mat, Vector3 scale, Color light, Color trail, float radius, float trailWidth = 0.08f)
            {
                var root = ProjectileRoot(name, radius);
                MeshObject("Shape", mesh, LoadMat(mat), root.transform, scale);
                if (light.maxColorComponent > 0f)
                    PointLight(root.transform, Vector3.zero, light, 1.8f, 2.6f);
                if (trail.maxColorComponent > 0f)
                    Trail(root, trail, trailWidth, 0.16f);
                SaveProjectile(root, name);
            }
            Shape("P_Pellet", sphere, "M_FX_Fire", Vector3.one * 0.13f, Color.clear, new Color(3f, 1.4f, 0.4f), 0.16f, 0.05f);
            Shape("P_Dart", Octahedron(), "M_FX_OrbGreen", new Vector3(0.18f, 0.9f, 0.18f), Color.clear, new Color(0.9f, 3f, 0.6f), 0.18f, 0.04f);
            Shape("P_IceOrb", sphere, "M_FX_Crystal", Vector3.one * 0.3f, new Color(0.5f, 0.8f, 1f), new Color(1f, 2f, 3.4f), 0.25f, 0.12f);
            Shape("P_Spark", sphere, "M_FX_Crystal", Vector3.one * 0.2f, new Color(0.5f, 0.7f, 1f), new Color(1.4f, 2.2f, 3.4f), 0.2f);
            Shape("P_Ink", sphere, "M_FX_Ink", Vector3.one * 0.26f, Color.clear, new Color(1.4f, 0.5f, 2.6f), 0.24f, 0.1f);
            Shape("P_Note", sphere, "M_FX_Ring", Vector3.one * 0.2f, new Color(0.7f, 0.4f, 1f), new Color(2.4f, 1.1f, 3.6f), 0.22f, 0.07f);
            Shape("P_StarShard", Octahedron(), "M_FX_Star", Vector3.one * 0.85f, new Color(1f, 0.9f, 0.6f), new Color(3.4f, 3f, 1.8f), 0.24f);
            Shape("P_Nail", Octahedron(), "M_FX_Moon", new Vector3(0.12f, 0.75f, 0.12f), Color.clear, new Color(2f, 2f, 2.2f), 0.14f, 0.03f);
            Shape("P_Shell", sphere, "M_FX_Fire", Vector3.one * 0.3f, new Color(1f, 0.55f, 0.2f), new Color(3.4f, 1.4f, 0.3f), 0.3f, 0.14f);
            Shape("P_Bubble", sphere, "M_FX_Crystal", Vector3.one * 0.5f, new Color(0.5f, 0.8f, 1f), Color.clear, 0.4f);
            Shape("P_Pebble", sphere, "M_FX_Stone", Vector3.one * 0.14f, Color.clear, new Color(1f, 1f, 1f), 0.15f, 0.03f);
            Shape("P_Lance", Octahedron(), "M_FX_Star", new Vector3(0.35f, 2.2f, 0.35f), new Color(1f, 0.8f, 0.4f), new Color(3.4f, 2.6f, 1.2f), 0.24f, 0.1f);
            Shape("P_Slug", Octahedron(), "M_FX_Moon", new Vector3(0.16f, 0.8f, 0.16f), Color.clear, new Color(2.6f, 2.8f, 3.2f), 0.14f, 0.04f);

            var wave = ProjectileRoot("P_Wave", 0.6f);
            MeshObject("Ring", Torus(), LoadMat("M_FX_Star"), wave.transform, Vector3.one * 1.4f);
            PointLight(wave.transform, Vector3.zero, new Color(1f, 0.85f, 0.4f), 2f, 3.5f);
            SaveProjectile(wave, "P_Wave");

            foreach (var (name, trail) in new[] { ("P_MoonArrow", new Color(3f, 3.2f, 3.6f)), ("P_IceArrow", new Color(1f, 2.2f, 3.4f)) })
            {
                var a = ProjectileRoot(name, 0.22f);
                PrefabUtility.InstantiatePrefab(ItemPrefab("Arrow"), a.transform);
                Trail(a, trail, 0.07f, 0.16f);
                SaveProjectile(a, name);
            }
            var knife = ProjectileRoot("P_Knife", 0.2f);
            var kv = (GameObject)PrefabUtility.InstantiatePrefab(ItemPrefab("Dagger"), knife.transform);
            kv.transform.localScale = Vector3.one * 0.85f;
            Trail(knife, new Color(3f, 0.8f, 0.9f), 0.05f, 0.12f);
            SaveProjectile(knife, "P_Knife");

            // Thrown skills fly as their own model; discs turn to face the camera.
            foreach (var (name, visual, color, faceCamera) in new[]
                     {
                         ("P_Chakram", "MoonChakram", new Color(3f, 3.2f, 3.6f), true),
                         ("P_Sawdisc", "BouncingSawdisc", new Color(2.6f, 2.6f, 2.8f), false),
                         ("P_Miasma", "MiasmaJar", new Color(0.9f, 3f, 0.6f), false),
                         ("P_ClusterBell", "ClusterBellBomb", new Color(3.2f, 2.4f, 1f), false),
                         ("P_Lodestone", "LodestoneMine", new Color(1.6f, 1.6f, 3.2f), false),
                         ("P_Inkwell", "AbyssInkwell", new Color(1.6f, 0.6f, 3.2f), false),
                     })
            {
                if (ItemPrefab(visual) == null)
                    continue; // kit not exported yet
                var p = ProjectileRoot(name, 0.32f);
                var v = (GameObject)PrefabUtility.InstantiatePrefab(ItemPrefab(visual), p.transform);
                if (faceCamera)
                    v.transform.localRotation = Quaternion.Euler(0f, 90f, 0f);
                PointLight(p.transform, Vector3.zero, color / 3.4f, 1.5f, 2.5f);
                Trail(p, color, 0.1f, 0.16f);
                SaveProjectile(p, name);
            }
        }

        // ------------------------------------------------------------ items

        static ItemDef Melee(string id, string visual, int unlock, int price, int tier, CritRule crit, float critMult, float speed,
            Color arc, string swing, string hit, params AttackStep[] combo)
        {
            var d = Item(id, ItemKind.Melee, visual, MountPoint.Weapon, unlock, price, tier, crit, critMult);
            d.animSpeed = speed;
            d.arcColor = arc;
            d.arcCore = Color.Lerp(arc, new Color(6.5f, 6.5f, 6.5f), 0.6f);
            d.sparkColor = arc * 0.9f;
            d.swingSound = swing;
            d.hitSound = hit;
            d.combo = combo;
            ResetExtras(d);
            return d;
        }

        static void ResetExtras(ItemDef d)
        {
            d.onHitChance = 0f;
            d.hasEffect = false;
            d.lifesteal = 0f;
            d.pull = 0f;
            d.comboRamp = 0f;
            d.eliteBonus = 1f;
            d.finisherWave = null;
            d.projectileCount = 1;
            d.spread = 0f;
            d.burst = 1;
            d.homing = 0f;
            d.bounces = 0;
            d.boomerang = false;
            d.chain = 0;
            d.pullOnHit = 0f;
            d.knockbackScale = 1f;
            d.projectileScale = 1f;
            d.projectileLifetime = 3f;
            d.parryRadius = 0f;
            d.parryApplies = false;
            d.thorns = 0f;
            d.reflectMultiplier = 1.5f;
            d.burstKind = BurstKind.None;
            d.radius = 0f;
            d.pierce = false;
            d.spin = false;
            d.projectileGravity = 0f;
            d.launchAngle = 0f;
            d.dualWield = false;
            d.offhandVisual = null;
        }

        static void Effect(ItemDef d, SkillEffect e, float duration, float chance = 1f)
        {
            d.hasEffect = true;
            d.effect = e;
            d.effectDuration = duration;
            d.onHitChance = chance;
        }

        static ItemDef Ranged(string id, string visual, int unlock, int price, int tier, string projectile, float speed, float damage,
            float cooldown, Color color, string fire, CritRule crit = CritRule.None, float critMult = 1.5f)
        {
            var d = Item(id, ItemKind.Bow, visual, MountPoint.Bow, unlock, price, tier, crit, critMult);
            ResetExtras(d);
            d.projectile = ProjectilePrefab(projectile);
            d.projectileSpeed = speed;
            d.damage = damage;
            d.cooldown = cooldown;
            d.effectColor = color;
            d.fireSound = fire;
            return d;
        }

        static ItemDef Shield(string id, string visual, int unlock, int price, int tier, float window, float block, float parryDamage, Color spark)
        {
            var d = Item(id, ItemKind.Shield, visual, MountPoint.Shield, unlock, price, tier, CritRule.None, 1.5f);
            ResetExtras(d);
            d.parryWindow = window;
            d.blockReduction = block;
            d.parryDamage = parryDamage;
            d.sparkColor = spark;
            return d;
        }

        static ItemDef Skill(string id, string visual, int unlock, int price, int tier, SkillKind kind, float damage, float cooldown, Color color,
            string fire, string projectile = null)
        {
            var d = Item(id, ItemKind.Skill, visual, MountPoint.Weapon, unlock, price, tier, CritRule.None, 1.5f);
            ResetExtras(d);
            d.skillKind = kind;
            d.damage = damage;
            d.cooldown = cooldown;
            d.effectColor = color;
            d.fireSound = fire;
            d.projectile = projectile != null ? ProjectilePrefab(projectile) : null;
            d.projectileSpeed = 15f;
            return d;
        }

        static AttackStep S(string clip, float dmg, float reach = 1.2f, float width = 2.3f, float height = 1.9f, float knock = 4.5f,
            float stun = 0.15f, bool fin = false)
        {
            bool thrust = clip.StartsWith("Spear");
            int total = thrust ? (fin ? 22 : 16) : (fin ? 24 : 18);
            int a0 = fin ? 5 : 4, a1 = fin ? 9 : 7;
            return Step(clip, total, a0, a1, fin ? 13 : 8, 3, 6, thrust ? 6f : 4.5f, dmg,
                new Vector2(reach, thrust ? 1.15f : 1.05f), new Vector2(width, thrust ? Mathf.Min(height, 1f) : height),
                fin ? knock * 2f : knock, fin ? stun + 0.25f : stun, fin ? 1f : 0.35f, fin ? 0.45f : 0.18f, fin);
        }

        static void BuildArmoryItems(List<ItemDef> list)
        {
            if (KitOf("EmberFang") == null)
            {
                Debug.LogWarning("[DC] Armory2 kits not exported yet: skipping the 60-weapon expansion");
                return;
            }
            Color fire = new Color(3.4f, 1.4f, 0.3f), ice = new Color(0.9f, 2.2f, 3.4f), bolt = new Color(1.4f, 2.2f, 3.4f),
                poison = new Color(0.9f, 3f, 0.6f), moon = new Color(2.8f, 3f, 3.4f), violet = new Color(2.2f, 0.9f, 3.4f),
                gold = new Color(3.4f, 2.6f, 0.9f), red = new Color(3.4f, 0.6f, 0.7f), steel = new Color(2.4f, 2.6f, 2.8f);

            // ------------------------------------------------------------ melee
            var m = Melee("melee_emberfang", "EmberFang", 0, 150, 1, CritRule.Burning, 2.2f, 1.35f, fire, "swing.light", "hit.flesh",
                S("Slash_Combo_1", 9), S("Slash_Combo_2", 9), S("Spear_Thrust_1", 16, 1.4f, 2.6f, fin: true));
            Effect(m, SkillEffect.Fire, 3f, 0.35f);
            list.Add(m);
            m = Melee("melee_moonsickle", "Moonsickle", 30, 170, 2, CritRule.Behind, 2.4f, 1.4f, moon, "swing.light", "hit.flesh",
                S("Slash_Combo_1", 8, width: 2.1f), S("Slash_Combo_2", 8, width: 2.1f), S("Slash_Combo_3", 15, fin: true));
            m.dualWield = true;
            list.Add(m);
            m = Melee("melee_leviathanrib", "LeviathanRib", 60, 230, 3, CritRule.Finisher, 1.8f, 0.6f, steel, "swing.heavy", "hit.heavy",
                S("Slash_Combo_1", 36, 1.6f, 3.4f, 2.6f, 8f, 0.5f), S("Slash_Combo_3", 54, 1.7f, 3.6f, 2.8f, 7f, 0.4f, true));
            m.finisherWave = ProjectilePrefab("P_Wave");
            m.finisherWaveDamage = 22f;
            list.Add(m);
            m = Melee("melee_pendulumaxe", "PendulumAxe", 40, 200, 2, CritRule.Disabled, 2f, 0.75f, gold, "swing.heavy", "hit.heavy",
                S("Slash_Combo_1", 24, 1.4f, 2.8f, 2.4f, 6f, 0.6f), S("Slash_Combo_2", 24, 1.4f, 2.8f, 2.4f, 6f, 0.6f),
                S("Slash_Combo_3", 38, 1.5f, 3f, 2.4f, 6f, 0.5f, true));
            list.Add(m);
            m = Melee("melee_lavenderbottle", "LavenderBottle", 0, 140, 1, CritRule.Afflicted, 1.8f, 0.95f, violet, "swing.heavy", "hit.flesh",
                S("Slash_Combo_1", 13), S("Slash_Combo_2", 13), S("Slash_Combo_3", 22, fin: true));
            Effect(m, SkillEffect.Poison, 5f);
            list.Add(m);
            m = Melee("melee_anchor", "DrownedAnchor", 50, 210, 2, CritRule.Finisher, 2f, 0.62f, steel, "swing.heavy", "hit.heavy",
                S("Slash_Combo_1", 30, 1.5f, 3f, 2.4f, 7f, 0.5f), S("Slash_Combo_3", 44, 1.6f, 3.2f, 2.6f, 6f, 0.4f, true));
            m.pull = 9f;
            list.Add(m);
            m = Melee("melee_moonsilkwhip", "MoonsilkWhip", 35, 180, 2, CritRule.Afflicted, 1.7f, 1.1f, moon, "swing.flail", "hit.flesh",
                S("Spear_Thrust_1", 11, 2.6f, 4.6f), S("Spear_Thrust_2", 11, 2.6f, 4.6f), S("Spear_Thrust_3", 18, 2.8f, 5f, fin: true));
            Effect(m, SkillEffect.Slow, 2f, 0.5f);
            list.Add(m);
            m = Melee("melee_gearsaw", "Gearsaw", 45, 190, 2, CritRule.Afflicted, 1.8f, 1.5f, gold, "swing.light", "hit.flesh",
                S("Slash_Combo_1", 7), S("Slash_Combo_2", 7), S("Slash_Combo_1", 7), S("Slash_Combo_3", 14, fin: true));
            Effect(m, SkillEffect.Poison, 4f, 0.3f);
            list.Add(m);
            m = Melee("melee_candelabra", "CandelabraTrident", 30, 180, 2, CritRule.Burning, 2f, 1f, fire, "swing.thrust", "hit.flesh",
                S("Spear_Thrust_1", 13, 1.9f, 3.4f), S("Spear_Thrust_2", 14, 1.9f, 3.4f), S("Spear_Thrust_3", 24, 2.1f, 3.8f, fin: true));
            Effect(m, SkillEffect.Fire, 3f, 0.5f);
            list.Add(m);
            m = Melee("melee_clockhand", "ClockhandLance", 55, 220, 3, CritRule.Finisher, 2.2f, 0.9f, ice, "swing.thrust", "hit.flesh",
                S("Spear_Thrust_1", 16, 2.4f, 4.8f), S("Spear_Thrust_2", 16, 2.4f, 4.8f), S("Spear_Thrust_3", 30, 2.6f, 5.2f, fin: true));
            Effect(m, SkillEffect.Slow, 2f, 0.3f);
            list.Add(m);
            m = Melee("melee_eelwhip", "Eelwhip", 40, 190, 2, CritRule.Disabled, 2f, 1.05f, bolt, "swing.flail", "hit.flesh",
                S("Spear_Thrust_1", 12, 2.5f, 4.4f), S("Spear_Thrust_2", 12, 2.5f, 4.4f), S("Spear_Thrust_3", 20, 2.7f, 4.8f, fin: true));
            Effect(m, SkillEffect.Lightning, 0.5f, 0.5f);
            list.Add(m);
            m = Melee("melee_scepter", "OssuaryScepter", 45, 200, 2, CritRule.Finisher, 1.6f, 0.9f, red, "swing.heavy", "hit.heavy",
                S("Slash_Combo_1", 18, 1.3f, 2.5f, 2f, 5f, 0.3f), S("Slash_Combo_2", 18), S("Slash_Combo_3", 30, fin: true));
            m.lifesteal = 0.12f;
            list.Add(m);
            m = Melee("melee_tongs", "FurnaceTongs", 25, 170, 1, CritRule.Burning, 2.3f, 1f, fire, "swing.light", "hit.heavy",
                S("Slash_Combo_1", 12), S("Slash_Combo_2", 12), S("Slash_Combo_3", 22, fin: true));
            Effect(m, SkillEffect.Fire, 4f, 0.6f);
            list.Add(m);
            m = Melee("melee_crook", "MoonherdCrook", 0, 160, 1, CritRule.Finisher, 1.8f, 1f, moon, "swing.heavy", "hit.flesh",
                S("Slash_Combo_1", 14, 1.6f, 3f), S("Slash_Combo_2", 14, 1.6f, 3f), S("Slash_Combo_3", 24, 1.8f, 3.2f, fin: true));
            m.pull = 8f;
            Effect(m, SkillEffect.Slow, 1.5f, 0.25f);
            list.Add(m);
            m = Melee("melee_katana", "StarsandKatana", 50, 210, 3, CritRule.Airborne, 2.5f, 1.2f, moon, "swing.light", "hit.flesh",
                S("Slash_Combo_1", 13, 1.3f, 2.6f), S("Slash_Combo_2", 13, 1.3f, 2.6f), S("Slash_Combo_3", 22, 1.4f, 2.8f, fin: true));
            list.Add(m);
            m = Melee("melee_sawshark", "SawsharkBlade", 35, 190, 2, CritRule.Afflicted, 1.9f, 1f, steel, "swing.light", "hit.flesh",
                S("Slash_Combo_1", 13, 1.4f, 2.6f), S("Slash_Combo_2", 13, 1.4f, 2.6f), S("Slash_Combo_3", 24, 1.5f, 2.8f, fin: true));
            Effect(m, SkillEffect.Poison, 4f, 0.45f);
            list.Add(m);
            m = Melee("melee_wardenkey", "WardensKey", 45, 200, 2, CritRule.Finisher, 1.7f, 0.95f, gold, "swing.heavy", "hit.heavy",
                S("Slash_Combo_1", 16, 1.4f, 2.6f), S("Slash_Combo_2", 16, 1.4f, 2.6f), S("Slash_Combo_3", 28, fin: true));
            m.eliteBonus = 1.6f;
            list.Add(m);
            m = Melee("melee_oar", "FerrymansOar", 30, 180, 2, CritRule.Finisher, 1.8f, 0.8f, violet, "swing.heavy", "hit.heavy",
                S("Slash_Combo_2", 18, 1.7f, 3.6f, 2.8f, 9f, 0.3f), S("Slash_Combo_3", 26, 1.8f, 3.8f, 2.8f, 8f, 0.3f, true));
            list.Add(m);
            m = Melee("melee_baton", "MaestrosBaton", 40, 170, 2, CritRule.None, 1.5f, 1.8f, gold, "swing.thrust", "hit.flesh",
                S("Spear_Thrust_1", 5, 1.5f, 2.6f), S("Spear_Thrust_2", 5, 1.5f, 2.6f), S("Spear_Thrust_1", 5, 1.5f, 2.6f),
                S("Spear_Thrust_3", 8, 1.6f, 2.8f, fin: true));
            m.comboRamp = 0.06f;
            list.Add(m);
            m = Melee("melee_knuckles", "EmberKnuckles", 35, 180, 2, CritRule.Finisher, 2f, 1.6f, fire, "swing.thrust", "hit.heavy",
                S("Slash_Combo_1", 7, 1f, 2f), S("Slash_Combo_2", 7, 1f, 2f), S("Slash_Combo_1", 7, 1f, 2f), S("Spear_Thrust_3", 16, 1.3f, 2.2f, fin: true));
            m.dualWield = true;
            Effect(m, SkillEffect.Fire, 3f, 0.2f);
            list.Add(m);

            // ----------------------------------------------------------- ranged
            var r = Ranged("bow_crescent", "CrescentLongbow", 35, 190, 2, "P_MoonArrow", 36f, 20f, 0.7f, moon, "bow.shoot", CritRule.LongRange, 1.8f);
            r.pierce = true;
            list.Add(r);
            r = Ranged("bow_repeater", "TripleRepeater", 0, 160, 1, "P_Arrow", 32f, 9f, 0.75f, steel, "crossbow.shoot");
            r.burst = 3;
            list.Add(r);
            r = Ranged("bow_blunderbuss", "Blunderbuss", 40, 200, 2, "P_Pellet", 30f, 7f, 1f, fire, "explode.fire");
            r.projectileCount = 6;
            r.spread = 6f;
            r.projectileLifetime = 0.33f;
            r.knockbackScale = 2f;
            list.Add(r);
            r = Ranged("bow_blowpipe", "TickBlowpipe", 0, 140, 1, "P_Dart", 34f, 5f, 0.35f, poison, "swing.thrust", CritRule.Afflicted, 2f);
            Effect(r, SkillEffect.Poison, 4f);
            list.Add(r);
            r = Ranged("bow_frostsling", "Frostsling", 30, 170, 2, "P_IceOrb", 22f, 10f, 1.1f, ice, "grenade.throw");
            r.projectileGravity = 18f;
            r.launchAngle = 12f;
            r.radius = 1.4f;
            Effect(r, SkillEffect.Ice, 1.6f);
            list.Add(r);
            r = Ranged("bow_chakram", "MoonChakram", 45, 210, 2, "P_Chakram", 20f, 14f, 0.9f, moon, "swing.flail");
            r.boomerang = true;
            r.spin = true;
            list.Add(r);
            r = Ranged("bow_knifefan", "KnifeFan", 35, 180, 2, "P_Knife", 30f, 8f, 0.6f, red, "swing.light", CritRule.Behind, 2.2f);
            r.projectileCount = 3;
            r.spread = 9f;
            list.Add(r);
            r = Ranged("bow_harp", "ThunderstringHarp", 50, 220, 3, "P_Spark", 28f, 10f, 0.8f, bolt, "lightning.zap");
            r.chain = 3;
            Effect(r, SkillEffect.Lightning, 0.4f);
            list.Add(r);
            r = Ranged("bow_bellhorn", "BellHorn", 40, 200, 2, "P_Wave", 16f, 12f, 1.2f, gold, "hit.bell");
            r.pierce = true;
            r.knockbackScale = 3f;
            r.projectileScale = 1.2f;
            r.projectileLifetime = 0.9f;
            list.Add(r);
            r = Ranged("bow_inksquirter", "InkSquirter", 30, 170, 2, "P_Ink", 20f, 6f, 0.7f, violet, "vermin.explode");
            r.burst = 2;
            r.projectileGravity = 6f;
            Effect(r, SkillEffect.Slow, 3f);
            list.Add(r);
            r = Ranged("bow_boneflute", "BoneFlute", 45, 210, 3, "P_Note", 14f, 9f, 0.9f, violet, "turret.fire");
            r.projectileCount = 2;
            r.spread = 25f;
            r.homing = 260f;
            list.Add(r);
            r = Ranged("bow_starwand", "StardustWand", 40, 200, 2, "P_StarShard", 24f, 11f, 0.6f, gold, "tk.star");
            r.bounces = 3;
            list.Add(r);
            r = Ranged("bow_harpoongun", "HarpoonGun", 45, 210, 2, "P_Harpoon", 34f, 24f, 1.4f, bolt, "harpoon.throw");
            r.pierce = true;
            r.pullOnHit = 9f;
            list.Add(r);
            r = Ranged("bow_nailer", "SteamNailer", 40, 200, 2, "P_Nail", 38f, 4f, 0.12f, steel, "arrow.hit");
            list.Add(r);
            r = Ranged("bow_mortar", "EmberMortar", 55, 230, 3, "P_Shell", 17f, 28f, 1.6f, fire, "explode.fire");
            r.projectileGravity = 26f;
            r.launchAngle = 30f;
            r.radius = 2.4f;
            Effect(r, SkillEffect.Fire, 4f);
            list.Add(r);
            r = Ranged("bow_bubblegun", "BubbleGun", 35, 180, 2, "P_Bubble", 7f, 12f, 0.8f, ice, "enemy.orb");
            r.homing = 60f;
            r.radius = 1.6f;
            r.projectileLifetime = 4f;
            Effect(r, SkillEffect.Slow, 4f);
            list.Add(r);
            r = Ranged("bow_chronobow", "ChronoCrossbow", 50, 220, 3, "P_IceArrow", 34f, 12f, 0.9f, ice, "crossbow.shoot", CritRule.Disabled, 2f);
            Effect(r, SkillEffect.Ice, 1.2f);
            list.Add(r);
            r = Ranged("bow_slingshot", "GravelSlingshot", 0, 120, 1, "P_Pebble", 26f, 7f, 0.4f, steel, "grenade.throw");
            r.projectileGravity = 6f;
            r.bounces = 2;
            list.Add(r);
            r = Ranged("bow_lantern", "LanternBeam", 40, 200, 2, "P_Lance", 40f, 14f, 0.8f, gold, "turret.fire");
            r.pierce = true;
            Effect(r, SkillEffect.Fire, 3f);
            list.Add(r);
            r = Ranged("bow_sextant", "SextantSniper", 60, 240, 3, "P_Slug", 60f, 16f, 1.5f, moon, "crossbow.shoot", CritRule.LongRange, 3f);
            list.Add(r);

            // ---------------------------------------------------------- shields
            var sh = Shield("shield_bell", "BellShield", 40, 190, 2, 0.2f, 0.8f, 25f, gold);
            sh.parryRadius = 3.5f;
            list.Add(sh);
            sh = Shield("shield_mirrormoon", "MirrorMoon", 50, 210, 3, 0.22f, 0.9f, 20f, moon);
            sh.reflectMultiplier = 3f;
            list.Add(sh);
            sh = Shield("shield_spikedshell", "SpikedShell", 0, 160, 1, 0.18f, 0.75f, 30f, steel);
            sh.thorns = 18f;
            list.Add(sh);
            sh = Shield("shield_clockface", "ClockfaceBuckler", 45, 200, 2, 0.32f, 0.8f, 20f, ice);
            sh.parryApplies = true;
            Effect(sh, SkillEffect.Ice, 3f);
            list.Add(sh);
            sh = Shield("shield_embertarge", "EmberTarge", 40, 200, 2, 0.2f, 0.8f, 25f, fire);
            sh.parryApplies = true;
            sh.parryRadius = 2.5f;
            Effect(sh, SkillEffect.Fire, 5f);
            list.Add(sh);
            sh = Shield("shield_whalescale", "WhalescaleTower", 55, 220, 3, 0.16f, 0.95f, 35f, steel);
            list.Add(sh);

            // ----------------------------------------------------------- skills
            var k = Skill("skill_starfall", "Starfall", 50, 220, 3, SkillKind.Rain, 18f, 14f, gold, "tk.star", "P_StarShard");
            k.count = 6;
            k.radius = 1.2f;
            list.Add(k);
            k = Skill("skill_thundertotem", "ThunderTotem", 45, 210, 2, SkillKind.Deploy, 14f, 18f, bolt, "teleport.activate");
            k.deployKind = DeployKind.Totem;
            k.duration = 9f;
            k.interval = 0.9f;
            list.Add(k);
            k = Skill("skill_gearsentry", "GearSentry", 40, 200, 2, SkillKind.Deploy, 9f, 18f, gold, "teleport.activate", "P_Arrow");
            k.deployKind = DeployKind.Turret;
            k.duration = 10f;
            k.interval = 0.7f;
            k.projectileSpeed = 30f;
            list.Add(k);
            k = Skill("skill_beartrap", "BearTrap", 0, 130, 1, SkillKind.Deploy, 30f, 10f, red, "shield.block");
            k.deployKind = DeployKind.Trap;
            k.duration = 20f;
            Effect(k, SkillEffect.Slow, 3f);
            list.Add(k);
            k = Skill("skill_miasma", "MiasmaJar", 35, 180, 2, SkillKind.Throw, 8f, 14f, poison, "grenade.throw", "P_Miasma");
            k.projectileGravity = 30f;
            k.launchAngle = 32f;
            k.radius = 2.2f;
            k.burstKind = BurstKind.Cloud;
            k.duration = 5f;
            k.interval = 0.5f;
            k.spin = true;
            list.Add(k);
            k = Skill("skill_clusterbell", "ClusterBellBomb", 0, 150, 1, SkillKind.Throw, 24f, 12f, gold, "grenade.throw", "P_ClusterBell");
            k.projectileGravity = 30f;
            k.launchAngle = 32f;
            k.radius = 2f;
            k.burstKind = BurstKind.Cluster;
            k.count = 4;
            k.spin = true;
            list.Add(k);
            k = Skill("skill_lodestone", "LodestoneMine", 40, 200, 2, SkillKind.Throw, 26f, 13f, bolt, "grenade.throw", "P_Lodestone");
            k.projectileGravity = 30f;
            k.launchAngle = 32f;
            k.radius = 2.4f;
            k.burstKind = BurstKind.Vortex;
            k.duration = 1.4f;
            k.power = 14f;
            list.Add(k);
            k = Skill("skill_frostnova", "FrostNova", 40, 200, 2, SkillKind.Nova, 10f, 15f, ice, "explode.ice");
            k.radius = 4f;
            Effect(k, SkillEffect.Ice, 3f);
            list.Add(k);
            k = Skill("skill_emberdash", "EmberDash", 35, 190, 2, SkillKind.Dash, 20f, 8f, fire, "player.roll");
            k.power = 7f;
            Effect(k, SkillEffect.Fire, 4f);
            list.Add(k);
            k = Skill("skill_stopwatch", "Stopwatch", 60, 240, 3, SkillKind.Nova, 0f, 22f, violet, "tk.rewind");
            k.radius = 16f;
            k.power = 0f;
            Effect(k, SkillEffect.Slow, 5f);
            list.Add(k);
            k = Skill("skill_ragevial", "RageVial", 0, 150, 1, SkillKind.Buff, 0f, 25f, red, "player.drink");
            k.duration = 8f;
            k.power = 0.5f;
            list.Add(k);
            k = Skill("skill_mendinglantern", "MendingLantern", 50, 220, 3, SkillKind.Deploy, 0f, 30f, poison, "fountain.use");
            k.deployKind = DeployKind.Healer;
            k.duration = 8f;
            k.interval = 0.5f;
            k.power = 0.012f;
            k.radius = 3.5f;
            list.Add(k);
            k = Skill("skill_sawdisc", "BouncingSawdisc", 35, 180, 2, SkillKind.Throw, 14f, 9f, steel, "swing.flail", "P_Sawdisc");
            k.projectileSpeed = 22f;
            k.pierce = true;
            k.bounces = 4;
            k.spin = true;
            list.Add(k);
            k = Skill("skill_inkwell", "AbyssInkwell", 55, 230, 3, SkillKind.Throw, 30f, 18f, violet, "grenade.throw", "P_Inkwell");
            k.projectileGravity = 30f;
            k.launchAngle = 32f;
            k.radius = 3f;
            k.burstKind = BurstKind.Vortex;
            k.duration = 4f;
            k.power = 9f;
            list.Add(k);
        }
    }
}
