using UnityEngine;

namespace DeadCells.Enemies
{
    /// <summary>
    /// Procedural animation for the rig-less creatures: body bob and squash
    /// from velocity, flapping wings (tick), wagging tail (vermin), pulsing
    /// (moss) and humming (obelisk).
    /// </summary>
    public class CreatureMotion : MonoBehaviour
    {
        public enum Style { Scurry, Flap, Pulse, Hum }

        public Style style;
        public Transform body;
        public Transform wingL, wingR, tail;
        public float rate = 1f;

        Rigidbody2D rb;
        float t;
        Vector3 bodyPos;
        Quaternion wingLRot, wingRRot, tailRot;

        void Awake()
        {
            rb = GetComponentInParent<Rigidbody2D>();
            if (body != null) bodyPos = body.localPosition;
            if (wingL != null) wingLRot = wingL.localRotation;
            if (wingR != null) wingRRot = wingR.localRotation;
            if (tail != null) tailRot = tail.localRotation;
            t = Random.value * 10f;
        }

        void Update()
        {
            float dt = Time.deltaTime;
            float speed = rb != null ? rb.linearVelocity.magnitude : 0f;
            t += dt * rate * (1f + speed * 0.4f);
            switch (style)
            {
                case Style.Scurry:
                    if (body != null)
                        body.localPosition = bodyPos + new Vector3(0f, Mathf.Abs(Mathf.Sin(t * 14f)) * 0.05f * Mathf.Clamp01(speed), 0f);
                    if (tail != null)
                        tail.localRotation = tailRot * Quaternion.Euler(0f, Mathf.Sin(t * 9f) * 25f, 0f);
                    break;
                case Style.Flap:
                    float flap = Mathf.Sin(t * 38f) * 55f;
                    if (wingL != null) wingL.localRotation = wingLRot * Quaternion.Euler(0f, flap, 0f);
                    if (wingR != null) wingR.localRotation = wingRRot * Quaternion.Euler(0f, -flap, 0f);
                    if (body != null)
                        body.localPosition = bodyPos + new Vector3(0f, Mathf.Sin(t * 4f) * 0.08f, 0f);
                    break;
                case Style.Pulse:
                    if (body != null)
                    {
                        float p = Mathf.Sin(t * 5f);
                        body.localScale = new Vector3(1f + p * 0.06f, 1f - p * 0.07f, 1f + p * 0.06f);
                    }
                    break;
                case Style.Hum:
                    if (body != null)
                        body.localPosition = bodyPos + new Vector3(Mathf.Sin(t * 60f) * 0.004f, 0f, 0f);
                    break;
            }
        }
    }
}
