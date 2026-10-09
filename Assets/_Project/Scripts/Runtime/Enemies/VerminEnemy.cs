using DeadCells.Combat;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using UnityEngine;

namespace DeadCells.Enemies
{
    /// <summary>Caustic vermin: scurries at you and bursts (the "explosive trap" of the epilogue).</summary>
    public class VerminEnemy : EnemyBase
    {
        public float runSpeed = 6.5f;
        public float fuse = 0.55f;
        public float blastRadius = 2.2f;
        public string runClip = "Run";

        float fuseUntil = -1f;

        protected override void Think(float dt)
        {
            if (fuseUntil > 0f)
            {
                hitFlash?.Flash(new Color(2.6f, 2.2f, 0.4f), Mathf.PingPong(Time.time * 8f, 1f));
                if (Time.time >= fuseUntil)
                    Explode();
                return;
            }
            if (!CanSeePlayer())
            {
                anim.Play("Idle", 0.15f);
                return;
            }
            anim.SetFacing(DirToPlayer);
            anim.Play(runClip, 0.08f);
            if (DistX < 1.4f && Mathf.Abs(DistY) < 1.4f)
            {
                fuseUntil = Time.time + fuse * windupScale;
                Telegraph(false);
            }
        }

        void Explode()
        {
            fuseUntil = -1f;
            var juice = JuiceEngine.Instance;
            Vector3 c = transform.position + Vector3.up * 0.4f;
            juice?.SlamWave(c, blastRadius);
            juice?.Embers(c, 30, new Color(1.6f, 2.6f, 0.4f));
            juice?.Shake(Vector2.up, 0.3f);
            foreach (var col in Physics2D.OverlapCircleAll(c, blastRadius, 1 << DCLayers.Player))
            {
                var h = col.GetComponentInParent<Health>();
                if (h == null)
                    continue;
                h.TakeDamage(new DamageInfo
                {
                    amount = Damage(baseDamage),
                    knockback = new Vector2(Mathf.Sign(h.transform.position.x - c.x) * 7f, 6f),
                    hitPoint = h.transform.position + Vector3.up,
                    source = gameObject,
                    effect = -1,
                });
                h.GetComponent<StatusEffects>()?.Apply(SkillEffect.Fire, 2.5f);
            }
            health.TakeDamage(new DamageInfo { amount = 99999f, source = gameObject, effect = -1 });
        }

        protected override void Move(float dt)
        {
            Vector2 v = body.linearVelocity;
            int dir = DirToPlayer;
            bool go = fuseUntil < 0f && CanSeePlayer() && GroundAhead(dir, 0.35f) && !WallAhead(dir, 0.4f);
            v.x = Mathf.MoveTowards(v.x, go ? dir * runSpeed : 0f, 50f * dt);
            body.linearVelocity = v;
        }
    }
}
