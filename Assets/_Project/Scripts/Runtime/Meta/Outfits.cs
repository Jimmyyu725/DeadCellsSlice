using DeadCells.Player;
using UnityEngine;

namespace DeadCells.Meta
{
    /// <summary>
    /// Cosmetic outfits sold by the Tailor: a body tint, the glow of the
    /// body's runes and the colours of the head flame.
    /// </summary>
    public static class Outfits
    {
        public class Def
        {
            public string id;
            public int cost;            // cells (0 = free / unlocked by `requires`)
            public string requires;     // "" or a condition: "bc1".."bc5", "true_end", "boss_rush", "daily"
            public Color tint = Color.white;
            public Color glow = new Color(1.34f, 0.79f, 1.98f);
            public Color core = new Color(4.2f, 3.6f, 4.6f);
            public Color flame = new Color(2.4f, 1.1f, 4.2f);
            public Color tip = new Color(0.55f, 0.12f, 1.1f);
        }

        public static readonly Def[] All =
        {
            new Def { id = "prisoner" },
            new Def { id = "crimson", cost = 40, tint = new Color(1.15f, 0.72f, 0.7f), glow = new Color(2.6f, 0.4f, 0.4f),
                      core = new Color(4.6f, 3.4f, 3f), flame = new Color(4f, 0.9f, 0.5f), tip = new Color(1.2f, 0.1f, 0.1f) },
            new Def { id = "verdant", cost = 40, tint = new Color(0.78f, 1.1f, 0.8f), glow = new Color(0.6f, 2.6f, 0.6f),
                      core = new Color(3.6f, 4.6f, 3.4f), flame = new Color(0.9f, 3.6f, 1f), tip = new Color(0.1f, 1f, 0.3f) },
            new Def { id = "frost", cost = 60, tint = new Color(0.8f, 0.95f, 1.2f), glow = new Color(0.6f, 1.8f, 3f),
                      core = new Color(3.8f, 4.4f, 5f), flame = new Color(0.8f, 2.2f, 4.4f), tip = new Color(0.1f, 0.5f, 1.4f) },
            new Def { id = "gilded", cost = 90, tint = new Color(1.25f, 1.08f, 0.7f), glow = new Color(3f, 2.2f, 0.6f),
                      core = new Color(5f, 4.6f, 3.4f), flame = new Color(4.2f, 2.6f, 0.6f), tip = new Color(1.4f, 0.6f, 0.1f) },
            new Def { id = "ashen", requires = "bc1", tint = new Color(0.62f, 0.62f, 0.66f), glow = new Color(2.6f, 2.6f, 2.8f),
                      core = new Color(4.4f, 4.4f, 4.6f), flame = new Color(1.8f, 1.8f, 2f), tip = new Color(0.3f, 0.3f, 0.35f) },
            new Def { id = "plague", requires = "bc3", tint = new Color(0.85f, 0.95f, 0.6f), glow = new Color(1.6f, 2.6f, 0.3f),
                      core = new Color(4f, 4.6f, 2.4f), flame = new Color(1.6f, 2.8f, 0.4f), tip = new Color(0.5f, 0.8f, 0.05f) },
            new Def { id = "daily", requires = "daily", tint = new Color(1.1f, 0.9f, 1.15f), glow = new Color(3f, 1.2f, 2.6f),
                      core = new Color(4.8f, 4f, 4.6f), flame = new Color(3.6f, 1.2f, 3f), tip = new Color(1.2f, 0.2f, 0.9f) },
            new Def { id = "rusher", requires = "boss_rush", tint = new Color(1.1f, 0.85f, 0.75f), glow = new Color(3.2f, 1.4f, 0.4f),
                      core = new Color(5f, 4f, 3f), flame = new Color(4.2f, 1.6f, 0.3f), tip = new Color(1.4f, 0.3f, 0.05f) },
            new Def { id = "collector", requires = "true_end", tint = new Color(0.7f, 0.85f, 1.05f), glow = new Color(0.6f, 2.6f, 3.4f),
                      core = new Color(4f, 4.8f, 5.2f), flame = new Color(0.6f, 3f, 4.2f), tip = new Color(0.05f, 0.9f, 1.4f) },
        };

        static MetaProgress M => SaveSystem.Data.meta;

        public static Def Get(string id)
        {
            foreach (var o in All)
                if (o.id == id)
                    return o;
            return All[0];
        }

        public static Def Current => Get(M.outfit);

        public static bool Owned(Def o) => o.cost <= 0 && string.IsNullOrEmpty(o.requires) || M.outfitsUnlocked.Contains(o.id);

        /// <summary>Unlock outfits whose condition is now met (called after wins and challenge runs).</summary>
        public static void Grant(string condition)
        {
            foreach (var o in All)
                if (o.requires == condition && !M.outfitsUnlocked.Contains(o.id))
                {
                    M.outfitsUnlocked.Add(o.id);
                    UI.GameHUD.Instance?.Toast(Loc.Get("hud.outfit_unlocked", Loc.Get($"outfit.{o.id}.name")), new Color(0.85f, 0.7f, 1f));
                }
        }

        static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");
        static readonly int EmissionId = Shader.PropertyToID("_EmissionColor");
        static readonly int CoreId = Shader.PropertyToID("_CoreColor");
        static readonly int FlameId = Shader.PropertyToID("_FlameColor");
        static readonly int TipId = Shader.PropertyToID("_TipColor");

        /// <summary>Paint a Beheaded model (the player or the menu hero) in the current outfit.</summary>
        public static void Apply(GameObject model)
        {
            if (model == null)
                return;
            var o = Current;
            var block = new MaterialPropertyBlock();
            foreach (var r in model.GetComponentsInChildren<Renderer>(true))
            {
                if (r.name.EndsWith("_Flame"))
                {
                    r.GetPropertyBlock(block);
                    block.SetColor(CoreId, o.core);
                    block.SetColor(FlameId, o.flame);
                    block.SetColor(TipId, o.tip);
                    r.SetPropertyBlock(block);
                }
                else if (r.name.EndsWith("_Body"))
                {
                    r.GetPropertyBlock(block);
                    block.SetColor(BaseColorId, o.tint);
                    block.SetColor(EmissionId, o.glow);
                    r.SetPropertyBlock(block);
                }
                block.Clear();
            }
        }

        public static void Apply(PlayerController p)
        {
            if (p != null)
                Apply(p.gameObject);
        }
    }
}
