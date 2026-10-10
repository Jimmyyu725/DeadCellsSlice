using DeadCells.FX;
using DeadCells.Items;
using UnityEngine;

namespace DeadCells.Enemies
{
    /// <summary>Singing obsidian obelisk: stationary, fires sonic rings when it sees you.</summary>
    public class TurretEnemy : EnemyBase
    {
        public GameObject ringPrefab;
        public float interval = 2.6f;
        public float ringSpeed = 9f;
        public int spread = 1;
        public Light core;
        public string singClip = "Attack";

        float timer;
        float charge;

        public override void Configure(int depth, bool elite)
        {
            base.Configure(depth, elite);
            spread = depth >= 3 || elite ? 3 : 1;
        }

        protected override void Think(float dt)
        {
            bool sees = CanSeePlayer();
            if (!sees)
            {
                charge = Mathf.MoveTowards(charge, 0f, dt);
                anim.Play("Idle", 0.2f);
                timer = interval * 0.5f;
            }
            else
            {
                anim.SetFacing(DirToPlayer);
                timer -= dt / windupScale;
                charge = Mathf.Clamp01(1f - timer / 0.8f);
                if (timer <= 0.8f && timer + dt > 0.8f)
                {
                    hitFlash?.Flash(new Color(2.2f, 0.8f, 3f), 0.6f);
                    Audio.Sfx.Play("turret.charge", transform.position + Vector3.up * 1.6f);
                    anim.Restart(anim.Has(singClip) ? singClip : "Idle", 0f);
                }
                if (timer <= 0f)
                {
                    timer = interval;
                    Vector3 from = transform.position + Vector3.up * 1.6f * transform.localScale.y;
                    Vector2 aim = AimAtPlayer(from, ringSpeed);
                    for (int i = 0; i < spread; i++)
                    {
                        float a = (i - (spread - 1) * 0.5f) * 14f;
                        var p = Fire(ringPrefab, from, Quaternion.Euler(0f, 0f, a) * aim, 0f, baseDamage);
                        if (p != null)
                        {
                            p.lifetime = 4f;
                            p.sparkColor = new Color(2f, 1f, 3f);
                        }
                    }
                    squash?.Punch(new Vector2(1.15f, 0.9f));
                    Audio.Sfx.Play("turret.fire", from);
                }
            }
            if (core != null)
                core.intensity = 0.6f + charge * 3.5f;
        }

        protected override void Move(float dt)
        {
            body.linearVelocity = new Vector2(0f, body.linearVelocity.y);
        }
    }
}
