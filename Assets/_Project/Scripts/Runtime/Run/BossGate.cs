using System.Collections;
using System.Collections.Generic;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// Arena gate: seals behind the player when the boss wakes and opens when
    /// it dies. Also unlocks the arena's exit door.
    /// </summary>
    public class BossGate : MonoBehaviour
    {
        public Collider2D blocker;
        public Transform bars;
        public float triggerX;
        public Enemies.EnemyBase boss;
        public ExitDoor exit;
        bool closed, done;

        void Start()
        {
            SetClosed(false, true);
            if (exit != null)
                exit.locked = true;
        }

        void SetClosed(bool c, bool instant = false)
        {
            closed = c;
            if (blocker != null)
                blocker.enabled = c;
            if (instant && bars != null)
                bars.localPosition = new Vector3(0f, c ? 0f : 3.4f, 0f);
        }

        void Update()
        {
            if (bars != null)
                bars.localPosition = Vector3.MoveTowards(bars.localPosition, new Vector3(0f, closed ? 0f : 3.4f, 0f), Time.deltaTime * 10f);
            if (done)
                return;
            var p = PlayerController.Main;
            if (!closed && p != null && p.transform.position.x > triggerX + 1.5f && boss != null && !boss.IsDead)
            {
                SetClosed(true);
                JuiceEngine.Instance?.Shake(Vector2.down, 0.5f);
                Audio.Sfx.Play("boss.gate");
                Audio.Sfx.Play("boss.intro");
                Audio.Music.Play("music.boss", 0.8f);
                boss.Engage();
                GameHUD.Instance?.ShowBoss(boss);
            }
            if (closed && (boss == null || boss.IsDead))
            {
                done = true;
                SetClosed(false);
                Audio.Music.ForBiome(RunManager.Instance != null && RunManager.Instance.Current != null ? RunManager.Instance.Current.id : "", 4f);
                if (exit != null)
                    exit.locked = false;
                GameHUD.Instance?.ShowBoss(null);
            }
        }
    }
}
