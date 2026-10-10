using System.Collections;
using DeadCells.Core;
using DeadCells.Meta;
using DeadCells.Run;
using UnityEngine;

namespace DeadCells.UI
{
    /// <summary>
    /// Title screen: Continue / New Game (difficulty + Boss Cells) /
    /// Achievements / Options / Cheats / Quit over a live diorama of the
    /// Oubliette. Typing the cheat word here unlocks the cheat menu.
    /// </summary>
    public class MainMenu : MonoBehaviour
    {
        public CharacterAnimator hero;

        MenuPanel menu;
        UILabel title, subtitle, info, toast;
        float toastUntil;
        BaseDifficulty newDifficulty = BaseDifficulty.Normal;
        int newBossCells;

        static SaveData Data => SaveSystem.Data;
        string version = "";

        void Start()
        {
            Time.timeScale = 1f;
            GamePause.Set(false);
            GameInput.GameplayEnabled = true;
            Loc.Current = Data.settings.language;
            version = Changelog.Latest;
            MenuPages.ApplyDisplay();
            Audio.Music.Play("music.menu", 1.2f);
            Audio.Music.Ambience(null, 1.2f);

            var canvas = UIKit.Canvas("TitleCanvas", 150, transform);
            var root = canvas.transform;
            title = UIKit.Label("Title", root, new Vector2(1f, 1f), new Vector2(-90f, -90f), new Vector2(1100f, 90f), TextAnchor.MiddleRight, new Color(0.92f, 0.86f, 1f), 9f, UILabel.Style.Pixel, 30, Vector2.one);
            title.SetKey("game.title");
            subtitle = UIKit.Label("Subtitle", root, new Vector2(1f, 1f), new Vector2(-90f, -185f), new Vector2(1100f, 60f), TextAnchor.MiddleRight, new Color(0.7f, 0.45f, 1f), 5f, UILabel.Style.Pixel, 30, Vector2.one);
            subtitle.SetKey("game.subtitle");
            info = UIKit.Label("Info", root, new Vector2(1f, 0f), new Vector2(-90f, 50f), new Vector2(1100f, 30f), TextAnchor.MiddleRight, new Color(0.55f, 0.6f, 0.68f), 2f, UILabel.Style.Pixel, 30, new Vector2(1f, 0f));
            toast = UIKit.Label("Toast", root, new Vector2(1f, 0f), new Vector2(-90f, 100f), new Vector2(1100f, 40f), TextAnchor.MiddleRight, UIKit.Gold, 3f, UILabel.Style.Pixel, 30, new Vector2(1f, 0f));

            menu = MenuPanel.Create("MainMenuPanel", 200, transform);
            menu.dimBackground = false;
            menu.Push(RootPage());
            MenuInput.ClearTyped();
            hero?.Restart("Idle", 0f);
            if (hero != null)
                Outfits.Apply(hero.gameObject);

            if (AutoplayDirector.Active)
                StartCoroutine(Autoplay());
        }

        MenuPage RootPage()
        {
            var page = new MenuPage { title = () => "", canBack = false };
            page.Add(MenuItem.Button(() => Loc.Get("menu.continue"), Continue, ContinueInfo, () => Data.run.active));
            page.Add(MenuItem.Button(() => Loc.Get("menu.new_game"), () => menu.Push(NewGamePage())));
            page.Add(MenuItem.Button(() => Loc.Get("menu.achievements"), () => menu.Push(MenuPages.Achievements(menu))));
            page.Add(MenuItem.Button(() => Loc.Get("menu.changelog"), () => menu.Push(MenuPages.Changelog(menu))));
            page.Add(MenuItem.Button(() => Loc.Get("menu.options"), () => menu.Push(MenuPages.Options(menu))));
            page.Add(MenuItem.Button(() => Loc.Get("menu.cheats"), () => menu.Push(MenuPages.Cheats(menu)), () => Loc.Get("menu.cheat_code_hint"), () => Cheats.Unlocked));
            page.Add(MenuItem.Button(() => Loc.Get("menu.quit"), Quit));
            if (Data.run.active)
                page.selected = 0;
            else
                page.selected = 1;
            return page;
        }

        string ContinueInfo()
        {
            var run = Data.run;
            if (!run.active)
                return "";
            string area = run.inPassage ? Loc.Get("biome.passage.name") : AreaName(run.biome);
            return Loc.Get("menu.continue_info", area, Difficulty.Label(run.difficulty), UIKit.FormatTime(run.time));
        }

