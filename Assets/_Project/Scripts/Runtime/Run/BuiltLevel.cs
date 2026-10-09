using System.Collections.Generic;
using DeadCells.Core;
using DeadCells.Enemies;
using DeadCells.Environment;
using DeadCells.Items;
using DeadCells.Meta;
using UnityEngine;
using UnityEngine.Rendering;

namespace DeadCells.Run
{
    /// <summary>What the builder produced (for the run manager, map and camera).</summary>
    public class BuiltLevel
    {
        public GameObject root;
        public LevelData data;
        public BiomeDef biome;
        public Vector3 playerStart;
        public readonly List<Teleporter> teleporters = new List<Teleporter>();
        public readonly List<EnemyBase> enemies = new List<EnemyBase>();
        public readonly List<Vector3> exits = new List<Vector3>();
        public readonly List<Vector3> shops = new List<Vector3>();
        public readonly List<Vector3> treasures = new List<Vector3>();
        public readonly List<Vector3> lore = new List<Vector3>();
        public EnemyBase boss;
        public Rect bounds;
    }
}
