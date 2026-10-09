using UnityEngine;

namespace DeadCells.Core
{
    /// <summary>Physics layers configured by the editor setup (Tag Manager).</summary>
    public static class DCLayers
    {
        public const int Ground = 8;
        public const int OneWay = 9;
        public const int Player = 10;
        public const int Enemy = 11;
        public const int PlayerDodge = 12;
        public const int Pickup = 13;
        public const int Fx = 14;

        public static readonly string[] Names =
        {
            null, null, null, null, null, null, null, null,
            "Ground", "OneWay", "Player", "Enemy", "PlayerDodge", "Pickup", "FX",
        };

        public static int GroundMask => (1 << Ground) | (1 << OneWay);
        public static int SolidMask => 1 << Ground;
        public static int EnemyMask => 1 << Enemy;
        public static int PlayerMask => (1 << Player) | (1 << PlayerDodge);
    }
}
