using System.Collections.Generic;
using DeadCells.Core;
using DeadCells.Enemies;
using DeadCells.Environment;
using DeadCells.Items;
using DeadCells.Meta;
using UnityEngine;
using UnityEngine.Rendering;

namespace DeadCells.Run
{
    /// <summary>Slow spin (gears) and bob (floating moon chunks).</summary>
    public class DecorMotion : MonoBehaviour
    {
        public float spinSpeed;
        public float bob;
        Vector3 home;
        float phase;

        void Start()
        {
            home = transform.localPosition;
            phase = Random.value * 10f;
        }

        void Update()
        {
            if (spinSpeed != 0f)
                transform.Rotate(0f, 0f, spinSpeed * Time.deltaTime, Space.Self);
            if (bob > 0f)
            {
                phase += Time.deltaTime;
                transform.localPosition = home + new Vector3(0f, Mathf.Sin(phase * 0.6f) * bob, 0f);
            }
        }
    }
}
