using System.Collections.Generic;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Meta;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// A one-tile solid block hiding a secret: cracked walls break to any hit
    /// (melee, projectiles, ground pound); rune floors only to a ground pound
    /// with the Ram rune. Touching blocks of the same kind break together.
    /// </summary>
    public class Breakable : MonoBehaviour
    {
        public bool ram;
        public int hits = 2;

        static readonly Dictionary<Vector2Int, Breakable> Cells = new Dictionary<Vector2Int, Breakable>();
        Vector2Int cell;
        float shakeUntil;
        Vector3 basePos;
        bool broken;

        bool registered;

        // Start, not OnEnable: the level builder positions the block after instantiating it.
        void Start()
        {
            cell = new Vector2Int(Mathf.FloorToInt(transform.position.x), Mathf.FloorToInt(transform.position.y + 0.05f));
            Cells[cell] = this;
            basePos = transform.localPosition;
            registered = true;
        }

        void OnDestroy()
        {
            if (registered && Cells.TryGetValue(cell, out var b) && b == this)
                Cells.Remove(cell);
        }

        void Update()
        {
            if (!registered)
                return;
            if (Time.time < shakeUntil)
                transform.localPosition = basePos + (Vector3)Random.insideUnitCircle * 0.04f;
            else if (transform.localPosition != basePos)
                transform.localPosition = basePos;
        }

        /// <summary>An attack touched this block. Returns true if it reacted.</summary>
        public bool Hit(bool pound)
        {
            if (broken)
                return false;
            if (ram && !(pound && Runes.Has(Runes.Ram)))
            {
                if (pound)
                {
                    Audio.Sfx.Play("shield.block", transform.position);
                    GameHUD.Instance?.Toast(Loc.Get("hud.need_rune", Loc.Get("rune.ram.name")), new Color(1f, 0.6f, 0.4f));
                }
                return pound;
            }
            shakeUntil = Time.time + 0.15f;
            if (--hits > 0 && !pound)
            {
                Audio.Sfx.Play("hit.heavy", transform.position, 0.6f, 0.7f);
                JuiceEngine.Instance?.Dust(transform.position + Vector3.up * 0.5f, Vector2.up, 4);
                return true;
            }
            BreakGroup();
            return true;
        }

        void BreakGroup()
        {
            var open = new Queue<Breakable>();
            open.Enqueue(this);
            broken = true;
            while (open.Count > 0)
            {
                var b = open.Dequeue();
                b.Shatter();
                foreach (var d in new[] { Vector2Int.up, Vector2Int.down, Vector2Int.left, Vector2Int.right })
                    if (Cells.TryGetValue(b.cell + d, out var n) && n != null && !n.broken && n.ram == ram)
                    {
                        n.broken = true;
                        open.Enqueue(n);
                    }
            }
            Achievements.Unlock("secret_room");
            Audio.Sfx.Play("door.open", transform.position, 0.9f, 0.7f);
            JuiceEngine.Instance?.Shake(Vector2.down, 0.35f);
        }

        void Shatter()
        {
            var juice = JuiceEngine.Instance;
            Vector3 c = transform.position + Vector3.up * 0.5f;
            juice?.Dust(c, Vector2.up, 10);
            juice?.Embers(c, 14, ram ? new Color(3.4f, 1.4f, 0.3f) : new Color(1.4f, 1.3f, 1.2f));
            Audio.Sfx.Play("hazard.spikes", c, 0.5f, 0.6f);
            Destroy(gameObject);
        }

        /// <summary>Breakables overlapping a box (melee swing / ground pound / projectile impact).</summary>
        public static bool HitArea(Vector2 center, Vector2 size, bool pound)
        {
            bool any = false;
            foreach (var col in Physics2D.OverlapBoxAll(center, size, 0f, DCLayers.SolidMask))
            {
                var b = col.GetComponentInParent<Breakable>();
                if (b != null)
                    any |= b.Hit(pound);
            }
            return any;
        }
    }
}
