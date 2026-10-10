using System.Linq;
using DeadCells.Core;
using DeadCells.Items;
using DeadCells.Meta;
using DeadCells.Run;
using UnityEngine;

namespace DeadCells.UI
{
    /// <summary>Menu pages shared by the main menu and the pause menu.</summary>
    public static class MenuPages
    {
        static Settings S => SaveSystem.Data.settings;

        public static MenuPage Options(MenuPanel panel)
        {
            var page = new MenuPage { title = () => Loc.Get("options.title") };
            page.Add(MenuItem.Option(() => Loc.Get("options.language"), () => Loc.Get(S.language == Language.Chinese ? "lang.chinese" : "lang.english"), _ =>
            {
                S.language = S.language == Language.Chinese ? Language.English : Language.Chinese;
                Loc.Current = S.language;
                SaveSystem.Save();
            }));
            page.Add(MenuItem.Option(() => Loc.Get("options.shake"), () => Mathf.RoundToInt(S.screenShake * 100f) + "%", d =>
            {
                S.screenShake = Mathf.Clamp01(Mathf.Round((S.screenShake + d * 0.25f) * 4f) / 4f);
                SaveSystem.Save();
            }));
            page.Add(MenuItem.Option(() => Loc.Get("options.music"), () => Mathf.RoundToInt(S.musicVolume * 100f) + "%", d =>
            {
                S.musicVolume = Mathf.Clamp01(Mathf.Round((S.musicVolume + d * 0.1f) * 10f) / 10f);
                SaveSystem.Save();
            }));
            page.Add(MenuItem.Option(() => Loc.Get("options.sfx"), () => Mathf.RoundToInt(S.sfxVolume * 100f) + "%", d =>
            {
                S.sfxVolume = Mathf.Clamp01(Mathf.Round((S.sfxVolume + d * 0.1f) * 10f) / 10f);
                SaveSystem.Save();
            }));
            page.Add(MenuItem.Option(() => Loc.Get("options.flame"), () => Loc.Get("flame." + S.flameIndex), d =>
            {
                S.flameIndex = (S.flameIndex + d + 3) % 3;
                GameManager.Instance?.ApplyFlame(S.flameIndex);
                SaveSystem.Save();
            }));
            page.Add(MenuItem.Option(() => Loc.Get("options.fullscreen"), () => Loc.Get(S.fullscreen ? "options.on" : "options.off"), _ =>
            {
                S.fullscreen = !S.fullscreen;
                ApplyDisplay();
                SaveSystem.Save();
            }));
            page.Add(MenuItem.Option(() => Loc.Get("options.skip_intro"), () => Loc.Get(S.skipIntro ? "options.on" : "options.off"), _ =>
            {
                S.skipIntro = !S.skipIntro;
                SaveSystem.Save();
            }));
            page.Add(MenuItem.Button(() => Loc.Get("options.controls"), () => panel.Push(Controls(panel))));
            page.Add(MenuItem.Button(() => Loc.Get("options.reset"), () => panel.Confirm(() => Loc.Get("options.reset_confirm"), () =>
            {
                SaveSystem.Reset();
                panel.Pop();
            }), null, () => !(RunManager.Instance != null)));
            page.Add(MenuItem.Button(() => Loc.Get("menu.back"), panel.Pop));
            return page;
        }

        public static void ApplyDisplay()
        {
            if (Application.isEditor)
                return;
            Screen.fullScreenMode = S.fullscreen ? FullScreenMode.FullScreenWindow : FullScreenMode.Windowed;
        }

        public static MenuPage Controls(MenuPanel panel)
        {
            var page = new MenuPage { title = () => Loc.Get("controls.title"), body = () => Loc.Get("controls.text") };
            page.Add(MenuItem.Button(() => Loc.Get("menu.back"), panel.Pop));
            return page;
        }

