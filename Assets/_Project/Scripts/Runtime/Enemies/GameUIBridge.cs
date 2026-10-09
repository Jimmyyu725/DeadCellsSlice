using System.Collections.Generic;
using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Player;
using UnityEngine;

namespace DeadCells.Enemies
{
    /// <summary>Lets enemies show dialogue without referencing the UI assembly section directly.</summary>
    public static class GameUIBridge
    {
        public static System.Action<string, string> Say;
    }
}
