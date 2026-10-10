using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>Gold and cells: pop out, bounce, then home in on the player.</summary>
    public class CurrencyPickup : MonoBehaviour
    {
        public enum Kind { Gold, Cell }

        public Kind kind;
        public int amount = 1;

        Rigidbody2D body;
        float age;
        Transform target;

        void Awake()
        {
            body = GetComponent<Rigidbody2D>();
        }

        public void Launch(Vector2 velocity)
        {
            if (body != null)
                body.linearVelocity = velocity;
        }

        void FixedUpdate()
        {
            age += Time.fixedDeltaTime;
            if (target == null)
            {
                var p = PlayerController.Main;
                if (p != null && age > 0.45f)
                    target = p.transform;
                return;
            }
            Vector2 to = (Vector2)(target.position + Vector3.up * 1.0f) - (Vector2)transform.position;
            float speed = Mathf.Lerp(6f, 26f, Mathf.Clamp01((age - 0.45f) * 1.5f));
            if (to.magnitude > 9f && age < 3f)
                return; // only magnetize when reasonably close
            // A short glittering trail while it flies to the player.
            if (Random.value < 0.6f)
                FX.JuiceEngine.Instance?.Glints(transform.position, 1, kind == Kind.Gold ? new Color(3f, 2.3f, 0.7f) : new Color(0.8f, 2.2f, 3.4f));
            if (body != null)
            {
                body.gravityScale = 0f;
                body.linearVelocity = Vector2.MoveTowards(body.linearVelocity, to.normalized * speed, 90f * Time.fixedDeltaTime);
                if (GetComponent<Collider2D>() is Collider2D c)
                    c.enabled = false;
            }
            if (to.magnitude < 0.5f)
                Collect();
        }

        void Collect()
        {
            var rm = RunManager.Instance;
            if (rm != null)
            {
                if (kind == Kind.Gold)
                    rm.AddGold(amount);
                else
                    rm.AddCells(amount);
                Audio.Sfx.Play(kind == Kind.Gold ? "pickup.gold" : "pickup.cell");
                FX.JuiceEngine.Instance?.Glints(transform.position, 3, kind == Kind.Gold ? new Color(3f, 2.3f, 0.7f) : new Color(0.8f, 2.2f, 3.4f));
            }
            Destroy(gameObject);
        }
    }
}
