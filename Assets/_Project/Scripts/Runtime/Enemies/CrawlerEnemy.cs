using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using UnityEngine;

namespace DeadCells.Enemies
{
    /// <summary>Moss peasant: slow crawl, then a hop that splashes on landing.</summary>
    public class CrawlerEnemy : EnemyBase
    {
        public float crawlSpeed = 1.4f;
        public float hopCooldown = 2.4f;
        public Vector2 hop = new Vector2(5.5f, 8f);
        public string moveClip = "Run";
        public string hopClip = "Attack";

        float nextHop;
        bool hopping;
        float hopStart;

        protected override bool InSuperArmor() => hopping;

        protected override void Think(float dt)
        {
            if (hopping)
            {
                if (Time.time - hopStart > 0.25f && Grounded)
                {
                    hopping = false;
                    squash?.Punch(new Vector2(1.35f, 0.7f));
                    StrikeBox(new Vector2(0f, 0.5f), new Vector2(2.2f, 1.2f), baseDamage, new Vector2(5f, 5f));
                    JuiceEngine.Instance?.Ichor(transform.position, Vector2.up, new Color(0.3f, 0.9f, 0.5f), 12);
                    nextHop = Time.time + hopCooldown;
                }
                return;
            }
            if (!CanSeePlayer())
            {
                anim.Play("Idle", 0.15f);
                return;
            }
            anim.SetFacing(DirToPlayer);
            anim.Play(moveClip, 0.1f);
            if (Time.time >= nextHop && DistX < 4.5f && Grounded)
            {
                Telegraph(false);
                hopping = true;
                hopStart = Time.time + 0.5f * windupScale;
                Invoke(nameof(Launch), 0.5f * windupScale);
            }
        }

        void Launch()
        {
            if (IsDead || IsDisabled)
            {
                hopping = false;
                return;
            }
            anim.Restart(anim.Has(hopClip) ? hopClip : moveClip, 0f);
            body.linearVelocity = new Vector2(DirToPlayer * hop.x, hop.y);
            squash?.Punch(new Vector2(0.75f, 1.3f));
        }

        protected override void Move(float dt)
        {
            if (hopping)
                return;
            Vector2 v = body.linearVelocity;
            int dir = DirToPlayer;
            bool go = CanSeePlayer() && GroundAhead(dir) && !WallAhead(dir) && DistX > 1f;
            v.x = Mathf.MoveTowards(v.x, go ? dir * crawlSpeed : 0f, 20f * dt);
            body.linearVelocity = v;
        }
    }
}