        public static MenuPage Achievements(MenuPanel panel)
        {
            var page = new MenuPage
            {
                title = () => Loc.Get("ach.title"),
                body = () => Loc.Get("ach.progress", Meta.Achievements.Count, Meta.Achievements.All.Length),
                visibleRows = 8,
            };
            foreach (var id in Meta.Achievements.All)
            {
                string a = id;
                page.Add(new MenuItem
                {
                    label = () => Meta.Achievements.Has(a) ? Loc.Get($"ach.{a}.name") : Loc.Get($"ach.{a}.name"),
                    value = () => Meta.Achievements.Has(a) ? "*" : "",
                    description = () => (Meta.Achievements.Has(a) ? "" : Loc.Get("ach.locked") + " - ") + Loc.Get($"ach.{a}.desc"),
                    tint = () => Meta.Achievements.Has(a) ? UIKit.Gold : new Color(0.5f, 0.52f, 0.58f),
                });
            }
            page.Add(MenuItem.Button(() => Loc.Get("menu.back"), panel.Pop));
            return page;
        }

        public static MenuPage Cheats(MenuPanel panel)
        {
            bool inRun = RunManager.Instance != null;
            var page = new MenuPage { title = () => Loc.Get("cheats.title"), body = () => Loc.Get("cheats.warning") + (inRun ? "" : "\n" + Loc.Get("cheats.menu_only")) };
            page.Add(MenuItem.Option(() => Loc.Get("cheats.god"), () => Loc.Get(Meta.Cheats.GodMode ? "options.on" : "options.off"), _ => Meta.Cheats.SetGodMode(!Meta.Cheats.GodMode)));
            page.Add(MenuItem.Option(() => Loc.Get("cheats.onehit"), () => Loc.Get(Meta.Cheats.OneHitKills ? "options.on" : "options.off"), _ => Meta.Cheats.SetOneHitKills(!Meta.Cheats.OneHitKills)));
            page.Add(MenuItem.Option(() => Loc.Get("cheats.nocd"), () => Loc.Get(Meta.Cheats.NoCooldowns ? "options.on" : "options.off"), _ => Meta.Cheats.SetNoCooldowns(!Meta.Cheats.NoCooldowns)));
            page.Add(MenuItem.Button(() => Loc.Get("cheats.gold"), () =>
            {
                Meta.Cheats.Use();
                SaveSystem.Data.run.gold += 1000;
                GameHUD.Instance?.Toast(Loc.Get("cheats.done"), UIKit.Gold);
            }, null, () => inRun));
            page.Add(MenuItem.Button(() => Loc.Get("cheats.cells"), () =>
            {
                Meta.Cheats.Use();
                SaveSystem.Data.run.cells += 200;
                GameHUD.Instance?.Toast(Loc.Get("cheats.done"), UIKit.CellBlue);
            }, null, () => inRun));
            page.Add(MenuItem.Button(() => Loc.Get("cheats.full_heal"), () => RunManager.Instance.CheatFullHeal(), null, () => inRun));
            page.Add(MenuItem.Button(() => Loc.Get("cheats.reveal_map"), () => RunManager.Instance.CheatRevealMap(), null, () => inRun));
            page.Add(MenuItem.Button(() => Loc.Get("cheats.skip_biome"), () =>
            {
                panel.CloseAll();
                RunManager.Instance.CheatSkipBiome();
            }, null, () => inRun));
            page.Add(MenuItem.Button(() => Loc.Get("cheats.unlock_all"), () =>
            {
                if (SaveSystem.Data.run.active)
                    Meta.Cheats.Use();
                var db = ItemDatabase.Instance;
                if (db != null)
                    foreach (var item in db.items.Where(i => i != null && i.unlockCost > 0))
                        if (!SaveSystem.Data.meta.unlockedItems.Contains(item.id))
                            SaveSystem.Data.meta.unlockedItems.Add(item.id);
                SaveSystem.Save();
            }));
            page.Add(MenuItem.Button(() => Loc.Get("cheats.bosscells"), () =>
            {
                if (SaveSystem.Data.run.active)
                    Meta.Cheats.Use();
                SaveSystem.Data.meta.bossCellsUnlocked = Difficulty.MaxBossCells;
                SaveSystem.Save();
            }));
            page.Add(MenuItem.Button(() => Loc.Get("menu.back"), panel.Pop));
            return page;
        }
    }
}
