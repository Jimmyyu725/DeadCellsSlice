using System.Collections.Generic;
using DeadCells.Items;
using DeadCells.Player;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// Anything the player can use with the Interact button. The nearest one
    /// in range becomes Current; the HUD shows its prompt (and an item card
    /// for equipment).
    /// </summary>
    public abstract class Interactable : MonoBehaviour
    {
        public float range = 1.7f;
        public Vector3 promptOffset = new Vector3(0f, 2.6f, 0f);

        static readonly List<Interactable> All = new List<Interactable>();

        public static Interactable Current { get; private set; }

        public abstract string Prompt { get; }
        public virtual bool CanInteract => true;
        /// <summary>Item shown on the HUD card (pickups, shop pedestals).</summary>
        public virtual ItemDef CardItem => null;
        public virtual int CardPrice => 0;

        public abstract void Interact(PlayerController player);

        protected virtual void OnEnable() => All.Add(this);

        protected virtual void OnDisable()
        {
            All.Remove(this);
            if (Current == this)
                Current = null;
        }

        public static void Scan(PlayerController player)
        {
            Current = null;
            if (player == null || !player.InControl)
                return;
            Vector3 p = player.transform.position + Vector3.up * 0.9f;
            float best = float.MaxValue;
            foreach (var it in All)
            {
                if (!it.CanInteract)
                    continue;
                Vector3 d = it.transform.position - p;
                float dist = Mathf.Abs(d.x) + Mathf.Max(0f, Mathf.Abs(d.y) - 0.9f) * 1.5f;
                if (dist <= it.range && dist < best)
                {
                    best = dist;
                    Current = it;
                }
            }
        }

        public static IEnumerable<T> AllOf<T>() where T : Interactable
        {
            foreach (var it in All)
                if (it is T t)
                    yield return t;
        }
    }
}
