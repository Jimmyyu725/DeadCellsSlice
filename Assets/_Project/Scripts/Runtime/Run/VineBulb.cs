using System.Collections;
using DeadCells.Core;
using DeadCells.FX;
using DeadCells.Meta;
using DeadCells.Player;
using DeadCells.UI;
using UnityEngine;

namespace DeadCells.Run
{
    /// <summary>
    /// A seed bulb that, with the Vine rune, grows a vine up to the ceiling
    /// with leaf platforms every three tiles on alternating sides.
    /// </summary>
    public class VineBulb : Interactable
    {
        public GameObject stalkModel;
        public GameObject leafModel;
        public int maxHeight = 16;
        bool grown;

        public override bool CanInteract => !grown;

        public override string Prompt => Runes.Has(Runes.Vine)
            ? Loc.Get("hud.vine_grow")
            : Loc.Get("hud.need_rune", Loc.Get("rune.vine.name"));

        public override void Interact(PlayerController player)
        {
            if (grown)
                return;
            if (!Runes.Has(Runes.Vine))
            {
                Audio.Sfx.Play("ui.error");
                return;
            }
            grown = true;
            StartCoroutine(Grow());
        }

        /// <summary>Grow without the interaction (tests).</summary>
        public void GrowNow()
        {
            if (!grown)
            {
                grown = true;
                StartCoroutine(Grow());
            }
        }

        IEnumerator Grow()
        {
            Vector2 baseP = transform.position;
            var hit = Physics2D.Raycast(baseP + Vector2.up * 0.6f, Vector2.up, maxHeight, DCLayers.SolidMask);
            int height = Mathf.Clamp(Mathf.FloorToInt((hit.collider != null ? hit.distance + 0.6f : maxHeight) - 1.5f), 3, maxHeight);
            Audio.Sfx.Play("tk.summon", transform.position, 0.8f, 0.8f);
            var juice = JuiceEngine.Instance;
            int side = 1;
            for (int k = 0; k < height; k++)
            {
                var seg = Instantiate(stalkModel, transform);
                seg.SetActive(true);
                seg.transform.localPosition = new Vector3(0f, 0.6f + k, 0f);
                StartCoroutine(Sprout(seg.transform, 0.18f));
                juice?.Embers(transform.position + new Vector3(0f, 0.6f + k, -0.3f), 3, new Color(0.9f, 3f, 0.6f));
                if (k > 0 && k % 3 == 0)
                {
                    Leaf(new Vector3(side * 0.85f, 0.6f + k, 0f));
                    side = -side;
                }
                yield return new WaitForSeconds(0.07f);
            }
            // A last leaf at the top so the climb ends on a step.
            Leaf(new Vector3(side * 0.85f, 0.6f + height - 0.4f, 0f));
        }

        void Leaf(Vector3 local)
        {
            var leaf = Instantiate(leafModel, transform);
            leaf.SetActive(true);
            leaf.transform.localPosition = local + Vector3.down * 0.1f;
            // Tip the pad toward the camera so it reads as a leaf, not a line.
            leaf.transform.localRotation = Quaternion.Euler(-38f, 0f, local.x > 0f ? -8f : 8f);
            leaf.transform.localScale = Vector3.one * 1.1f;
            StartCoroutine(Sprout(leaf.transform, 0.25f));
            var go = new GameObject("LeafPlatform");
            go.transform.SetParent(transform, false);
            go.transform.localPosition = local;
            go.layer = DCLayers.OneWay;
            var col = go.AddComponent<BoxCollider2D>();
            col.size = new Vector2(1.5f, 0.2f);
            col.offset = new Vector2(0f, -0.1f);
            col.usedByEffector = true;
            var eff = go.AddComponent<PlatformEffector2D>();
            eff.useOneWay = true;
            eff.surfaceArc = 170f;
            eff.useSideFriction = false;
            eff.useSideBounce = false;
        }

        static IEnumerator Sprout(Transform t, float duration)
        {
            Vector3 full = t.localScale;
            float time = 0f;
            while (time < duration)
            {
                time += Time.deltaTime;
                float k = Mathf.SmoothStep(0f, 1f, time / duration);
                t.localScale = new Vector3(full.x * k, full.y * k, full.z * k);
                yield return null;
            }
            t.localScale = full;
        }
    }
}
