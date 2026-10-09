using DeadCells.FX;
using DeadCells.Items;
using UnityEngine;

namespace DeadCells.Enemies
{
    /// <summary>
    /// Eel-tongued fisherfolk: flings crystallized-lightning harpoons and
    /// leaps across gables at the player.
    /// </summary>
    public class FisherEnemy : EnemyBase
    {
        public GameObject harpoonPrefab;
        public float runSpeed = 3.8f;
        public float throwRange = 11f;
        public int throwRelease = 19;
        public float harpoonSpeed = 20f;
        public float throwCooldown = 2.8f;
        public float leapCooldown = 4f;
        public Vector2 leapVelocity = new Vector2(8f, 11f);
        public float leapDamage = 16f;

        enum State { Idle, Chase, Throw, Leap }

        State state;
        float clock;
        bool released;
        float nextThrow;
        float nextLeap;
        bool airborne;

        float Frame => clock * 60f + 1f;

        protected override bool InSuperArmor() => state == State.Leap;

        protected override void OnInterrupted() => state = State.Chase;

        protected override void Think(float dt)
        {
            switch (state)
            {
                case State.Idle:
                    anim.Play("Idle", 0.15f);
                    if (CanSeePlayer())
                        state = State.Chase;
                    break;
                case State.Chase:
                    if (!CanSeePlayer(1.5f))
                    {
                        state = State.Idle;
                        break;
                    }
                    anim.SetFacing(DirToPlayer);
                    anim.Play(Mathf.Abs(body.linearVelocity.x) > 0.3f ? "Run" : "Idle", 0.1f);
                    bool heightGap = Mathf.Abs(DistY) > 1.5f;
                    if (Time.time >= nextLeap && (heightGap || DistX > 4f) && DistX < 9f && Grounded)
                        StartLeap();
                    else if (Time.time >= nextThrow && DistX < throwRange && DistX > 2.5f)
                        StartThrow();
                    break;
                case State.Throw:
                    clock += dt / windupScale;
                    if (!released && Frame >= throwRelease)
                    {
                        released = true;
                        Vector3 from = transform.position + new Vector3(FacingDir * 0.8f, 1.6f, 0f);
                        var p = Fire(harpoonPrefab, from, AimAtPlayer(from, harpoonSpeed), 0f, baseDamage);
                        if (p != null)
                        {
                            p.hasEffect = true;
                            p.effect = SkillEffect.Lightning;
                            p.effectDuration = 0.5f;
                            p.sparkColor = new Color(1.6f, 2.4f, 3.2f);
                        }
                    }
                    if (Frame >= anim.FrameCount("Throw"))
                    {
                        state = State.Chase;
                        nextThrow = Time.time + throwCooldown * Random.Range(0.8f, 1.2f);
                    }
                    break;
                case State.Leap:
                    clock += dt;
                    if (airborne && clock > 0.25f && Grounded)
                    {
                        airborne = false;
                        squash?.Punch(new Vector2(1.3f, 0.75f));
                        JuiceEngine.Instance?.Dust(transform.position, Vector2.up, 8);
                        StrikeBox(new Vector2(0f, 0.8f), new Vector2(2.6f, 1.6f), leapDamage, new Vector2(6f, 6f));
                        state = State.Chase;
                        nextLeap = Time.time + leapCooldown;
                    }
                    break;
            }
        }

        void StartThrow()
        {
            state = State.Throw;
            clock = 0f;
            released = false;
            anim.Restart("Throw", 0f);
            anim.SetSpeed(1f / windupScale);
            Telegraph(false);
        }

        void StartLeap()
        {
            state = State.Leap;
            clock = 0f;
            airborne = true;
            anim.Restart("Leap", 0f);
            int dir = DirToPlayer;
            float vx = Mathf.Clamp((player.position.x - transform.position.x) * 1.15f, -leapVelocity.x, leapVelocity.x);
            float vy = leapVelocity.y + Mathf.Clamp(DistY, 0f, 4f) * 1.5f;
            body.linearVelocity = new Vector2(vx == 0f ? dir * 2f : vx, vy);
            squash?.Punch(new Vector2(0.8f, 1.25f));
            Telegraph(false);
        }

        protected override void Move(float dt)
        {
            Vector2 v = body.linearVelocity;
            switch (state)
            {
                case State.Chase:
                    int dir = DirToPlayer;
                    bool go = DistX > 3.5f && GroundAhead(dir) && !WallAhead(dir);
                    v.x = Mathf.MoveTowards(v.x, go ? dir * runSpeed : 0f, 30f * dt);
                    break;
                case State.Idle:
                case State.Throw:
                    v.x = Mathf.MoveTowards(v.x, 0f, 30f * dt);
                    break;
                case State.Leap:
                    break; // ballistic
            }
            body.linearVelocity = v;
        }
    }
}
