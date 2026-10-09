using UnityEngine;

namespace DeadCells.Environment
{
    /// <summary>
    /// Heavy hanging chain as a damped pendulum about its ceiling anchor
    /// (rotation around world Z, i.e. in the screen plane). Nudged by the
    /// player running through it and by nearby impacts.
    /// </summary>
    public class ChainSway : MonoBehaviour
    {
        public float length = 3f;
        public float damping = 0.6f;
        public float idleAmplitude = 1.5f;
        public float pushRadius = 1.2f;

        float angle;      // degrees
        float velocity;   // degrees / s
        float seed;
        Transform player;
        Rigidbody2D playerBody;

        void Start()
        {
            seed = Random.value * 10f;
            var p = FindAnyObjectByType<Player.PlayerController>();
            if (p != null)
            {
                player = p.transform;
                playerBody = p.GetComponent<Rigidbody2D>();
            }
        }

        void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f)
                return;
            float g = 9.81f / Mathf.Max(0.5f, length);
            float accel = -g * Mathf.Sin(angle * Mathf.Deg2Rad) * Mathf.Rad2Deg - damping * velocity;
            accel += Mathf.Sin(Time.time * 0.7f + seed) * idleAmplitude;
            if (player != null && playerBody != null)
            {
                Vector3 bottom = transform.position + Vector3.down * length * 0.75f;
                Vector2 d = player.position + Vector3.up - bottom;
                if (Mathf.Abs(d.x) < pushRadius && Mathf.Abs(d.y) < length * 0.6f)
                    accel += -playerBody.linearVelocity.x * 9f;
            }
            velocity += accel * dt;
            angle = Mathf.Clamp(angle + velocity * dt, -35f, 35f);
            transform.localRotation = Quaternion.Euler(0f, 0f, angle);
        }

        public void Kick(float degreesPerSecond)
        {
            velocity += degreesPerSecond;
        }
    }
}
