using System.Collections.Generic;
using System.Linq;
using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.Enemies;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Player;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace DeadCells.EditorTools
{
    public static partial class DCContentBuilder
    {
        // ------------------------------------------------------ item visuals

        /// <summary>Weapon/item display prefabs (item convention: +Y primary, +X secondary).</summary>
        public static void BuildItemVisuals()
        {
            var weapons = LoadMat("M_Weapons");
            var arsenal = LoadMat("M_Arsenal");
            ItemVisual("RustySword", $"{WeaponDir}/RustySword.fbx", weapons, 0.09f, 0.78f);
            ItemVisual("Broadsword", $"{WeaponDir}/Broadsword.fbx", weapons, 0.12f, 1.32f);
            ItemVisual("FrontlineShield", $"{WeaponDir}/FrontlineShield.fbx", weapons);
            ItemVisual("Cleaver", $"{ArsenalDir}/Cleaver.fbx", arsenal, 0.08f, 0.64f);
            ItemVisual("Spear", $"{ArsenalDir}/Spear.fbx", arsenal, 0.7f, 1.86f);
            ItemVisual("Dagger", $"{ArsenalDir}/Dagger.fbx", arsenal, 0.04f, 0.26f);
            ItemVisual("Bow", $"{ArsenalDir}/Bow.fbx", arsenal);
            ItemVisual("Arrow", $"{ArsenalDir}/Arrow.fbx", arsenal);
            ItemVisual("FireGrenade", $"{ArsenalDir}/FireGrenade.fbx", arsenal);
            ItemVisual("IceGrenade", $"{ArsenalDir}/IceGrenade.fbx", arsenal);
            ItemVisual("Harpoon", $"{ArsenalDir}/Harpoon.fbx", arsenal);
            ItemVisual("Flask", $"{ArsenalDir}/Flask.fbx", arsenal);
            ItemVisual("Scroll", $"{ArsenalDir}/Scroll.fbx", arsenal);
            var armory = LoadMat("M_Armory");
            ItemVisual("BellMaul", $"{ArmoryDir}/BellMaul.fbx", armory, new Vector2(0f, 0.9f), new Vector2(0.15f, 1.18f));
            ItemVisual("PendulumRapier", $"{ArmoryDir}/PendulumRapier.fbx", armory, new Vector2(0f, 0.15f), new Vector2(0f, 1.1f));
            ItemVisual("TideScythe", $"{ArmoryDir}/TideScythe.fbx", armory, new Vector2(0.05f, 1.1f), new Vector2(0.76f, 0.8f));
            ItemVisual("ChainFlail", $"{ArmoryDir}/ChainFlail.fbx", armory, new Vector2(0.05f, 0.4f), new Vector2(0.2f, 0.66f));
            ItemVisual("GraveShovel", $"{ArmoryDir}/GraveShovel.fbx", armory, new Vector2(0f, 0.86f), new Vector2(0f, 1.2f));
            ItemVisual("Crossbow", $"{ArmoryDir}/Crossbow.fbx", armory);
            ItemVisual("Greatsword", $"{CharDir}/RoyalGuardian/Greatsword.fbx", LoadMat("M_Greatsword"));
            BuildArmoryVisuals();
            ItemVisual("Shovel", $"{CharDir}/TimeKeeper/Shovel.fbx", LoadMat("M_Shovel"));
        }

        static void ItemVisual(string name, string fbx, Material mat, float bladeBase = -1f, float bladeTip = -1f) =>
            ItemVisual(name, fbx, mat, new Vector2(0f, bladeBase), new Vector2(0f, bladeTip));

        /// <summary>Item prefab; BladeBase/BladeTip (item space, x = edge side, y = blade axis) drive the slash trail.</summary>
        static void ItemVisual(string name, string fbx, Material mat, Vector2 bladeBase, Vector2 bladeTip)
        {
            var go = Instance(fbx);
            go.name = name;
            AssignAll(go, mat);
            if (bladeTip.y > 0f)
            {
                var b = new GameObject("BladeBase").transform;
                b.SetParent(go.transform, false);
                b.localPosition = bladeBase;
                var t = new GameObject("BladeTip").transform;
                t.SetParent(go.transform, false);
                t.localPosition = bladeTip;
            }
            Save(go, "Items/" + name);
        }

        static GameObject ItemPrefab(string name) => LoadPrefab("Items/" + name);

        // ------------------------------------------------------- projectiles

        static Mesh torusMesh, octaMesh;

        static Mesh Torus()
        {
            if (torusMesh != null)
                return torusMesh;
            var m = new Mesh();
            const int seg = 24, ring = 8;
            const float R = 0.32f, r = 0.07f;
            var v = new List<Vector3>();
            var n = new List<Vector3>();
            var tris = new List<int>();
            for (int i = 0; i <= seg; i++)
            {
                float a = i / (float)seg * Mathf.PI * 2f;
                var c = new Vector3(Mathf.Cos(a), Mathf.Sin(a), 0f);
                for (int j = 0; j <= ring; j++)
                {
                    float b = j / (float)ring * Mathf.PI * 2f;
                    var dir = c * Mathf.Cos(b) + Vector3.forward * Mathf.Sin(b);
                    v.Add(c * R + dir * r);
                    n.Add(dir);
                }
            }
            for (int i = 0; i < seg; i++)
            for (int j = 0; j < ring; j++)
            {
                int a = i * (ring + 1) + j, b2 = a + ring + 1;
                tris.AddRange(new[] { a, b2, a + 1, a + 1, b2, b2 + 1 });
            }
            m.SetVertices(v);
            m.SetNormals(n);
            m.SetTriangles(tris, 0);
            m.RecalculateBounds();
            return torusMesh = SaveMesh(m, "Torus");
        }

        static Mesh Octahedron()
        {
            if (octaMesh != null)
                return octaMesh;
            var m = new Mesh();
            Vector3[] p = { Vector3.up * 0.3f, Vector3.down * 0.3f, Vector3.left * 0.1f, Vector3.right * 0.1f, Vector3.forward * 0.1f, Vector3.back * 0.1f };
            int[] f = { 0, 2, 5, 0, 5, 3, 0, 3, 4, 0, 4, 2, 1, 5, 2, 1, 3, 5, 1, 4, 3, 1, 2, 4 };
            var v = new List<Vector3>();
            var tris = new List<int>();
            for (int i = 0; i < f.Length; i++)
            {
                v.Add(p[f[i]]);
                tris.Add(i);
            }
            m.SetVertices(v);
            m.SetTriangles(tris, 0);
            m.RecalculateNormals();
            m.RecalculateBounds();
            return octaMesh = SaveMesh(m, "Octahedron");
        }

        static GameObject MeshObject(string name, Mesh mesh, Material mat, Transform parent, Vector3 scale)
        {
            var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer));
            go.transform.SetParent(parent, false);
            go.transform.localScale = scale;
            go.GetComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.GetComponent<MeshRenderer>();
            r.sharedMaterial = mat;
            r.shadowCastingMode = ShadowCastingMode.Off;
            return go;
        }

        static void Trail(GameObject go, Color color, float width, float time)
        {
            var t = go.AddComponent<TrailRenderer>();
            t.sharedMaterial = LoadMat("M_FX_Additive");
            t.time = time;
            t.minVertexDistance = 0.05f;
            t.widthCurve = new AnimationCurve(new Keyframe(0f, width), new Keyframe(1f, 0f));
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(color, 0f), new GradientColorKey(color, 1f) },
                new[] { new GradientAlphaKey(1f, 0f), new GradientAlphaKey(0f, 1f) });
            t.colorGradient = g;
            t.shadowCastingMode = ShadowCastingMode.Off;
            t.receiveShadows = false;
        }

        static GameObject ProjectileRoot(string name, float hitRadius)
        {
            var go = new GameObject(name);
            go.layer = DCLayers.Fx;
            var p = go.AddComponent<Projectile>();
            p.hitRadius = hitRadius;
            return go;
        }

        static void SaveProjectile(GameObject go, string name)
        {
            SetLayer(go, DCLayers.Fx);
            Save(go, "Projectiles/" + name);
        }

        public static void BuildProjectiles()
        {
            // Player projectiles use the arsenal models (+Y = flight direction).
            var arrow = ProjectileRoot("P_Arrow", 0.22f);
            var av = (GameObject)PrefabUtility.InstantiatePrefab(ItemPrefab("Arrow"), arrow.transform);
            Trail(arrow, new Color(2f, 2.2f, 2.6f), 0.06f, 0.12f);
            SaveProjectile(arrow, "P_Arrow");

            foreach (var (name, item, color) in new[] { ("P_FireGrenade", "FireGrenade", new Color(3.4f, 1.4f, 0.3f)), ("P_IceGrenade", "IceGrenade", new Color(0.9f, 2.2f, 3.4f)) })
            {
                var g = ProjectileRoot(name, 0.3f);
                PrefabUtility.InstantiatePrefab(ItemPrefab(item), g.transform);
                PointLight(g.transform, Vector3.zero, color / 3.4f, 1.5f, 2.5f);
                Trail(g, color, 0.1f, 0.18f);
                SaveProjectile(g, name);
            }
            var harpoon = ProjectileRoot("P_Harpoon", 0.3f);
            PrefabUtility.InstantiatePrefab(ItemPrefab("Harpoon"), harpoon.transform);
            PointLight(harpoon.transform, new Vector3(0f, 0.4f, -0.3f), new Color(0.5f, 0.75f, 1f), 2.5f, 3f);
            Trail(harpoon, new Color(1.4f, 2.2f, 3.4f), 0.12f, 0.15f);
            SaveProjectile(harpoon, "P_Harpoon");

            // Enemy projectiles: glowing shapes.
            var sphere = Resources.GetBuiltinResource<Mesh>("Sphere.fbx");
            var orb = ProjectileRoot("E_Orb", 0.32f);
            MeshObject("Orb", sphere, LoadMat("M_FX_OrbGreen"), orb.transform, Vector3.one * 0.36f);
            PointLight(orb.transform, Vector3.zero, new Color(0.6f, 1f, 0.5f), 2f, 3f);
            Trail(orb, new Color(1.2f, 3f, 1f), 0.25f, 0.25f);
            SaveProjectile(orb, "E_Orb");

            var ring = ProjectileRoot("E_Ring", 0.38f);
            var rv = MeshObject("Ring", Torus(), LoadMat("M_FX_Ring"), ring.transform, Vector3.one * 1.2f);
            rv.AddComponent<Run.Spinner>().axis = Vector3.forward;
            PointLight(ring.transform, Vector3.zero, new Color(0.7f, 0.4f, 1f), 1.8f, 3f);
            SaveProjectile(ring, "E_Ring");

            var shock = ProjectileRoot("E_Shockwave", 0.55f);
            MeshObject("Wave", sphere, LoadMat("M_FX_Shock"), shock.transform, new Vector3(1.4f, 0.5f, 0.6f)).transform.localPosition = new Vector3(0f, -0.15f, 0f);
            PointLight(shock.transform, Vector3.zero, new Color(1f, 0.75f, 0.3f), 2.5f, 3.5f);
            SaveProjectile(shock, "E_Shockwave");

            var star = ProjectileRoot("E_Star", 0.3f);
            MeshObject("Star", sphere, LoadMat("M_FX_Star"), star.transform, Vector3.one * 0.32f);
            PointLight(star.transform, Vector3.zero, new Color(1f, 0.9f, 0.6f), 2.2f, 3f);
            Trail(star, new Color(3.4f, 3f, 1.8f), 0.22f, 0.3f);
            SaveProjectile(star, "E_Star");

            var shard = ProjectileRoot("E_Shard", 0.22f);
            MeshObject("Shard", Octahedron(), LoadMat("M_FX_Crystal"), shard.transform, Vector3.one);
            Trail(shard, new Color(1.2f, 1.8f, 3f), 0.08f, 0.12f);
            SaveProjectile(shard, "E_Shard");

            // Time Keeper's starlight column.
            var pillar = new GameObject("StarPillar");
            var column = MeshObject("Column", Resources.GetBuiltinResource<Mesh>("Cylinder.fbx"), LoadMat("M_FX_Star"), pillar.transform, new Vector3(0.2f, 0.05f, 0.2f));
            column.transform.localPosition = Vector3.zero;
            var colChild = column.transform;
            var sp = pillar.AddComponent<StarPillar>();
            sp.column = colChild;
            var warn = FxLibrary.Create("Warn", pillar.transform, LoadMat("M_FX_Additive"), ps =>
            {
                var main = ps.main;
                main.loop = true;
                main.startLifetime = 0.5f;
                main.startSpeed = new ParticleSystem.MinMaxCurve(1f, 3f);
                main.startSize = new ParticleSystem.MinMaxCurve(0.04f, 0.08f);
                main.startColor = new Color(3.2f, 2.8f, 1.6f);
                var e = ps.emission;
                e.rateOverTime = 40f;
                var shape = ps.shape;
                shape.shapeType = ParticleSystemShapeType.Box;
                shape.scale = new Vector3(1.2f, 0.1f, 0.4f);
                shape.rotation = new Vector3(-90f, 0f, 0f);
            });
            warn.Play();
            sp.warn = warn;
            PointLight(pillar.transform, new Vector3(0f, 1f, -0.5f), new Color(1f, 0.9f, 0.6f), 2.5f, 4f);
            SetLayer(pillar, DCLayers.Fx);
            Save(pillar, "Projectiles/StarPillar");
            BuildArmoryProjectiles();
        }

        static GameObject ProjectilePrefab(string name) => LoadPrefab("Projectiles/" + name);

        // ------------------------------------------------------------- rigs

        static (GameObject root, Transform facing, Transform squash, Transform yaw, GameObject model) Rig(
            string name, string fbx, string controller, float modelScale)
        {
            var root = new GameObject(name);
            var facing = new GameObject("Visual").transform;
            facing.SetParent(root.transform, false);
            var squash = new GameObject("Squash").transform;
            squash.SetParent(facing, false);
            var yaw = new GameObject("Yaw").transform;
            yaw.SetParent(squash, false);
            var model = Instance(fbx);
            model.transform.SetParent(yaw, false);
            model.transform.localScale = Vector3.one * modelScale;
            if (controller != null)
            {
                var animator = model.GetComponent<Animator>() ?? model.AddComponent<Animator>();
                animator.runtimeAnimatorController = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>($"{AnimDir}/{controller}.controller");
                animator.applyRootMotion = false;
                animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                animator.updateMode = AnimatorUpdateMode.Normal;
            }
            return (root, facing, squash, yaw, model);
        }

        /// <summary>
        /// Local pose that puts an item's +Y along `primaryModel` and +X along
        /// `secondaryModel` (model space, bind pose) when parented to `socket`.
        /// </summary>
        static (Vector3 pos, Quaternion rot) MountPose(Transform socket, Transform modelRoot, Vector3 primaryModel, Vector3 secondaryModel, Vector3 offsetModel)
        {
            var probe = new GameObject("MountProbe").transform;
            Vector3 zModel = Vector3.Cross(secondaryModel, primaryModel);
            Quaternion modelRot = Quaternion.LookRotation(zModel, primaryModel);
            probe.SetPositionAndRotation(socket.position + modelRoot.TransformVector(offsetModel), modelRoot.rotation * modelRot);
            probe.SetParent(socket, true);
            var result = (probe.localPosition, probe.localRotation);
            Object.DestroyImmediate(probe.gameObject);
            return result;
        }

        static PlayerCombat.Mount Mount(Transform socket, Transform modelRoot, Vector3 primary, Vector3 secondary, Vector3 offset)
        {
            if (socket == null)
            {
                Debug.LogError("[DC] missing socket for mount");
                return default;
            }
            var (p, r) = MountPose(socket, modelRoot, primary, secondary, offset);
            return new PlayerCombat.Mount { socket = socket, localPosition = p, localRotation = r };
        }

        static void Attach(Transform item, Transform socket, Transform modelRoot, Vector3 primaryModel, Vector3 secondaryModel, Vector3 offsetModel)
        {
            var (p, r) = MountPose(socket, modelRoot, primaryModel, secondaryModel, offsetModel);
            item.SetParent(socket, false);
            item.localPosition = p;
            item.localRotation = r;
        }

        static Transform[] Bones(Transform root, params string[] names) => names.Select(n => Find(root, n)).Where(t => t != null).ToArray();

        static PhysicsMaterial2D NoFriction()
        {
            string path = $"{Root}/Rendering/PM_NoFriction.physicsMaterial2D";
            var m = AssetDatabase.LoadAssetAtPath<PhysicsMaterial2D>(path);
            if (m == null)
            {
                System.IO.Directory.CreateDirectory($"{Root}/Rendering");
                m = new PhysicsMaterial2D("NoFriction") { friction = 0f, bounciness = 0f };
                AssetDatabase.CreateAsset(m, path);
            }
            return m;
        }

        static readonly Vector3 Forward = new Vector3(0, 0, -1); // model space: characters face -Z

        // ------------------------------------------------------------ player

        public static void BuildPlayerPrefab()
        {
            var (root, facing, squash, yaw, model) = Rig("Player", $"{CharDir}/Beheaded/Beheaded.fbx", "Beheaded", 1f);
            root.layer = DCLayers.Player;
            yaw.localRotation = Quaternion.Euler(0f, -65f, 0f);

            foreach (var r in model.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                r.updateWhenOffscreen = true;
                r.sharedMaterial = r.name switch
                {
                    "Beheaded_Flame" => LoadMat("M_BeheadedFlame"),
                    "Beheaded_Eye" => LoadMat("M_BeheadedEye"),
                    "Beheaded_Smoke" => LoadMat("M_BeheadedSmoke"),
                    _ => LoadMat("M_Beheaded"),
                };
                r.shadowCastingMode = r.name == "Beheaded_Body" ? ShadowCastingMode.On : ShadowCastingMode.Off;
            }

            Transform weaponSocket = Find(model.transform, "weapon_socket");
            Transform shieldSocket = Find(model.transform, "shield_socket");
            Transform offhandSocket = Find(model.transform, "offhand_socket");
            Transform headSocket = Find(model.transform, "head_socket");

            var flameLight = PointLight(headSocket, Vector3.zero, new Color(0.61f, 0.36f, 0.9f), 2.2f, 4.5f, "FlameLight");

            var body = root.AddComponent<Rigidbody2D>();
            body.bodyType = RigidbodyType2D.Dynamic;
            body.gravityScale = 0f;
            body.freezeRotation = true;
            body.interpolation = RigidbodyInterpolation2D.Interpolate;
            body.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
            var col = root.AddComponent<CapsuleCollider2D>();
            col.size = new Vector2(0.56f, 1.72f);
            col.offset = new Vector2(0f, 0.86f);
            col.direction = CapsuleDirection2D.Vertical;
            col.sharedMaterial = NoFriction();
            var health = root.AddComponent<Health>();
            health.maxHealth = 200f;
            root.AddComponent<GameInput>();
            var anim = root.AddComponent<CharacterAnimator>();
            anim.animator = model.GetComponent<Animator>();
            anim.facingPivot = facing;
            anim.yawPivot = yaw;
            anim.yawFacingRight = -65f;
            var sq = squash.gameObject.AddComponent<SquashStretch>();
            var flash = root.AddComponent<HitFlash>();
            flash.renderers = model.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r => r.name == "Beheaded_Body").Cast<Renderer>().ToArray();
            root.AddComponent<StatusEffects>();

            var sec = model.AddComponent<SecondaryMotion>();
            sec.chains = new List<SecondaryMotion.Chain>
            {
                new SecondaryMotion.Chain { name = "Scarf", bones = Bones(model.transform, "scarf_01", "scarf_02", "scarf_03", "scarf_04"), stiffness = 0.16f, damping = 0.86f, gravity = 3f },
                new SecondaryMotion.Chain { name = "CoatL", bones = Bones(model.transform, "coat_L_01", "coat_L_02", "coat_L_03"), stiffness = 0.3f, damping = 0.8f, gravity = 3f },
                new SecondaryMotion.Chain { name = "CoatR", bones = Bones(model.transform, "coat_R_01", "coat_R_02", "coat_R_03"), stiffness = 0.3f, damping = 0.8f, gravity = 3f },
            };

            var arcGo = new GameObject("SlashArc", typeof(MeshFilter), typeof(MeshRenderer));
            arcGo.transform.SetParent(root.transform, false);
            arcGo.layer = DCLayers.Fx;
            arcGo.GetComponent<MeshRenderer>().sharedMaterial = LoadMat("M_SlashArc");
            var arc = arcGo.AddComponent<SlashArc>();
            arc.pivot = Find(model.transform, "upper_arm.R");

            var controller = root.AddComponent<PlayerController>();
            controller.anim = anim;
            controller.squash = sq;
            controller.hitFlash = flash;
            controller.flameRenderer = model.GetComponentsInChildren<SkinnedMeshRenderer>(true).First(r => r.name == "Beheaded_Flame");
            controller.secondaryMotion = sec;
            controller.baseMaxHealth = 200f;

            var combat = root.AddComponent<PlayerCombat>();
            combat.slashArc = arc;
            combat.weaponMount = Mount(weaponSocket, model.transform, Forward, Vector3.up, Vector3.zero);
            combat.offhandMount = Mount(offhandSocket, model.transform, Forward, Vector3.up, Vector3.zero);
            combat.bowMount = Mount(offhandSocket, model.transform, Vector3.up, Vector3.right, Vector3.zero);
            combat.shieldMount = Mount(shieldSocket, model.transform, new Vector3(0, 0, 1), Vector3.right, new Vector3(0.03f, 0f, 0.03f));
            var flask = (GameObject)PrefabUtility.InstantiatePrefab(ItemPrefab("Flask"));
            Attach(flask.transform, weaponSocket, model.transform, Vector3.up, Vector3.right, Vector3.zero);
            flask.SetActive(false);
            combat.flaskVisual = flask;

            var camTarget = new GameObject("CameraTarget").transform;
            camTarget.SetParent(root.transform, false);
            camTarget.localPosition = new Vector3(0f, 1.3f, 0f);
            _ = flameLight;
            Save(root, "Player");
        }

        /// <summary>Display-only Beheaded for the title screen.</summary>
        public static void BuildMenuHero()
        {
            var (root, facing, squash, yaw, model) = Rig("MenuHero", $"{CharDir}/Beheaded/Beheaded.fbx", "Beheaded", 1f);
            yaw.localRotation = Quaternion.Euler(0f, -40f, 0f);
            foreach (var r in model.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                r.updateWhenOffscreen = true;
                r.sharedMaterial = r.name switch
                {
                    "Beheaded_Flame" => LoadMat("M_BeheadedFlame"),
                    "Beheaded_Eye" => LoadMat("M_BeheadedEye"),
                    "Beheaded_Smoke" => LoadMat("M_BeheadedSmoke"),
                    _ => LoadMat("M_Beheaded"),
                };
            }
            var anim = root.AddComponent<CharacterAnimator>();
            anim.animator = model.GetComponent<Animator>();
            anim.facingPivot = facing;
            anim.yawPivot = yaw;
            anim.yawFacingRight = -40f;
            var cleaver = (GameObject)PrefabUtility.InstantiatePrefab(ItemPrefab("Cleaver"));
            Attach(cleaver.transform, Find(model.transform, "weapon_socket"), model.transform, Forward, Vector3.up, Vector3.zero);
            PointLight(Find(model.transform, "head_socket"), Vector3.zero, new Color(0.61f, 0.36f, 0.9f), 2.6f, 5f, "FlameLight");
            var sec = model.AddComponent<SecondaryMotion>();
            sec.chains = new List<SecondaryMotion.Chain>
            {
                new SecondaryMotion.Chain { name = "Scarf", bones = Bones(model.transform, "scarf_01", "scarf_02", "scarf_03", "scarf_04"), stiffness = 0.16f, damping = 0.86f, gravity = 3f },
            };
            Save(root, "MenuHero");
        }

        // ----------------------------------------------------------- enemies

        static (GameObject root, CharacterAnimator anim, HitFlash flash, SquashStretch squash, GameObject model) EnemyRig(
            string name, string fbx, string controller, float scale, string material, Vector2 colliderSize, bool flying = false)
        {
            var (root, facing, squash, yaw, model) = Rig(name, fbx, controller, scale);
            root.layer = DCLayers.Enemy;
            yaw.localRotation = Quaternion.Euler(0f, -65f, 0f);
            foreach (var r in model.GetComponentsInChildren<Renderer>(true))
            {
                r.sharedMaterial = LoadMat(material);
                r.shadowCastingMode = ShadowCastingMode.On;
                if (r is SkinnedMeshRenderer smr)
                    smr.updateWhenOffscreen = true;
            }
            var body = root.AddComponent<Rigidbody2D>();
            body.bodyType = RigidbodyType2D.Dynamic;
            body.gravityScale = flying ? 0f : 3.2f;
            body.freezeRotation = true;
            body.interpolation = RigidbodyInterpolation2D.Interpolate;
            var col = root.AddComponent<CapsuleCollider2D>();
            col.size = colliderSize;
            col.offset = new Vector2(0f, colliderSize.y * 0.5f);
            col.direction = colliderSize.y >= colliderSize.x ? CapsuleDirection2D.Vertical : CapsuleDirection2D.Horizontal;
            col.sharedMaterial = NoFriction();
            root.AddComponent<Health>();
            root.AddComponent<StatusEffects>();
            var anim = root.AddComponent<CharacterAnimator>();
            anim.animator = model.GetComponent<Animator>();
            anim.facingPivot = facing;
            anim.yawPivot = yaw;
            var flash = root.AddComponent<HitFlash>();
            flash.renderers = model.GetComponentsInChildren<Renderer>(true);
            var sq = squash.gameObject.AddComponent<SquashStretch>();
            var rags = new List<SecondaryMotion.Chain>();
            foreach (var (chain, bones) in new[] { ("RagL", new[] { "coat_L_01", "coat_L_02", "coat_L_03" }), ("RagR", new[] { "coat_R_01", "coat_R_02", "coat_R_03" }) })
            {
                var b = Bones(model.transform, bones);
                if (b.Length > 0)
                    rags.Add(new SecondaryMotion.Chain { name = chain, bones = b, stiffness = 0.25f, damping = 0.82f, gravity = 3f });
            }
            if (rags.Count > 0)
                model.AddComponent<SecondaryMotion>().chains = rags;
            return (root, anim, flash, sq, model);
        }

        static void Wire(EnemyBase e, CharacterAnimator anim, HitFlash flash, SquashStretch squash, GameObject model, string nameKey,
            float health, float damage, int cells)
        {
            e.anim = anim;
            e.hitFlash = flash;
            e.squash = squash;
            e.nameKey = nameKey;
            e.baseHealth = health;
            e.baseDamage = damage;
            e.cellReward = cells;
            e.tintRenderers = model.GetComponentsInChildren<Renderer>(true);
        }

        public static void BuildEnemyPrefabs()
        {
            // Drowned prisoner.
            {
                var (root, anim, flash, sq, model) = EnemyRig("Zombie", $"{CharDir}/Zombie/Zombie.fbx", "Zombie", 1.12f, "M_Zombie", new Vector2(0.62f, 1.62f));
                var e = root.AddComponent<MeleeEnemy>();
                Wire(e, anim, flash, sq, model, "enemy.zombie", 70f, 14f, 2);
                Save(root, "Enemies/Zombie");
            }
            // Clock-hand sentinel.
            {
                var (root, anim, flash, sq, model) = EnemyRig("Sentinel", $"{CharDir}/Sentinel/Sentinel.fbx", "Sentinel", 1f, "M_Sentinel", new Vector2(0.64f, 1.75f));
                var e = root.AddComponent<MeleeEnemy>();
                Wire(e, anim, flash, sq, model, "enemy.sentinel", 95f, 17f, 3);
                e.chaseSpeed = 5.4f;
                e.patrolSpeed = 1.9f;
                e.windupSpeed = 0.7f;
                e.strikeSpeed = 1.3f;
                e.strikeFrames = new Vector2Int(17, 22);
                e.lungeSpeed = 8.5f;
                e.attackRange = 2.2f;
                e.hitboxOffset = new Vector2(1.2f, 1.1f);
                e.hitboxSize = new Vector2(2.0f, 1.6f);
                e.cooldown = 0.75f;
                e.burstColor = new Color(2.4f, 1.8f, 0.7f);
                e.ichorColor = new Color(0.55f, 0.45f, 0.2f);
                Save(root, "Enemies/Sentinel");
            }
            // Orchid-lantern monk.
            {
                var (root, anim, flash, sq, model) = EnemyRig("Monk", $"{CharDir}/Monk/Monk.fbx", "Monk", 1f, "M_Monk", new Vector2(0.6f, 1.7f), true);
                var e = root.AddComponent<CasterEnemy>();
                Wire(e, anim, flash, sq, model, "enemy.monk", 80f, 16f, 3);
                e.flying = true;
                e.orbPrefab = ProjectilePrefab("E_Orb");
                e.lantern = PointLight(root.transform, new Vector3(0f, 2.0f, -0.6f), new Color(0.6f, 1f, 0.5f), 1.6f, 4f, "Lantern");
                e.burstColor = new Color(1.2f, 2.8f, 0.9f);
                e.aggroRange = 13f;
                e.verticalAggro = 5f;
                Save(root, "Enemies/Monk");
            }
            // Eel-tongued fisher.
            {
                var (root, anim, flash, sq, model) = EnemyRig("Fisher", $"{CharDir}/Fisher/Fisher.fbx", "Fisher", 1f, "M_Fisher", new Vector2(0.62f, 1.8f));
                var e = root.AddComponent<FisherEnemy>();
                Wire(e, anim, flash, sq, model, "enemy.fisher", 90f, 15f, 3);
                e.harpoonPrefab = ProjectilePrefab("P_Harpoon");
                e.aggroRange = 13f;
                e.verticalAggro = 5f;
                e.burstColor = new Color(1.1f, 2f, 3.2f);
                Save(root, "Enemies/Fisher");
            }
            // Royal Guardian (boss).
            {
                var (root, anim, flash, sq, model) = EnemyRig("RoyalGuardian", $"{CharDir}/RoyalGuardian/RoyalGuardian.fbx", "RoyalGuardian", 1f, "M_RoyalGuardian", new Vector2(1.1f, 2.9f));
                var sword = (GameObject)PrefabUtility.InstantiatePrefab(ItemPrefab("Greatsword"));
                var socket = Find(model.transform, "weapon_socket");
                if (socket != null)
                    Attach(sword.transform, socket, model.transform, Forward, Vector3.up, Vector3.zero);
                var e = root.AddComponent<RoyalGuardianBoss>();
                Wire(e, anim, flash, sq, model, "enemy.guardian", 2400f, 26f, 0);
                e.isBoss = true;
                e.shockwavePrefab = ProjectilePrefab("E_Shockwave");
                e.aggroRange = 30f;
                e.verticalAggro = 8f;
                e.burstColor = new Color(3f, 2.2f, 0.8f);
                e.ichorColor = new Color(0.5f, 0.1f, 0.12f);
                root.GetComponent<Rigidbody2D>().mass = 20f;
                Save(root, "Enemies/RoyalGuardian");
            }
            // Creatures (rig-less, procedurally animated) first: the Time Keeper summons ticks.
            Creature("Vermin", new Vector2(0.75f, 0.42f), CreatureMotion.Style.Scurry, false, "enemy.vermin", 22f, 22f, 1, root =>
            {
                var e = root.AddComponent<VerminEnemy>();
                e.burstColor = new Color(1.6f, 2.6f, 0.4f);
                return e;
            });
            Creature("Tick", new Vector2(0.7f, 0.6f), CreatureMotion.Style.Flap, true, "enemy.tick", 40f, 12f, 2, root =>
            {
                var e = root.AddComponent<FlyerEnemy>();
                e.flying = true;
                e.aggroRange = 12f;
                e.verticalAggro = 7f;
                e.burstColor = new Color(1.2f, 1.6f, 2.6f);
                return e;
            });
            Creature("MossBlob", new Vector2(1.0f, 0.8f), CreatureMotion.Style.Pulse, false, "enemy.mossblob", 60f, 13f, 2, root =>
            {
                var e = root.AddComponent<CrawlerEnemy>();
                e.burstColor = new Color(0.8f, 2.6f, 1f);
                e.ichorColor = new Color(0.25f, 0.7f, 0.35f);
                return e;
            });
            Creature("Obelisk", new Vector2(0.9f, 2.6f), CreatureMotion.Style.Hum, false, "enemy.obelisk", 120f, 14f, 3, root =>
            {
                var e = root.AddComponent<TurretEnemy>();
                e.ringPrefab = ProjectilePrefab("E_Ring");
                e.core = PointLight(root.transform, new Vector3(0f, 1.6f, -0.6f), new Color(0.75f, 0.45f, 1f), 0.6f, 4f, "Core");
                e.aggroRange = 14f;
                e.verticalAggro = 6f;
                e.burstColor = new Color(2.2f, 1f, 3.2f);
                e.ichorColor = new Color(0.15f, 0.1f, 0.2f);
                e.superArmor = true;
                var rb = root.GetComponent<Rigidbody2D>();
                rb.constraints = RigidbodyConstraints2D.FreezePositionX | RigidbodyConstraints2D.FreezeRotation;
                rb.mass = 50f;
                return e;
            });
            // Time Keeper (final boss).
            {
                var (root, anim, flash, sq, model) = EnemyRig("TimeKeeper", $"{CharDir}/TimeKeeper/TimeKeeper.fbx", "TimeKeeper", 1f, "M_TimeKeeper", new Vector2(1.2f, 3.4f));
                var shovel = (GameObject)PrefabUtility.InstantiatePrefab(ItemPrefab("Shovel"));
                var socket = Find(model.transform, "weapon_socket");
                if (socket != null)
                    Attach(shovel.transform, socket, model.transform, Vector3.up, Forward, Vector3.zero);
                var e = root.AddComponent<TimeKeeperBoss>();
                Wire(e, anim, flash, sq, model, "enemy.timekeeper", 4200f, 28f, 0);
                e.isBoss = true;
                e.starPrefab = ProjectilePrefab("E_Star");
                e.pillarPrefab = ProjectilePrefab("StarPillar");
                e.tickPrefab = LoadPrefab("Enemies/Tick");
                e.aggroRange = 34f;
                e.verticalAggro = 10f;
                e.burstColor = new Color(3.4f, 3f, 1.7f);
                PointLight(root.transform, new Vector3(0f, 2.6f, -0.8f), new Color(1f, 0.85f, 0.55f), 2.4f, 6f, "Starlight");
                root.GetComponent<Rigidbody2D>().mass = 25f;
                Save(root, "Enemies/TimeKeeper");
            }
        }

        static void Creature(string name, Vector2 colliderSize, CreatureMotion.Style style, bool flying, string nameKey, float health, float damage, int cells,
            System.Func<GameObject, EnemyBase> addBrain)
        {
            var (root, anim, flash, sq, model) = EnemyRig(name, $"{CharDir}/Creatures/{name}.fbx", null, 1f, "M_Creatures", colliderSize, flying);
            var motion = model.AddComponent<CreatureMotion>();
            motion.style = style;
            motion.body = model.transform.childCount > 0 ? model.transform.GetChild(0) : model.transform;
            motion.body = Find(model.transform, name) ?? model.transform;
            motion.wingL = Find(model.transform, $"{name}_WingL");
            motion.wingR = Find(model.transform, $"{name}_WingR");
            motion.tail = Find(model.transform, $"{name}_Tail");
            var e = addBrain(root);
            Wire(e, anim, flash, sq, model, nameKey, health, damage, cells);
            if (flying)
            {
                var col = root.GetComponent<CapsuleCollider2D>();
                col.offset = Vector2.zero;
            }
            Save(root, "Enemies/" + name);
        }
    }
}
