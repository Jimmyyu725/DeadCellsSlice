using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>Spins a pickup visual around an axis (coins, item displays).</summary>
    public class Spinner : MonoBehaviour
    {
        public Vector3 axis = Vector3.up;
        public float speed = 240f;

        void Update() => transform.Rotate(axis, speed * Time.deltaTime, Space.Self);
    }
}