        static string AreaName(int biome)
        {
            string[] keys = { "oubliette", "promenade", "ossuary", "stilt", "lung" };
            return Loc.Get($"biome.{keys[Mathf.Clamp(biome, 0, keys.Length - 1)]}.name");
        }

        MenuPage NewGamePage()
        {
            newBossCells = Mathf.Min(newBossCells, Data.meta.bossCellsUnlocked);
            var page = new MenuPage { title = () => Loc.Get("newgame.title") };
            page.Add(MenuItem.Option(() => Loc.Get("newgame.difficulty"), () => Difficulty.Label(newDifficulty), d =>
            {
                newDifficulty = (BaseDifficulty)(((int)newDifficulty + d + 3) % 3);
            }, () => Loc.Get("difficulty." + newDifficulty.ToString().ToLowerInvariant() + ".desc")));
            page.Add(new MenuItem
            {
                label = () => Loc.Get("newgame.bosscells"),
                value = () => Data.meta.bossCellsUnlocked > 0 ? newBossCells.ToString() : "-",
                change = d =>
                {
                    int max = Data.meta.bossCellsUnlocked;
                    if (max > 0)
                        newBossCells = (newBossCells + d + max + 1) % (max + 1);
                },
                confirm = () =>
                {
                    int max = Data.meta.bossCellsUnlocked;
                    if (max > 0)
                        newBossCells = (newBossCells + 1) % (max + 1);
                },
                description = () => Data.meta.bossCellsUnlocked <= 0 ? Loc.Get("newgame.bosscells_locked") : BossCellText(),
                enabled = () => Data.meta.bossCellsUnlocked > 0,
            });
            page.Add(MenuItem.Button(() => Loc.Get("newgame.start"), () =>
            {
                if (Data.run.active)
                    menu.Confirm(() => Loc.Get("newgame.overwrite"), Begin);
                else
                    Begin();
            }, () => Data.run.active ? Loc.Get("newgame.overwrite") : ""));
            page.Add(MenuItem.Button(() => Loc.Get("menu.back"), menu.Pop));
            return page;
        }

        string BossCellText()
        {
            int bc = newBossCells;
            string refill = bc switch { 0 => "100", 1 => newDifficulty == BaseDifficulty.Hard ? "50" : "100", 2 => "50", _ => "0" };
            return Loc.Get("bosscells.desc", bc, 15 * bc, 20 * bc, refill);
        }

        void Begin()
        {
            RunManager.NewRun(newDifficulty, newBossCells);
            RunManager.PrologueRequested = !Data.settings.skipIntro;
            SceneFlow.LoadGame();
        }

        void Continue()
        {
            if (Data.run.active)
                SceneFlow.LoadGame();
        }

        void Quit()
        {
            SaveSystem.Save();
            Application.Quit();
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#endif
        }

        void Update()
        {
            var s = Data.stats;
            info.Text = Loc.Get("menu.save_info", s.runs, s.wins, s.deaths, Achievements.Count, Achievements.All.Length) + "   v" + version;
            if (!Cheats.Unlocked && MenuInput.Typed.EndsWith(Cheats.Code))
            {
                Cheats.UnlockMenu();
                MenuInput.ClearTyped();
                toast.Text = Loc.Get("menu.cheats_unlocked");
                toastUntil = Time.unscaledTime + 3f;
            }
            toast.gameObject.SetActive(Time.unscaledTime < toastUntil);
        }

        IEnumerator Autoplay()
        {
            var ap = AutoplayDirector.Instance;
            yield return new WaitForSecondsRealtime(1.5f);
            if (ap.captureMenu)
            {
                ap.Capture("menu_root");
                yield return new WaitForSecondsRealtime(0.5f);
                menu.Push(NewGamePage());
                yield return new WaitForSecondsRealtime(0.6f);
                ap.Capture("menu_newgame");
                menu.Pop();
                menu.Push(MenuPages.Options(menu));
                yield return new WaitForSecondsRealtime(0.6f);
                ap.Capture("menu_options");
                menu.Pop();
                menu.Push(MenuPages.Achievements(menu));
                yield return new WaitForSecondsRealtime(0.6f);
                ap.Capture("menu_achievements");
                menu.Pop();
                menu.Push(MenuPages.Changelog(menu));
                yield return new WaitForSecondsRealtime(0.6f);
                ap.Capture("menu_changelog");
                menu.Pop();
                menu.Push(MenuPages.Cheats(menu));
                yield return new WaitForSecondsRealtime(0.6f);
                ap.Capture("menu_cheats");
                menu.Pop();
                yield return new WaitForSecondsRealtime(0.3f);
            }
            ap.StartRun();
        }
    }
}
