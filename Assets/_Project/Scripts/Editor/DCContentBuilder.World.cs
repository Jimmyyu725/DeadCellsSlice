using System.Collections.Generic;
using System.IO;
using System.Linq;
using DeadCells.Core;
using DeadCells.Enemies;
using DeadCells.Environment;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Run;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace DeadCells.EditorTools
{
    public static partial class DCContentBuilder
    {
        [System.Serializable]
        class ManifestModule
        {
            public string name;
            public string role;
            public string fbx;
            public string atlas;
            public int tris;
        }

        [System.Serializable]
        class Manifest
        {
            public ManifestModule[] modules;
        }

        static Manifest LoadManifest(string path)
        {
            if (!File.Exists(path))
            {
                Debug.LogError("[DC] missing manifest " + path);
                return new Manifest { modules = new ManifestModule[0] };
            }
            return JsonUtility.FromJson<Manifest>(File.ReadAllText(path));
        }

        // ------------------------------------------------------------ props

        static GameObject Prop(string fbxName, string name)
        {
            var go = Instance($"{PropsDir}/{fbxName}.fbx");
            go.name = name;
            AssignAll(go, LoadMat("M_Props"));
            return go;
        }

        static GameObject Wrap(string name, GameObject visual)
        {
            var root = new GameObject(name);
            visual.transform.SetParent(root.transform, false);
            return root;
        }

        public static void BuildWorldPrefabs()
        {
            BuildTorchPrefab();
            BuildMenuHero();

            // Chest with a hinged lid.
            var chestVis = Prop("Chest", "Visual");
            var chest = Wrap("Chest", chestVis);
            var c = chest.AddComponent<Chest>();
            c.lid = Find(chestVis.transform, "Chest_Lid");
            c.glow = PointLight(chest.transform, new Vector3(0f, 0.8f, -0.6f), new Color(1f, 0.8f, 0.4f), 1.4f, 3f, "Glow");
            c.range = 1.6f;
            Save(chest, "World/Chest");

            // Chronometer-gate teleporter.
            var telVis = Prop("Teleporter", "Visual");
            var tel = Wrap("Teleporter", telVis);
            var t = tel.AddComponent<Teleporter>();
            var portal = Find(telVis.transform, "PortalSocket");
            t.glow = PointLight(portal != null ? portal : tel.transform, portal != null ? new Vector3(0f, 0f, -0.4f) : new Vector3(0f, 1.6f, -0.6f), new Color(0.75f, 0.45f, 1f), 0.4f, 6f, "Glow");
            t.glowRenderers = telVis.GetComponentsInChildren<Renderer>();
            t.range = 1.9f;
            Save(tel, "World/Teleporter");

            // Lore tablet.
            var loreVis = Prop("LoreTablet", "Visual");
            var lore = Wrap("LoreTablet", loreVis);
            var lt = lore.AddComponent<LoreTablet>();
            lt.glow = PointLight(lore.transform, new Vector3(0f, 0.9f, -0.6f), new Color(0.55f, 1f, 0.5f), 1.8f, 3.5f, "Glow");
            Save(lore, "World/LoreTablet");

            // Fountain (flask refill) with a violet spray.
            var fVis = Prop("Fountain", "Visual");
            var liquid = Find(fVis.transform, "Fountain_Liquid");
            if (liquid != null)
                foreach (var r in liquid.GetComponentsInChildren<Renderer>())
                    r.sharedMaterial = LoadMat("M_Liquid_Wine");
            var fountain = Wrap("Fountain", fVis);
            var fo = fountain.AddComponent<Fountain>();
            fo.water = FxLibrary.Create("Spray", fountain.transform, LoadMat("M_FX_Flash"), ps =>
            {
                var main = ps.main;
                main.loop = true;
                main.startLifetime = new ParticleSystem.MinMaxCurve(0.6f, 1.1f);
                main.startSpeed = new ParticleSystem.MinMaxCurve(1.2f, 2.4f);
                main.startSize = new ParticleSystem.MinMaxCurve(0.04f, 0.09f);
                main.startColor = new ParticleSystem.MinMaxGradient(new Color(1.4f, 0.6f, 2.6f, 0.8f), new Color(2.2f, 1.2f, 3.2f, 1f));
                main.gravityModifier = 0.6f;
                var e = ps.emission;
                e.rateOverTime = 26f;
                var shape = ps.shape;
                shape.shapeType = ParticleSystemShapeType.Cone;
                shape.angle = 18f;
                shape.radius = 0.05f;
                shape.rotation = new Vector3(-90f, 0f, 0f);
            });
            fo.water.transform.localPosition = new Vector3(0f, 1.25f, -0.2f);
            fo.water.Play();
            PointLight(fountain.transform, new Vector3(0f, 1.2f, -0.6f), new Color(0.8f, 0.5f, 1f), 1.8f, 4f, "Glow");
            fo.range = 1.8f;
            Save(fountain, "World/Fountain");

            // Exit door: double doors swing open when unlocked.
            var dVis = Prop("ExitDoor", "Visual");
            var door = Wrap("ExitDoor", dVis);
            var ed = door.AddComponent<ExitDoor>();
            ed.leaf = Find(dVis.transform, "Door_Left");
            ed.leafRight = Find(dVis.transform, "Door_Right");
            var dl = Find(dVis.transform, "ExitDoor_Light");
            if (dl != null)
                foreach (var r in dl.GetComponentsInChildren<Renderer>())
                {
                    r.sharedMaterial = LoadMat("M_FX_Star");
                    r.shadowCastingMode = ShadowCastingMode.Off;
                }
            PointLight(door.transform, new Vector3(0f, 1.8f, -0.4f), new Color(1f, 0.85f, 0.6f), 2.2f, 5f, "DoorLight");
            ed.range = 2.2f;
            Save(door, "World/ExitDoor");

            // Merchant at his stall.
            var merchant = new GameObject("Merchant");
            var stall = Prop("MerchantStall", "Stall");
            stall.transform.SetParent(merchant.transform, false);
            stall.transform.localPosition = new Vector3(0f, 0f, 0.6f);
            var ls = Find(stall.transform, "LightSocket");
            PointLight(ls != null ? ls : stall.transform, ls != null ? Vector3.zero : new Vector3(0f, 2.4f, -0.4f), new Color(1f, 0.7f, 0.4f), 2.4f, 5f, "Lantern");
            var mVis = Prop("Merchant", "Visual");
            mVis.transform.SetParent(merchant.transform, false);
            mVis.transform.localPosition = new Vector3(0f, 0f, -0.2f);
            var mn = merchant.AddComponent<NpcInteractable>();
            mn.role = NpcInteractable.Role.Merchant;
            mn.range = 2f;
            Save(merchant, "World/Merchant");

            // The Collector ("the Horologist").
            var colVis = Prop("Collector", "Visual");
            var collector = Wrap("Collector", colVis);
            var cn = collector.AddComponent<NpcInteractable>();
            cn.role = NpcInteractable.Role.Collector;
            cn.range = 2f;
            PointLight(collector.transform, new Vector3(0.4f, 2.0f, -0.8f), new Color(0.6f, 0.9f, 1f), 2.4f, 4.5f, "Lamp");
            Save(collector, "World/Collector");

            // Shop pedestal / item drop.
            var pedVis = Prop("Pedestal", "Visual");
            var pedestal = Wrap("Pedestal", pedVis);
            var ip = pedestal.AddComponent<ItemPickup>();
            var socket = Find(pedVis.transform, "ItemSocket");
            var display = new GameObject("Display").transform;
            display.SetParent(pedestal.transform, false);
            display.localPosition = socket != null ? pedestal.transform.InverseTransformPoint(socket.position) : new Vector3(0f, 1.15f, 0f);
            ip.display = display;
            PointLight(pedestal.transform, new Vector3(0f, 1.4f, -0.6f), new Color(1f, 0.85f, 0.6f), 1.2f, 2.5f, "Glow");
            Save(pedestal, "World/Pedestal");

            var drop = new GameObject("ItemDrop");
            var dip = drop.AddComponent<ItemPickup>();
            var dd = new GameObject("Display").transform;
            dd.SetParent(drop.transform, false);
            dd.localPosition = new Vector3(0f, 0.9f, 0f);
            dip.display = dd;
            PointLight(drop.transform, new Vector3(0f, 1f, -0.5f), new Color(1f, 0.85f, 0.6f), 1.4f, 2.5f, "Glow");
            Save(drop, "World/ItemDrop");

            // Scroll and blueprint pickups (the arsenal scroll, the blueprint glows blue).
            var scroll = new GameObject("ScrollPickup");
            var sd = new GameObject("Display").transform;
            sd.SetParent(scroll.transform, false);
            PrefabUtility.InstantiatePrefab(ItemPrefab("Scroll"), sd);
            var sp = scroll.AddComponent<ScrollPickup>();
            sp.display = sd;
            PointLight(scroll.transform, new Vector3(0f, 1f, -0.5f), new Color(1f, 0.6f, 0.4f), 1.6f, 2.5f, "Glow");
            Save(scroll, "World/ScrollPickup");

            var bp = new GameObject("Blueprint");
            var bd = new GameObject("Display").transform;
            bd.SetParent(bp.transform, false);
            var bv = (GameObject)PrefabUtility.InstantiatePrefab(ItemPrefab("Scroll"), bd);
            AssignAll(bv, LoadMat("M_FX_Blueprint"), false);
            bp.AddComponent<BlueprintPickup>();
            PointLight(bp.transform, new Vector3(0f, 0.9f, -0.5f), new Color(0.5f, 0.8f, 1f), 2f, 3f, "Glow");
            Save(bp, "World/Blueprint");

            // Currency.
            var gold = new GameObject("Gold");
            var coin = Prop("Coin", "Visual");
            coin.transform.SetParent(gold.transform, false);
            coin.transform.localScale = Vector3.one * 1.6f;
            coin.AddComponent<Spinner>().speed = 360f;
            Currency(gold, CurrencyPickup.Kind.Gold);
            Save(gold, "World/Gold");

            var cell = new GameObject("Cell");
            MeshObject("Orb", Resources.GetBuiltinResource<Mesh>("Sphere.fbx"), LoadMat("M_FX_Cell"), cell.transform, Vector3.one * 0.2f);
            Currency(cell, CurrencyPickup.Kind.Cell);
            Save(cell, "World/Cell");

            BuildSpikes();
            BuildBossGate();
            BuildBiomeHazards();

            var wp = Asset<WorldPrefabs>($"{ResourcesDir}/WorldPrefabs.asset");
            wp.chest = LoadPrefab("World/Chest");
            wp.teleporter = LoadPrefab("World/Teleporter");
            wp.loreTablet = LoadPrefab("World/LoreTablet");
            wp.fountain = LoadPrefab("World/Fountain");
            wp.exitDoor = LoadPrefab("World/ExitDoor");
            wp.merchant = LoadPrefab("World/Merchant");
            wp.collector = LoadPrefab("World/Collector");
            wp.pedestal = LoadPrefab("World/Pedestal");
            wp.itemDrop = LoadPrefab("World/ItemDrop");
            wp.scroll = LoadPrefab("World/ScrollPickup");
            wp.blueprint = LoadPrefab("World/Blueprint");
            wp.gold = LoadPrefab("World/Gold");
            wp.cell = LoadPrefab("World/Cell");
            wp.bossGate = LoadPrefab("World/BossGate");
            wp.spikes = LoadPrefab("World/Spikes");
            wp.deepMaterial = LoadMat("M_ENV_Deep");
            wp.shaftMaterial = LoadMat("M_LightShaft");
            wp.liquidWater = LoadMat("M_Liquid_Water");
            wp.liquidWine = LoadMat("M_Liquid_Wine");
            wp.liquidVoid = LoadMat("M_Liquid_Void");
            wp.liquidBrass = LoadMat("M_Liquid_Brass");
            EditorUtility.SetDirty(wp);
        }

        static void Currency(GameObject go, CurrencyPickup.Kind kind)
        {
            go.layer = DCLayers.Pickup;
            var rb = go.AddComponent<Rigidbody2D>();
            rb.gravityScale = 2.4f;
            rb.interpolation = RigidbodyInterpolation2D.Interpolate;
            rb.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
            var col = go.AddComponent<CircleCollider2D>();
            col.radius = 0.1f;
            col.sharedMaterial = AssetDatabase.LoadAssetAtPath<PhysicsMaterial2D>($"{Root}/Rendering/PM_Bouncy.physicsMaterial2D") ?? Bouncy();
            go.AddComponent<CurrencyPickup>().kind = kind;
            SetLayer(go, DCLayers.Pickup);
        }

        static PhysicsMaterial2D Bouncy()
        {
            var m = new PhysicsMaterial2D("Bouncy") { friction = 0.4f, bounciness = 0.45f };
            AssetDatabase.CreateAsset(m, $"{Root}/Rendering/PM_Bouncy.physicsMaterial2D");
            return m;
        }

        static T Asset<T>(string path) where T : ScriptableObject
        {
            var a = AssetDatabase.LoadAssetAtPath<T>(path);
            if (a == null)
            {
                a = ScriptableObject.CreateInstance<T>();
                AssetDatabase.CreateAsset(a, path);
            }
            return a;
        }

        /// <summary>Iron spike strip, one tile wide (procedural mesh).</summary>
        static void BuildSpikes()
        {
            var mesh = new Mesh();
            var v = new List<Vector3>();
            var tris = new List<int>();
            for (int i = 0; i < 4; i++)
            {
                float x = -0.375f + i * 0.25f;
                float h = 0.55f + (i % 2) * 0.12f;
                foreach (float z in new[] { -0.6f, 0.2f })
                {
                    int b = v.Count;
                    v.Add(new Vector3(x - 0.1f, 0f, z - 0.1f));
                    v.Add(new Vector3(x + 0.1f, 0f, z - 0.1f));
                    v.Add(new Vector3(x + 0.1f, 0f, z + 0.1f));
                    v.Add(new Vector3(x - 0.1f, 0f, z + 0.1f));
                    v.Add(new Vector3(x, h, z));
                    tris.AddRange(new[] { b, b + 4, b + 1, b + 1, b + 4, b + 2, b + 2, b + 4, b + 3, b + 3, b + 4, b });
                }
            }
            // Flat (faceted) normals.
            var fv = new List<Vector3>();
            var ft = new List<int>();
            for (int i = 0; i < tris.Count; i++)
            {
                fv.Add(v[tris[i]]);
                ft.Add(i);
            }
            mesh.SetVertices(fv);
            mesh.SetTriangles(ft, 0);
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            var saved = SaveMesh(mesh, "SpikeStrip");
            var go = new GameObject("Spikes");
            MeshObject("Strip", saved, LoadMat("M_Spikes"), go.transform, Vector3.one).GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.On;
            Save(go, "World/Spikes");
        }

        /// <summary>Arena portcullis: iron bars + a solid blocker while closed.</summary>
        static void BuildBossGate()
        {
            var mesh = new Mesh();
            var parts = new List<CombineInstance>();
            var cube = Resources.GetBuiltinResource<Mesh>("Cube.fbx");
            for (int i = 0; i < 5; i++)
                parts.Add(new CombineInstance { mesh = cube, transform = Matrix4x4.TRS(new Vector3(-0.4f + i * 0.2f, 1.9f, 0f), Quaternion.identity, new Vector3(0.08f, 3.8f, 0.08f)) });
            foreach (float y in new[] { 0.6f, 2.0f, 3.4f })
                parts.Add(new CombineInstance { mesh = cube, transform = Matrix4x4.TRS(new Vector3(0f, y, 0f), Quaternion.identity, new Vector3(1.0f, 0.1f, 0.12f)) });
            for (int i = 0; i < 5; i++)
                parts.Add(new CombineInstance { mesh = cube, transform = Matrix4x4.TRS(new Vector3(-0.4f + i * 0.2f, -0.05f, 0f), Quaternion.Euler(0f, 0f, 45f), Vector3.one * 0.12f) });
            mesh.CombineMeshes(parts.ToArray(), true, true);
            mesh.RecalculateBounds();
            var saved = SaveMesh(mesh, "Portcullis");
            var go = new GameObject("BossGate");
            var bars = MeshObject("Bars", saved, LoadMat("M_Spikes"), go.transform, Vector3.one);
            bars.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.On;
            var blocker = new GameObject("Blocker");
            blocker.transform.SetParent(go.transform, false);
            blocker.layer = DCLayers.Ground;
            var box = blocker.AddComponent<BoxCollider2D>();
            box.size = new Vector2(1f, 6f);
            box.offset = new Vector2(0f, 3f);
            var gate = go.AddComponent<BossGate>();
            gate.blocker = box;
            gate.bars = bars.transform;
            Save(go, "World/BossGate");
        }

        static void BuildBiomeHazards()
        {
            // Promenade: cloud of crystallized sorrow.
            var cloud = new GameObject("SorrowCloud");
            var ps = FxLibrary.Create("Cloud", cloud.transform, LoadMat("M_FX_Dust"), p =>
            {
                var main = p.main;
                main.loop = true;
                main.startLifetime = new ParticleSystem.MinMaxCurve(2f, 3.5f);
                main.startSpeed = new ParticleSystem.MinMaxCurve(0.05f, 0.25f);
                main.startSize = new ParticleSystem.MinMaxCurve(0.8f, 1.6f);
                main.startColor = new ParticleSystem.MinMaxGradient(new Color(0.55f, 0.65f, 0.9f, 0.35f), new Color(0.75f, 0.85f, 1f, 0.5f));
                main.maxParticles = 60;
                var e = p.emission;
                e.rateOverTime = 14f;
                var shape = p.shape;
                shape.shapeType = ParticleSystemShapeType.Box;
                shape.scale = new Vector3(3f, 0.8f, 1f);
            });
            ps.Play();
            var glints = FxLibrary.Create("Glints", cloud.transform, LoadMat("M_FX_Flash"), p =>
            {
                var main = p.main;
                main.loop = true;
                main.startLifetime = 1f;
                main.startSpeed = 0.1f;
                main.startSize = new ParticleSystem.MinMaxCurve(0.04f, 0.09f);
                main.startColor = new Color(1.6f, 2.2f, 3.2f);
                var e = p.emission;
                e.rateOverTime = 10f;
                var shape = p.shape;
                shape.shapeType = ParticleSystemShapeType.Box;
                shape.scale = new Vector3(3f, 0.6f, 0.6f);
            });
            glints.Play();
            PointLight(cloud.transform, new Vector3(0f, 0f, -0.6f), new Color(0.6f, 0.75f, 1f), 1.2f, 4f, "Glow");
            cloud.AddComponent<SorrowCloud>().shardPrefab = ProjectilePrefab("E_Shard");
            SetLayer(cloud, DCLayers.Fx);
            Save(cloud, "World/SorrowCloud");

            // Clockmaker's Lung: furnace that belches starlight fire.
            var vent = Instance($"{BiomeArtDir}/ClockLung/Meshes/ClockLung_Furnace.fbx");
            vent.name = "Visual";
            AssignAll(vent, LoadMat("M_ClockLung_Kit"));
            var ventRoot = Wrap("FurnaceVent", vent);
            vent.transform.localPosition = new Vector3(0f, 0f, 1.6f);
            var fv = ventRoot.AddComponent<FurnaceVent>();
            fv.flames = FxLibrary.Create("Flames", ventRoot.transform, LoadMat("M_FX_Additive"), p =>
            {
                var main = p.main;
                main.loop = true;
                main.startLifetime = new ParticleSystem.MinMaxCurve(0.4f, 0.8f);
                main.startSpeed = new ParticleSystem.MinMaxCurve(3f, 6f);
                main.startSize = new ParticleSystem.MinMaxCurve(0.08f, 0.18f);
                main.startColor = new ParticleSystem.MinMaxGradient(new Color(4f, 2.2f, 0.5f), new Color(4f, 3.4f, 1.8f));
                var e = p.emission;
                e.rateOverTime = 0f;
                var shape = p.shape;
                shape.shapeType = ParticleSystemShapeType.Box;
                shape.scale = new Vector3(1.2f, 0.2f, 0.6f);
                shape.rotation = new Vector3(-90f, 0f, 0f);
            });
            fv.flames.Play();
            var socket = Find(vent.transform, "LightSocket");
            fv.glow = PointLight(socket != null ? socket : ventRoot.transform, socket != null ? Vector3.zero : new Vector3(0f, 1.2f, 0.6f), new Color(1f, 0.6f, 0.25f), 0.3f, 6f, "Glow");
            Save(ventRoot, "World/FurnaceVent");
        }

        // ------------------------------------------------------------ torch

        public static void BuildTorchPrefab()
        {
            var go = Instance($"{EnvDir}/Meshes/ENV_Torch.fbx");
            go.name = "Torch";
            AssignAll(go, LoadMat("M_ENV_Kit"));
            Transform socket = Find(go.transform, "FlameSocket");
            Vector3 flamePos = socket != null ? go.transform.InverseTransformPoint(socket.position) : new Vector3(0f, 0.795f, -0.495f);

            var flameMesh = AssetDatabase.LoadAllAssetsAtPath($"{CharDir}/Beheaded/Beheaded.fbx").OfType<Mesh>().FirstOrDefault(m => m.name == "Beheaded_Flame");
            var flame = new GameObject("TorchFlame", typeof(MeshFilter), typeof(MeshRenderer));
            flame.transform.SetParent(go.transform, false);
            flame.GetComponent<MeshFilter>().sharedMesh = flameMesh;
            flame.GetComponent<MeshRenderer>().sharedMaterial = LoadMat("M_TorchFlame");
            flame.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
            flame.transform.localScale = Vector3.one * 0.62f;
            flame.transform.localPosition = flamePos - new Vector3(0f, 1.515f * 0.62f, 0f);

            var l = PointLight(go.transform, flamePos + new Vector3(0f, 0.15f, -0.25f), new Color(1f, 0.55f, 0.22f), 4f, 6.5f, "TorchLight");
            AddFlicker(l, 4f, 6.5f);
            var embers = TorchEmbers(go.transform);
            embers.transform.localPosition = flamePos + Vector3.up * 0.1f;
            Save(go, "Torch");
        }

        static void AddFlicker(Light l, float intensity, float range)
        {
            var flicker = l.gameObject.AddComponent<TorchFlicker>();
            flicker.baseIntensity = intensity;
            flicker.baseRange = range;
            flicker.intensityJitter = 0.1f;
            flicker.rangeJitter = 0.04f;
            flicker.speed = 3.5f;
            flicker.wobble = 0f;
        }

        static ParticleSystem TorchEmbers(Transform parent)
        {
            var go = new GameObject("TorchEmbers");
            go.transform.SetParent(parent, false);
            go.layer = DCLayers.Fx;
            var ps = go.AddComponent<ParticleSystem>();
            var main = ps.main;
            main.loop = true;
            main.playOnAwake = true;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.startLifetime = new ParticleSystem.MinMaxCurve(0.5f, 1.2f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.4f, 1.4f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.03f, 0.06f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(3.5f, 1.4f, 0.3f), new Color(4f, 2.4f, 0.6f));
            main.gravityModifier = -0.35f;
            main.maxParticles = 64;
            var emission = ps.emission;
            emission.rateOverTime = 9f;
            var shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Sphere;
            shape.radius = 0.08f;
            var noise = ps.noise;
            noise.enabled = true;
            noise.strength = 0.7f;
            noise.frequency = 1.6f;
            var size = ps.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 1f), new Keyframe(1f, 0f)));
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = LoadMat("M_FX_Additive");
            r.renderMode = ParticleSystemRenderMode.Stretch;
            r.velocityScale = 0.08f;
            r.lengthScale = 1.4f;
            r.shadowCastingMode = ShadowCastingMode.Off;
            return ps;
        }

        // ------------------------------------------------------------ items

        static AttackStep Step(string clip, int total, int a0, int a1, int cancel, int l0, int l1, float lunge, float dmg,
            Vector2 offset, Vector2 size, float knock, float stun, float hitstop, float shake, bool finisher = false) => new AttackStep
        {
            clip = clip, totalFrames = total, activeFrames = new Vector2Int(a0, a1), cancelFrame = cancel, lungeFrames = new Vector2Int(l0, l1),
            lungeSpeed = lunge, damage = dmg, hitboxOffset = offset, hitboxSize = size, knockback = knock, stun = stun,
            hitStopWeight = hitstop, shake = shake, finisher = finisher,
        };

        static ItemDef Item(string id, ItemKind kind, string visual, MountPoint mount, int unlock, int price, int tier, CritRule crit, float critMult)
        {
            var d = Asset<ItemDef>($"{ContentDir}/Items/{id}.asset");
            d.id = id;
            d.kind = kind;
            d.visual = visual != null ? ItemPrefab(visual) : null;
            d.offhandVisual = null;
            d.mount = mount;
            d.unlockCost = unlock;
            d.basePrice = price;
            d.tier = tier;
            d.crit = crit;
            d.critMultiplier = critMult;
            d.icon = null;
            d.icon = visual != null ? AssetDatabase.LoadAssetAtPath<Sprite>($"{ArtDir}/Icons/{visual}.png") : null;
            d.swingSound = "swing.light";
            d.hitSound = "hit.flesh";
            d.fireSound = "";
            EditorUtility.SetDirty(d);
            return d;
        }

        public static void BuildItems()
        {
            var list = new List<ItemDef>();

            var cleaver = Item("melee_cleaver", ItemKind.Melee, "Cleaver", MountPoint.Weapon, 0, 120, 1, CritRule.Finisher, 1.75f);
            cleaver.animSpeed = 0.95f;
            cleaver.arcColor = new Color(2.6f, 1.0f, 2.8f);
            cleaver.arcCore = new Color(6f, 5f, 6.5f);
            cleaver.sparkColor = new Color(2.8f, 1.8f, 2.6f);
            cleaver.combo = new[]
            {
                Step("Slash_Combo_1", 18, 4, 7, 8, 3, 6, 4.5f, 14, new Vector2(1.15f, 1.0f), new Vector2(2.3f, 1.8f), 4f, 0.15f, 0.3f, 0.17f),
                Step("Slash_Combo_2", 18, 4, 7, 8, 3, 6, 4.5f, 16, new Vector2(1.1f, 1.3f), new Vector2(2.2f, 2.3f), 4.5f, 0.15f, 0.35f, 0.2f),
                Step("Slash_Combo_3", 24, 5, 9, 13, 4, 8, 7f, 26, new Vector2(1.3f, 0.9f), new Vector2(2.7f, 2.0f), 9f, 0.35f, 1f, 0.45f, true),
            };
            list.Add(cleaver);

            var rusty = Item("melee_rusty", ItemKind.Melee, "RustySword", MountPoint.Weapon, 0, 110, 1, CritRule.Finisher, 1.5f);
            rusty.animSpeed = 1.05f;
            rusty.arcColor = new Color(0.9f, 2.4f, 3.2f);
            rusty.arcCore = new Color(5f, 6f, 6.5f);
            rusty.sparkColor = new Color(2.2f, 2.6f, 3f);
            rusty.combo = new[]
            {
                Step("Slash_Combo_1", 18, 4, 7, 8, 3, 6, 4.5f, 13, new Vector2(1.15f, 1.0f), new Vector2(2.3f, 1.8f), 4f, 0.15f, 0.25f, 0.16f),
                Step("Slash_Combo_2", 18, 4, 7, 8, 3, 6, 4.5f, 15, new Vector2(1.1f, 1.3f), new Vector2(2.2f, 2.3f), 4.5f, 0.15f, 0.35f, 0.2f),
                Step("Slash_Combo_3", 24, 5, 9, 13, 4, 8, 7f, 22, new Vector2(1.3f, 0.9f), new Vector2(2.7f, 2.0f), 9f, 0.35f, 1f, 0.45f, true),
            };
            list.Add(rusty);

            var broad = Item("melee_broadsword", ItemKind.Melee, "Broadsword", MountPoint.Weapon, 30, 180, 2, CritRule.Disabled, 2f);
            broad.animSpeed = 0.72f;
            broad.arcColor = new Color(3.2f, 1.6f, 0.4f);
            broad.arcCore = new Color(6.5f, 5.5f, 3.5f);
            broad.sparkColor = new Color(3f, 2f, 0.8f);
            broad.combo = new[]
            {
                Step("Slash_Combo_1", 18, 4, 8, 9, 3, 6, 3.5f, 32, new Vector2(1.5f, 1.0f), new Vector2(3.0f, 2.2f), 7f, 0.4f, 0.7f, 0.35f),
                Step("Slash_Combo_3", 24, 5, 10, 14, 4, 8, 5f, 48, new Vector2(1.6f, 0.9f), new Vector2(3.3f, 2.4f), 12f, 0.6f, 1f, 0.6f, true),
            };
            broad.swingSound = "swing.heavy";
            broad.hitSound = "hit.heavy";
            list.Add(broad);

            var spear = Item("melee_spear", ItemKind.Melee, "Spear", MountPoint.Weapon, 40, 170, 2, CritRule.Finisher, 1.9f);
            spear.animSpeed = 1f;
            spear.bladeLength = 1.86f;
            spear.arcColor = new Color(0.9f, 2.6f, 2.2f);
            spear.arcCore = new Color(5f, 6.5f, 6f);
            spear.sparkColor = new Color(2f, 2.8f, 2.6f);
            spear.combo = new[]
            {
                Step("Spear_Thrust_1", 16, 4, 7, 8, 3, 6, 5.5f, 15, new Vector2(1.8f, 1.1f), new Vector2(3.4f, 0.9f), 4f, 0.12f, 0.3f, 0.15f),
                Step("Spear_Thrust_2", 16, 4, 7, 8, 3, 6, 5.5f, 17, new Vector2(1.8f, 1.2f), new Vector2(3.4f, 0.9f), 4.5f, 0.15f, 0.35f, 0.18f),
                Step("Spear_Thrust_3", 22, 5, 9, 12, 4, 8, 9f, 30, new Vector2(2.1f, 1.1f), new Vector2(4.0f, 1.0f), 10f, 0.35f, 1f, 0.45f, true),
            };
            spear.swingSound = "swing.thrust";
            list.Add(spear);

            var daggers = Item("melee_daggers", ItemKind.Melee, "Dagger", MountPoint.Weapon, 50, 160, 2, CritRule.Behind, 2.3f);
            daggers.dualWield = true;
            daggers.offhandVisual = ItemPrefab("Dagger");
            daggers.animSpeed = 1.4f;
            daggers.arcColor = new Color(2.8f, 0.6f, 1.2f);
            daggers.arcCore = new Color(6.5f, 4f, 5f);
            daggers.sparkColor = new Color(3f, 1.2f, 1.6f);
            daggers.combo = new[]
            {
                Step("Slash_Combo_1", 18, 4, 7, 7, 3, 6, 5f, 9, new Vector2(1.0f, 1.0f), new Vector2(2.0f, 1.7f), 2.5f, 0.1f, 0.2f, 0.1f),
                Step("Slash_Combo_2", 18, 4, 7, 7, 3, 6, 5f, 9, new Vector2(1.0f, 1.2f), new Vector2(2.0f, 2.0f), 2.5f, 0.1f, 0.2f, 0.1f),
                Step("Spear_Thrust_1", 16, 4, 7, 8, 3, 6, 7f, 14, new Vector2(1.4f, 1.1f), new Vector2(2.6f, 1.0f), 5f, 0.2f, 0.6f, 0.25f, true),
            };
            list.Add(daggers);

            // Bell-Breaker: two crushing swings; the toll stuns, and stunned foes take critical hits.
            var maul = Item("melee_bellmaul", ItemKind.Melee, "BellMaul", MountPoint.Weapon, 0, 170, 1, CritRule.Disabled, 2.2f);
            maul.animSpeed = 0.66f;
            maul.bladeLength = 1.3f;
            maul.arcColor = new Color(3.2f, 1.9f, 0.5f);
            maul.arcCore = new Color(6.5f, 5.5f, 3.5f);
            maul.sparkColor = new Color(3.2f, 2.2f, 0.8f);
            maul.combo = new[]
            {
                Step("Slash_Combo_1", 18, 4, 8, 10, 3, 6, 3f, 30, new Vector2(1.5f, 1.1f), new Vector2(3.0f, 2.4f), 8f, 0.9f, 0.8f, 0.4f),
                Step("Slash_Combo_3", 24, 5, 10, 15, 4, 8, 4.5f, 46, new Vector2(1.6f, 0.9f), new Vector2(3.3f, 2.6f), 13f, 0.7f, 1f, 0.65f, true),
            };
            maul.swingSound = "swing.heavy";
            maul.hitSound = "hit.bell";
            list.Add(maul);

            // Pendulum Rapier: quick thrusts that crit right after a roll.
            var rapier = Item("melee_rapier", ItemKind.Melee, "PendulumRapier", MountPoint.Weapon, 35, 165, 2, CritRule.AfterDodge, 2.4f);
            rapier.animSpeed = 1.3f;
            rapier.bladeLength = 1.1f;
            rapier.arcColor = new Color(3f, 2.5f, 1.1f);
            rapier.arcCore = new Color(6.5f, 6f, 4.5f);
            rapier.sparkColor = new Color(3f, 2.6f, 1.4f);
            rapier.combo = new[]
            {
                Step("Spear_Thrust_1", 16, 4, 7, 7, 3, 6, 6f, 10, new Vector2(1.6f, 1.15f), new Vector2(3.0f, 0.8f), 3f, 0.1f, 0.25f, 0.12f),
                Step("Spear_Thrust_2", 16, 4, 7, 7, 3, 6, 6f, 11, new Vector2(1.6f, 1.2f), new Vector2(3.0f, 0.8f), 3f, 0.1f, 0.25f, 0.12f),
                Step("Spear_Thrust_3", 22, 5, 9, 12, 4, 8, 9f, 20, new Vector2(1.9f, 1.1f), new Vector2(3.6f, 0.9f), 7f, 0.3f, 0.8f, 0.3f, true),
            };
            rapier.swingSound = "swing.thrust";
            list.Add(rapier);

            // Tide Scythe: slow, very wide sweeps.
            var scythe = Item("melee_scythe", ItemKind.Melee, "TideScythe", MountPoint.Weapon, 45, 190, 2, CritRule.Finisher, 2f);
            scythe.animSpeed = 0.85f;
            scythe.bladeLength = 1.5f;
            scythe.arcColor = new Color(0.6f, 2.6f, 3.0f);
            scythe.arcCore = new Color(4.5f, 6.5f, 6.5f);
            scythe.sparkColor = new Color(1.6f, 2.8f, 3f);
            scythe.combo = new[]
            {
                Step("Slash_Combo_2", 18, 4, 8, 9, 3, 6, 4f, 17, new Vector2(1.6f, 1.3f), new Vector2(3.4f, 2.8f), 5f, 0.2f, 0.4f, 0.22f),
                Step("Slash_Combo_1", 18, 4, 8, 9, 3, 6, 4f, 17, new Vector2(1.6f, 1.0f), new Vector2(3.4f, 2.2f), 5f, 0.2f, 0.4f, 0.22f),
                Step("Slash_Combo_3", 24, 5, 10, 14, 4, 8, 6f, 34, new Vector2(1.7f, 1.0f), new Vector2(3.6f, 2.6f), 11f, 0.4f, 1f, 0.5f, true),
            };
            scythe.swingSound = "swing.heavy";
            list.Add(scythe);

            // Chain Flail: the last hit of the combo sends enemies flying.
            var flail = Item("melee_flail", ItemKind.Melee, "ChainFlail", MountPoint.Weapon, 0, 150, 1, CritRule.Finisher, 2f);
            flail.animSpeed = 0.95f;
            flail.bladeLength = 0.9f;
            flail.arcColor = new Color(3.2f, 1.2f, 0.4f);
            flail.arcCore = new Color(6.5f, 4.5f, 3f);
            flail.sparkColor = new Color(3.2f, 1.6f, 0.6f);
            flail.combo = new[]
            {
                Step("Slash_Combo_1", 18, 4, 7, 9, 3, 6, 4f, 15, new Vector2(1.4f, 1.1f), new Vector2(2.7f, 2.0f), 7f, 0.2f, 0.35f, 0.2f),
                Step("Slash_Combo_2", 18, 4, 7, 9, 3, 6, 4f, 15, new Vector2(1.4f, 1.3f), new Vector2(2.7f, 2.3f), 7f, 0.2f, 0.35f, 0.2f),
                Step("Slash_Combo_3", 24, 5, 9, 14, 4, 8, 6f, 32, new Vector2(1.5f, 0.9f), new Vector2(3.0f, 2.2f), 15f, 0.5f, 1f, 0.55f, true),
            };
            flail.swingSound = "swing.flail";
            flail.hitSound = "hit.heavy";
            list.Add(flail);

            // Gravedigger's Shovel: finishes off anything below 35% health.
            var shovel = Item("melee_shovel", ItemKind.Melee, "GraveShovel", MountPoint.Weapon, 25, 140, 1, CritRule.LowHealth, 2.5f);
            shovel.animSpeed = 1f;
            shovel.bladeLength = 1.2f;
            shovel.arcColor = new Color(2.6f, 2.3f, 1.8f);
            shovel.arcCore = new Color(6f, 6f, 5.5f);
            shovel.sparkColor = new Color(2.6f, 2.4f, 2f);
            shovel.combo = new[]
            {
                Step("Slash_Combo_1", 18, 4, 7, 9, 3, 6, 4.5f, 18, new Vector2(1.4f, 1.0f), new Vector2(2.7f, 2.0f), 6f, 0.2f, 0.35f, 0.2f),
                Step("Slash_Combo_3", 24, 5, 9, 13, 4, 8, 6.5f, 28, new Vector2(1.5f, 0.8f), new Vector2(3.0f, 1.8f), 10f, 0.4f, 0.9f, 0.45f, true),
            };
            shovel.swingSound = "swing.heavy";
            shovel.hitSound = "hit.heavy";
            list.Add(shovel);

            var shield = Item("shield_frontline", ItemKind.Shield, "FrontlineShield", MountPoint.Shield, 0, 140, 1, CritRule.None, 1.5f);
            shield.parryWindow = 0.2f;
            shield.blockReduction = 0.85f;
            shield.parryDamage = 30f;
            shield.sparkColor = new Color(3f, 2.3f, 0.6f);
            list.Add(shield);

            var bow = Item("bow_spiked", ItemKind.Bow, "Bow", MountPoint.Bow, 0, 150, 1, CritRule.LongRange, 1.8f);
            bow.projectile = ProjectilePrefab("P_Arrow");
            bow.projectileSpeed = 32f;
            bow.projectileGravity = 0f;
            bow.damage = 16f;
            bow.cooldown = 0.5f;
            bow.effectColor = new Color(2.2f, 2.4f, 2.8f);
            bow.fireSound = "bow.shoot";
            list.Add(bow);

            // Fishbone Crossbow: slow bolts that pierce every enemy in a line.
            var crossbow = Item("bow_crossbow", ItemKind.Bow, "Crossbow", MountPoint.Bow, 40, 190, 2, CritRule.None, 1.5f);
            crossbow.projectile = ProjectilePrefab("P_Arrow");
            crossbow.projectileSpeed = 42f;
            crossbow.projectileGravity = 0f;
            crossbow.damage = 30f;
            crossbow.cooldown = 1.1f;
            crossbow.pierce = true;
            crossbow.effectColor = new Color(2.8f, 2.2f, 1.2f);
            crossbow.fireSound = "crossbow.shoot";
            list.Add(crossbow);

            var fire = Item("skill_fire_grenade", ItemKind.Skill, "FireGrenade", MountPoint.Weapon, 0, 130, 1, CritRule.None, 1.5f);
            fire.projectile = ProjectilePrefab("P_FireGrenade");
            fire.projectileSpeed = 15f;
            fire.projectileGravity = 30f;
            fire.launchAngle = 32f;
            fire.damage = 20f;
            fire.radius = 2.6f;
            fire.hasEffect = true;
            fire.effect = SkillEffect.Fire;
            fire.effectDuration = 4f;
            fire.cooldown = 10f;
            fire.spin = true;
            fire.effectColor = new Color(3.4f, 1.4f, 0.3f);
            fire.fireSound = "grenade.throw";
            list.Add(fire);

            var ice = Item("skill_ice_grenade", ItemKind.Skill, "IceGrenade", MountPoint.Weapon, 35, 150, 2, CritRule.None, 1.5f);
            ice.projectile = ProjectilePrefab("P_IceGrenade");
            ice.projectileSpeed = 15f;
            ice.projectileGravity = 30f;
            ice.launchAngle = 32f;
            ice.damage = 10f;
            ice.radius = 2.8f;
            ice.hasEffect = true;
            ice.effect = SkillEffect.Ice;
            ice.effectDuration = 3.5f;
            ice.cooldown = 12f;
            ice.spin = true;
            ice.effectColor = new Color(0.9f, 2.2f, 3.4f);
            ice.fireSound = "grenade.throw";
            list.Add(ice);

            var harpoon = Item("skill_harpoon", ItemKind.Skill, "Harpoon", MountPoint.Weapon, 60, 200, 3, CritRule.None, 1.5f);
            harpoon.projectile = ProjectilePrefab("P_Harpoon");
            harpoon.projectileSpeed = 34f;
            harpoon.damage = 28f;
            harpoon.pierce = true;
            harpoon.hasEffect = true;
            harpoon.effect = SkillEffect.Lightning;
            harpoon.effectDuration = 0.6f;
            harpoon.cooldown = 8f;
            harpoon.effectColor = new Color(1.4f, 2.2f, 3.4f);
            harpoon.fireSound = "harpoon.throw";
            list.Add(harpoon);

            BuildArmoryItems(list);
            foreach (var d in list)
                EditorUtility.SetDirty(d);
            var db = Asset<ItemDatabase>($"{ResourcesDir}/ItemDatabase.asset");
            db.items = list;
            db.coinPrefab = LoadPrefab("World/Gold");
            db.cellPrefab = LoadPrefab("World/Cell");
            db.flaskPrefab = ItemPrefab("Flask");
            db.scrollPrefab = LoadPrefab("World/ScrollPickup");
            db.itemDropPrefab = LoadPrefab("World/ItemDrop");
            EditorUtility.SetDirty(db);
        }

        // ------------------------------------------------------------ biomes

        static BiomeDef.TileModule TileModule(string role, string fbx)
        {
            var go = AssetDatabase.LoadAssetAtPath<GameObject>(fbx);
            var mf = go != null ? go.GetComponentInChildren<MeshFilter>() : null;
            if (mf == null)
            {
                Debug.LogError($"[DC] missing tile module {fbx}");
                return null;
            }
            return new BiomeDef.TileModule { role = role, mesh = mf.sharedMesh, matrix = go.transform.worldToLocalMatrix * mf.transform.localToWorldMatrix };
        }

        /// <summary>Static decor prefab from a kit module (material picked by the module's atlas).</summary>
        static GameObject DecorPrefab(string biome, string name, string fbx, Material mat)
        {
            var go = Instance(fbx);
            go.name = name;
            AssignAll(go, mat);
            return Save(go, $"Biomes/{biome}/{name}");
        }

        static GameObject LightPrefab(string biome, string fbx, Material mat, Color color, float intensity)
        {
            var go = Instance(fbx);
            go.name = biome + "_Light";
            AssignAll(go, mat);
            var socket = Find(go.transform, "LightSocket");
            var l = PointLight(socket != null ? socket : go.transform, socket != null ? Vector3.zero : new Vector3(0f, 0.4f, -0.4f), color, intensity, 6.5f, "Light");
            AddFlicker(l, intensity, 6.5f);
            return Save(go, $"Biomes/{biome}/{biome}_Light");
        }

        static BiomeDef.Decor D(GameObject prefab, BiomeDef.Placement p, float density, float z0, float z1, float s0 = 1f, float s1 = 1f, float spin = 0f, float bob = 0f) =>
            new BiomeDef.Decor { prefab = prefab, placement = p, density = density, z = new Vector2(z0, z1), scale = new Vector2(s0, s1), spinSpeed = spin, bob = bob };

        static BiomeDef.EnemyEntry E(string prefab, float weight) => new BiomeDef.EnemyEntry { prefab = LoadPrefab("Enemies/" + prefab), weight = weight };

        public static void BuildBiomes()
        {
            var biomes = new List<BiomeDef>();

            // ---- The Oubliette (existing Prisoners' Quarters kit).
            var oub = Asset<BiomeDef>($"{ContentDir}/Biomes/Oubliette.asset");
            oub.id = "Oubliette";
            oub.locKey = "oubliette";
            oub.depth = 0;
            oub.isPassage = false;
            oub.mainRooms = 10;
            oub.treasureRooms = 2;
            oub.eliteRooms = 0;
            oub.merchant = true;
            oub.lore = new[] { "oub1", "oub2", "oub3" };
            oub.bossTag = "";
            oub.enemyDensity = 0.75f;
            string env = $"{EnvDir}/Meshes/";
            oub.tiles = new List<BiomeDef.TileModule>
            {
                TileModule("Fill_A", env + "ENV_Stone_A.fbx"), TileModule("Fill_B", env + "ENV_Stone_B.fbx"), TileModule("Fill_C", env + "ENV_Stone_C.fbx"),
                TileModule("Top_A", env + "ENV_StoneTop_A.fbx"), TileModule("Top_B", env + "ENV_StoneTop_B.fbx"),
                TileModule("Edge_L", env + "ENV_StoneEdge_L.fbx"), TileModule("Edge_R", env + "ENV_StoneEdge_R.fbx"),
                TileModule("Platform", env + "ENV_WoodPlatform.fbx"), TileModule("BackWall", env + "ENV_BackWall.fbx"),
            };
            var envKit = LoadMat("M_ENV_Kit");
            var bgKit = LoadMat("M_BG_Kit");
            oub.kitMaterial = envKit;
            oub.wallMaterial = LoadMat("M_ENV_Wall");
            oub.deepMaterial = LoadMat("M_ENV_Deep");
            oub.platformMaterial = envKit;
            oub.backWallScale = 0.5f;
            oub.lightPrefab = LoadPrefab("Torch");
            oub.decor = new List<BiomeDef.Decor>
            {
                D(DecorPrefab("Oubliette", "Pillar", env + "ENV_Pillar.fbx", envKit), BiomeDef.Placement.Floor, 7, 1.7f, 1.8f),
                D(DecorPrefab("Oubliette", "Arch", env + "ENV_Arch.fbx", envKit), BiomeDef.Placement.Floor, 2.5f, 1.7f, 1.75f),
                D(DecorPrefab("Oubliette", "CellDoor", env + "ENV_CellDoor.fbx", envKit), BiomeDef.Placement.Floor, 5, 1.6f, 1.65f),
                D(DecorPrefab("Oubliette", "Chain", env + "ENV_Chain.fbx", envKit), BiomeDef.Placement.Ceiling, 6, 0.6f, 1.2f, 0.8f, 1.3f),
                D(DecorPrefab("Oubliette", "Cage", env + "ENV_Cage.fbx", envKit), BiomeDef.Placement.Ceiling, 2, 0.9f, 1.3f),
                D(DecorPrefab("Oubliette", "Banner", env + "ENV_Banner.fbx", envKit), BiomeDef.Placement.WallMounted, 3, 2.3f, 2.3f),
                D(DecorPrefab("Oubliette", "Grate", env + "ENV_Grate.fbx", envKit), BiomeDef.Placement.WallMounted, 3, 2.38f, 2.38f),
                D(DecorPrefab("Oubliette", "Barrel", env + "ENV_Barrel.fbx", envKit), BiomeDef.Placement.Floor, 6, 0.8f, 1.2f),
                D(DecorPrefab("Oubliette", "Crate", env + "ENV_Crate.fbx", envKit), BiomeDef.Placement.Floor, 5, 0.8f, 1.2f),
                D(DecorPrefab("Oubliette", "BonePile", env + "ENV_BonePile.fbx", envKit), BiomeDef.Placement.Floor, 6, 0.6f, 1.0f),
                D(DecorPrefab("Oubliette", "BG_Ruins", env + "BG_Ruins.fbx", bgKit), BiomeDef.Placement.MidBackground, 7, 5f, 5.5f),
                D(DecorPrefab("Oubliette", "BG_Tower_A", env + "BG_Tower_A.fbx", bgKit), BiomeDef.Placement.FarBackground, 2, 10f, 16f, 1f, 1.5f),
                D(DecorPrefab("Oubliette", "BG_Tower_B", env + "BG_Tower_B.fbx", bgKit), BiomeDef.Placement.FarBackground, 2, 10f, 16f, 1f, 1.5f),
                D(DecorPrefab("Oubliette", "BG_Spires", env + "BG_Spires.fbx", bgKit), BiomeDef.Placement.FarBackground, 2, 10f, 16f, 1f, 1.6f),
            };
            Atmosphere(oub, new Color(0.10f, 0.26f, 0.32f), 0.15f, new Color(0.035f, 0.05f, 0.075f), new Color(0.06f, 0.11f, 0.14f),
                new Color(0.62f, 0.82f, 1f), 0.65f, new Color(0.35f, 0.85f, 1f), 0.9f, new Color(1f, 0.55f, 0.22f), 4f,
                new Color(0.55f, 0.95f, 1.1f, 0.5f), new Color(0.9f, 1.1f, 1.2f, 0.9f), new Color(3f, 1.1f, 0.3f), new Color(3.5f, 1.8f, 0.5f), new Color(0.6f, 0.95f, 1f));
            oub.backWallHeight = new Vector2(4.5f, 8f);
            oub.lightSpacing = 8f;
            oub.lightShafts = 3f;
            oub.shaftColor = new Color(0.55f, 0.95f, 1f);
            oub.liquid = BiomeDef.LiquidKind.Water;
            oub.liquidMaterial = LoadMat("M_Liquid_Water");
            oub.ground = new List<BiomeDef.EnemyEntry> { E("Zombie", 3f), E("MossBlob", 1.5f), E("Vermin", 1f) };
            oub.flying = new List<BiomeDef.EnemyEntry>();
            oub.turrets = new List<BiomeDef.EnemyEntry>();
            oub.boss = null;
            oub.hazardPrefab = null;
            oub.hazardDensity = 0f;
            EditorUtility.SetDirty(oub);

            // ---- Kit biomes.
            var prom = KitBiome("Promenade", "promenade", 1, 12, 2, 1, new[] { "prom1", "prom2", "prom3" }, "", 0.8f);
            Atmosphere(prom, new Color(0.05f, 0.06f, 0.15f), 0.12f, new Color(0.025f, 0.028f, 0.06f), new Color(0.05f, 0.055f, 0.1f),
                new Color(0.86f, 0.9f, 1f), 0.7f, new Color(0.6f, 0.75f, 1f), 0.9f, new Color(1f, 0.88f, 0.68f), 3.4f,
                new Color(0.7f, 0.8f, 1.2f, 0.5f), new Color(1f, 1.1f, 1.3f, 0.9f), new Color(1.6f, 2f, 3f), new Color(2f, 2.4f, 3.2f), new Color(0.75f, 0.85f, 1f));
            prom.backWallHeight = new Vector2(2f, 5f);
            prom.lightSpacing = 10f;
            prom.lightShafts = 4f;
            prom.shaftColor = new Color(0.7f, 0.8f, 1f);
            prom.liquid = BiomeDef.LiquidKind.Void;
            prom.liquidMaterial = LoadMat("M_Liquid_Void");
            prom.ground = new List<BiomeDef.EnemyEntry> { E("Sentinel", 3f), E("Zombie", 1.5f), E("MossBlob", 1f) };
            prom.flying = new List<BiomeDef.EnemyEntry> { E("Tick", 3f) };
            prom.turrets = new List<BiomeDef.EnemyEntry> { E("Obelisk", 1f) };
            prom.hazardPrefab = LoadPrefab("World/SorrowCloud");
            prom.hazardDensity = 3f;
            Signature(prom, "MoonChunk", BiomeDef.Placement.Floating, 4f, 3.5f, 6f, 0.6f, 1.1f, 0f, 0.35f);
            Signature(prom, "ClockTower", BiomeDef.Placement.FarBackground, 1.5f, 14f, 18f, 0.9f, 1.2f, bg: true);

            var oss = KitBiome("Ossuary", "ossuary", 2, 12, 2, 1, new[] { "oss1", "oss2", "oss3" }, "boss_guardian", 0.8f);
            Atmosphere(oss, new Color(0.15f, 0.17f, 0.13f), 0.17f, new Color(0.05f, 0.055f, 0.045f), new Color(0.11f, 0.12f, 0.1f),
                new Color(0.85f, 0.9f, 0.8f), 0.55f, new Color(0.7f, 1f, 0.6f), 0.8f, new Color(0.6f, 1f, 0.45f), 3.8f,
                new Color(0.8f, 0.9f, 0.7f, 0.4f), new Color(1f, 1.1f, 0.9f, 0.8f), new Color(1.2f, 2.6f, 0.6f), new Color(1.6f, 3f, 0.8f), new Color(0.85f, 1f, 0.75f));
            oss.backWallHeight = new Vector2(7f, 11f);
            oss.lightSpacing = 9f;
            oss.lightShafts = 2.5f;
            oss.shaftColor = new Color(0.75f, 1f, 0.6f);
            oss.liquid = BiomeDef.LiquidKind.Brass;
            oss.liquidMaterial = LoadMat("M_Liquid_Tallow");
            oss.ground = new List<BiomeDef.EnemyEntry> { E("Monk", 2.5f), E("Sentinel", 1.5f), E("Vermin", 1.5f) };
            oss.flying = new List<BiomeDef.EnemyEntry> { E("Tick", 1f), E("Monk", 1.5f) };
            oss.turrets = new List<BiomeDef.EnemyEntry> { E("Obelisk", 3f) };
            oss.boss = LoadPrefab("Enemies/RoyalGuardian");
            Signature(oss, "RibArch", BiomeDef.Placement.Floor, 3f, 1.8f, 2.2f);
            Signature(oss, "SkullWall", BiomeDef.Placement.WallMounted, 3f, 2.45f, 2.45f, 0.5f, 0.5f);

            var stilt = KitBiome("StiltVillage", "stilt", 3, 13, 3, 1, new[] { "stilt1", "stilt2" }, "", 0.85f);
            Atmosphere(stilt, new Color(0.22f, 0.10f, 0.27f), 0.14f, new Color(0.06f, 0.03f, 0.07f), new Color(0.13f, 0.08f, 0.15f),
                new Color(0.9f, 0.72f, 1f), 0.7f, new Color(1f, 0.6f, 0.95f), 0.9f, new Color(1f, 0.62f, 0.35f), 4.2f,
                new Color(1f, 0.6f, 1.2f, 0.45f), new Color(1.2f, 0.9f, 1.4f, 0.8f), new Color(1.6f, 1.2f, 2.4f), new Color(2f, 1.6f, 2.8f), new Color(1f, 0.75f, 1f));
            stilt.rainUp = true;
            stilt.backWallHeight = new Vector2(3f, 6f);
            stilt.lightSpacing = 9f;
            stilt.lightShafts = 2f;
            stilt.shaftColor = new Color(1f, 0.65f, 1f);
            stilt.liquid = BiomeDef.LiquidKind.Wine;
            stilt.liquidMaterial = LoadMat("M_Liquid_Wine");
            stilt.ground = new List<BiomeDef.EnemyEntry> { E("Fisher", 3f), E("Zombie", 1f), E("Vermin", 1.5f) };
            stilt.flying = new List<BiomeDef.EnemyEntry> { E("Tick", 2f) };
            stilt.turrets = new List<BiomeDef.EnemyEntry> { E("Fisher", 1f) };
            Signature(stilt, "Stilt", BiomeDef.Placement.UnderPlatform, 25f, 0.2f, 0.6f);
            Signature(stilt, "Pagoda", BiomeDef.Placement.FarBackground, 2f, 12f, 18f, 0.9f, 1.3f, bg: true);

            var lung = KitBiome("ClockLung", "lung", 4, 11, 2, 2, new[] { "lung1", "lung2" }, "boss_keeper", 0.9f);
            Atmosphere(lung, new Color(0.22f, 0.13f, 0.06f), 0.13f, new Color(0.06f, 0.04f, 0.02f), new Color(0.15f, 0.1f, 0.06f),
                new Color(1f, 0.82f, 0.55f), 0.75f, new Color(1f, 0.75f, 0.4f), 0.9f, new Color(1f, 0.72f, 0.32f), 4.4f,
                new Color(1.4f, 1.2f, 0.7f, 0.5f), new Color(1.6f, 1.4f, 1f, 0.9f), new Color(3.4f, 2.4f, 0.8f), new Color(4f, 3.2f, 1.6f), new Color(1f, 0.85f, 0.55f));
            lung.backWallHeight = new Vector2(8f, 12f);
            lung.lightSpacing = 8f;
            lung.lightShafts = 3f;
            lung.shaftColor = new Color(1f, 0.8f, 0.45f);
            lung.liquid = BiomeDef.LiquidKind.Brass;
            lung.liquidMaterial = LoadMat("M_Liquid_Brass");
            lung.ground = new List<BiomeDef.EnemyEntry> { E("Sentinel", 2f), E("Fisher", 1f), E("Monk", 1.5f), E("Zombie", 1f) };
            lung.flying = new List<BiomeDef.EnemyEntry> { E("Tick", 2f) };
            lung.turrets = new List<BiomeDef.EnemyEntry> { E("Obelisk", 3f) };
            lung.boss = LoadPrefab("Enemies/TimeKeeper");
            lung.hazardPrefab = LoadPrefab("World/FurnaceVent");
            lung.hazardDensity = 2f;
            Signature(lung, "Gear", BiomeDef.Placement.FarBackground, 6f, 6f, 12f, 1f, 2.2f, 14f);
            Signature(lung, "OrganPipes", BiomeDef.Placement.FarBackground, 2f, 12f, 18f, 0.9f, 1.3f, bg: true);
            Signature(lung, "Furnace", BiomeDef.Placement.Floor, 1.5f, 1.9f, 2.1f);

            // ---- Passage between biomes (Oubliette kit, calmer violet light).
            var passage = Asset<BiomeDef>($"{ContentDir}/Biomes/Passage.asset");
            EditorUtility.CopySerialized(oub, passage);
            passage.name = "Passage";
            passage.id = "Passage";
            passage.locKey = "passage";
            passage.isPassage = true;
            passage.merchant = false;
            passage.lore = new string[0];
            passage.ground = new List<BiomeDef.EnemyEntry>();
            passage.flying = new List<BiomeDef.EnemyEntry>();
            passage.turrets = new List<BiomeDef.EnemyEntry>();
            Atmosphere(passage, new Color(0.13f, 0.1f, 0.24f), 0.14f, new Color(0.04f, 0.035f, 0.08f), new Color(0.09f, 0.08f, 0.15f),
                new Color(0.8f, 0.7f, 1f), 0.6f, new Color(0.7f, 0.55f, 1f), 0.9f, new Color(0.85f, 0.6f, 1f), 3.6f,
                new Color(0.8f, 0.6f, 1.2f, 0.5f), new Color(1f, 0.85f, 1.3f, 0.9f), new Color(2f, 1.2f, 3f), new Color(2.4f, 1.6f, 3.4f), new Color(0.85f, 0.7f, 1f));
            passage.liquidMaterial = LoadMat("M_Liquid_Wine");
            EditorUtility.SetDirty(passage);

            foreach (var b in new[] { prom, oss, stilt, lung })
                EditorUtility.SetDirty(b);
        }

        static void Atmosphere(BiomeDef b, Color fog, float density, Color ambient, Color ambientLight, Color key, float keyIntensity, Color rim, float rimIntensity,
            Color torch, float torchIntensity, Color motesA, Color motesB, Color embersA, Color embersB, Color title)
        {
            b.fogColor = fog;
            b.fogDensity = density;
            b.ambient = ambient;
            b.ambientLight = ambientLight;
            b.keyColor = key;
            b.keyIntensity = keyIntensity;
            b.keyEuler = new Vector3(20f, 24f, 0f);
            b.rimColor = rim;
            b.rimIntensity = rimIntensity;
            b.torchColor = torch;
            b.torchIntensity = torchIntensity;
            b.motesA = motesA;
            b.motesB = motesB;
            b.embersA = embersA;
            b.embersB = embersB;
            b.titleColor = title;
        }

        static BiomeDef KitBiome(string id, string locKey, int depth, int mainRooms, int treasure, int elite, string[] lore, string bossTag, float density)
        {
            var b = Asset<BiomeDef>($"{ContentDir}/Biomes/{id}.asset");
            b.id = id;
            b.locKey = locKey;
            b.depth = depth;
            b.isPassage = false;
            b.mainRooms = mainRooms;
            b.treasureRooms = treasure;
            b.eliteRooms = elite;
            b.merchant = true;
            b.lore = lore;
            b.bossTag = bossTag;
            b.enemyDensity = density;
            b.rainUp = false;
            b.boss = null;
            b.hazardPrefab = null;
            b.hazardDensity = 0f;
            string dir = $"{BiomeArtDir}/{id}";
            var manifest = LoadManifest($"{dir}/biome_manifest.json");
            var kit = LoadMat($"M_{id}_Kit");
            var bg = LoadMat($"M_{id}_BG");
            b.kitMaterial = kit;
            b.wallMaterial = LoadMat($"M_{id}_Wall");
            b.deepMaterial = LoadMat($"M_{id}_Deep");
            b.platformMaterial = kit;
            b.backWallScale = 0.5f;
            b.tiles = new List<BiomeDef.TileModule>();
            foreach (var role in new[] { "Fill_A", "Fill_B", "Fill_C", "Top_A", "Top_B", "Edge_L", "Edge_R", "Platform", "BackWall" })
                b.tiles.Add(TileModule(role, $"{dir}/Meshes/{id}_{role}.fbx"));
            Material MatFor(string module)
            {
                var m = manifest.modules.FirstOrDefault(x => x.name == module);
                return m != null && m.atlas != null && m.atlas.EndsWith("_BG") ? bg : kit;
            }
            GameObject Decor(string role) => DecorPrefab(id, role, $"{dir}/Meshes/{id}_{role}.fbx", MatFor($"{id}_{role}"));
            b.lightPrefab = LightPrefab(id, $"{dir}/Meshes/{id}_Light.fbx", kit, Color.white, 4f);
            b.decor = new List<BiomeDef.Decor>
            {
                D(Decor("Pillar"), BiomeDef.Placement.Floor, 6, 1.7f, 1.8f),
                D(Decor("Arch"), BiomeDef.Placement.Floor, 2.5f, 1.7f, 1.8f),
                D(Decor("Door"), BiomeDef.Placement.Floor, 4, 1.66f, 1.7f),
                D(Decor("Hang"), BiomeDef.Placement.Ceiling, 6, 0.6f, 1.3f, 0.8f, 1.2f),
                D(Decor("Prop_A"), BiomeDef.Placement.Floor, 6, 0.7f, 1.2f),
                D(Decor("Prop_B"), BiomeDef.Placement.Floor, 5, 0.7f, 1.2f),
                D(Decor("Prop_C"), BiomeDef.Placement.Floor, 5, 0.7f, 1.2f),
                D(Decor("BG_Near"), BiomeDef.Placement.MidBackground, 7, 5f, 5.5f),
                D(Decor("BG_Far_A"), BiomeDef.Placement.FarBackground, 2.5f, 10f, 16f, 1f, 1.4f),
                D(Decor("BG_Far_B"), BiomeDef.Placement.FarBackground, 2.5f, 10f, 16f, 1f, 1.4f),
            };
            return b;
        }

        static void Signature(BiomeDef b, string role, BiomeDef.Placement placement, float density, float z0, float z1, float s0 = 1f, float s1 = 1f,
            float spin = 0f, float bob = 0f, bool bg = false)
        {
            string dir = $"{BiomeArtDir}/{b.id}";
            var mat = bg ? LoadMat($"M_{b.id}_BG") : LoadMat($"M_{b.id}_Kit");
            var manifest = LoadManifest($"{dir}/biome_manifest.json");
            var m = manifest.modules.FirstOrDefault(x => x.name == $"{b.id}_{role}");
            if (m != null && m.atlas != null)
                mat = m.atlas.EndsWith("_BG") ? LoadMat($"M_{b.id}_BG") : LoadMat($"M_{b.id}_Kit");
            var prefab = DecorPrefab(b.id, role, $"{dir}/Meshes/{b.id}_{role}.fbx", mat);
            b.decor.Add(D(prefab, placement, density, z0, z1, s0, s1, spin, bob));
        }
    }
}
