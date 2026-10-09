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
    /// Teleport statue. Lights up when first seen (map marker); using it opens
    /// the map to pick another discovered statue, as in Dead Cells.
    /// </summary>
    public class Teleporter : Interactable
    {
        public Light glow;
        public Renderer[] glowRenderers = new Renderer[0];
        public float discoverRadius = 7f;
        public bool Discovered { get; private set; }
        public int Index { get; set; }

        static readonly int EmissionId = Shader.PropertyToID("_EmissionColor");
        MaterialPropertyBlock block;

        public override bool CanInteract => Discovered;
        public override string Prompt => Loc.Get("hud.teleport");

        void Awake()
        {
            block = new MaterialPropertyBlock();
            SetLit(false);
        }

        void SetLit(bool lit)
        {
            if (glow != null)
                glow.intensity = lit ? 3.2f : 0.4f;
            foreach (var r in glowRenderers)
            {
                if (r == null)
                    continue;
                r.GetPropertyBlock(block);
                block.SetColor(EmissionId, lit ? new Color(1.2f, 0.6f, 3.2f) : new Color(0.08f, 0.05f, 0.15f));
                r.SetPropertyBlock(block);
            }
        }

        void Update()
        {
            if (Discovered)
                return;
            var p = PlayerController.Main;
            if (p != null && Vector2.Distance(p.transform.position, transform.position) < discoverRadius)
                Discover(true);
        }

        public void Discover(bool announce)
        {
            if (Discovered)
                return;
            Discovered = true;
            SetLit(true);
            if (announce)
            {
                GameHUD.Instance?.Toast(Loc.Get("hud.teleporter_found"), new Color(0.8f, 0.6f, 1f));
                JuiceEngine.Instance?.Embers(transform.position + Vector3.up * 1.5f, 24, new Color(1.6f, 0.8f, 3.2f));
            }
        }

        public override void Interact(PlayerController player) => GameUI.Instance?.OpenTeleportMap(this);
    }
}
