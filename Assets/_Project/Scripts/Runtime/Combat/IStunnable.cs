using UnityEngine;

namespace DeadCells.Combat
{
    /// <summary>Implemented by enemies that can be stunned by parries.</summary>
    public interface IStunnable
    {
        void Stun(float seconds, Vector2 knockback);
    }
}
