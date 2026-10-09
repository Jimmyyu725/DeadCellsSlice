using UnityEngine;

namespace DeadCells.FX
{
    /// <summary>Drives the toon shader's _HitFlash on every renderer of a character.</summary>
    public class HitFlash : MonoBehaviour
    {
        static readonly int FlashId = Shader.PropertyToID("_HitFlash");
        static readonly int FlashColorId = Shader.PropertyToID("_HitFlashColor");

        public Renderer[] renderers;
        public float decay = 9f;

        MaterialPropertyBlock block;
        float amount;
        Color color = new Color(2.2f, 2.2f, 2.2f, 1f);

        void Awake()
        {
            block = new MaterialPropertyBlock();
            if (renderers == null || renderers.Length == 0)
                renderers = GetComponentsInChildren<Renderer>(true);
        }

        public void Flash(Color c, float strength = 1f)
        {
            color = c;
            amount = Mathf.Max(amount, strength);
            Push();
        }

        void Update()
        {
            if (amount <= 0f)
                return;
            // Unscaled: the flash must be visible during hit-stop.
            amount = Mathf.Max(0f, amount - decay * Time.unscaledDeltaTime);
            Push();
        }

        void Push()
        {
            foreach (var r in renderers)
            {
                if (r == null)
                    continue;
                r.GetPropertyBlock(block);
                block.SetFloat(FlashId, amount > 0.5f ? 1f : amount * 2f * 0.6f);
                block.SetColor(FlashColorId, color);
                r.SetPropertyBlock(block);
            }
        }
    }
}
