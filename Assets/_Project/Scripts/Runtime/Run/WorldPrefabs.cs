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
    /// <summary>Prefabs shared by every biome (Resources/WorldPrefabs).</summary>
    public class WorldPrefabs : ScriptableObject
    {
        public GameObject chest;
        public GameObject teleporter;
        public GameObject loreTablet;
        public GameObject fountain;
        public GameObject exitDoor;
        public GameObject merchant;
        public GameObject collector;
        public GameObject pedestal;
        public GameObject itemDrop;
        public GameObject scroll;
        public GameObject blueprint;
        public GameObject gold;
        public GameObject cell;
        public GameObject bossGate;
        public GameObject spikes;
        public GameObject mutator, blacksmith, tailor;
        public GameObject timedDoor, curseShroud;
        public GameObject crackedBlock, ramSlab, vineBulb, variantDoor;
        public GameObject runeVine, runeRam, runeSpider;
        public Material deepMaterial;
        public Material shaftMaterial;
        public Material liquidWater, liquidWine, liquidVoid, liquidBrass;

        static WorldPrefabs instance;

        public static WorldPrefabs Instance => instance != null ? instance : instance = Resources.Load<WorldPrefabs>("WorldPrefabs");
    }
}
