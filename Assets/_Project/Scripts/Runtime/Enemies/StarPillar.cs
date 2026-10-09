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
    /// <summary>Telegraphed column of starlight erupting from the floor.</summary>
    public class StarPillar : MonoBehaviour
    {
        public float delay = 0.8f;
        public float duration = 0.45f;
        public float damage = 14f;
        public Vector2 size = new Vector2(1.4f, 6f);
        public GameObject owner;
        public Transform column;
        public ParticleSystem warn;

        float t;
        bool hit;

        void Start()
        {
            if (column != null)
                column.localScale = new Vector3(0.2f, 0.05f, 0.2f);
        }

        void Update()
        {
            t += Time.deltaTime;
            if (t < delay)
                return;
            float k = Mathf.Clamp01((t - delay) / 0.08f);
            if (column != null)
                column.localScale = new Vector3(size.x * (1f - (t - delay) / duration * 0.5f), size.y * k, size.x);
            if (!hit)
            {
                if (t - delay < 0.02f)
                {
                    JuiceEngine.Instance?.Shake(Vector2.up, 0.25f);
                    JuiceEngine.Instance?.Embers(transform.position + Vector3.up, 24, new Color(3.2f, 2.8f, 1.6f));
                }
                var col = Physics2D.OverlapBox((Vector2)transform.position + new Vector2(0f, size.y * 0.5f), size, 0f, 1 << DCLayers.Player);
                var h = col != null ? col.GetComponentInParent<Health>() : null;
                if (h != null)
                {
                    hit = true;
                    h.TakeDamage(new DamageInfo
                    {
                        amount = damage,
                        knockback = new Vector2(0f, 10f),
                        hitPoint = h.transform.position + Vector3.up,
                        source = owner != null ? owner : gameObject,
                        effect = -1,
                    });
                }
            }
            if (t > delay + duration)
                Destroy(gameObject);
        }
    }
}
