using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Meta;
using DeadCells.Player;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// Promenade "cloud of crystallized sorrow": drifts slowly and drops
    /// crystal shards when the player is beneath it.
    /// </summary>
    public class SorrowCloud : MonoBehaviour
    {
        public GameObject shardPrefab;
        public float drift = 2.5f;
        public float interval = 1.4f;
        public float damage = 12f;

        Vector3 home;
        float timer;
        float phase;

        void Start()
        {
            home = transform.position;
            phase = Random.value * 10f;
            timer = interval;
        }

        void Update()
        {
            phase += Time.deltaTime;
            transform.position = home + new Vector3(Mathf.Sin(phase * 0.35f) * drift, Mathf.Sin(phase * 0.8f) * 0.3f, 0f);
            var p = PlayerController.Main;
            if (p == null || shardPrefab == null)
                return;
            float dx = Mathf.Abs(p.transform.position.x - transform.position.x);
            float dy = transform.position.y - p.transform.position.y;
            if (dx > 4f || dy < 0f || dy > 12f)
                return;
            timer -= Time.deltaTime;
            if (timer > 0f)
                return;
            timer = interval;
            var go = Instantiate(shardPrefab, transform.position + new Vector3(Random.Range(-1f, 1f), -0.5f, 0f), Quaternion.identity);
            go.SetActive(true);
            var proj = go.GetComponent<Items.Projectile>();
            if (proj != null)
            {
                proj.velocity = new Vector2(0f, -4f);
                proj.gravity = 16f;
                proj.fromPlayer = false;
                proj.damage = damage * Difficulty.EnemyDamage;
                proj.owner = gameObject;
            }
        }
    }
}
