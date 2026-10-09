using UnityEngine.SceneManagement;

namespace DeadCells.Run
{
    public static class SceneFlow
    {
        public const string MenuScene = "MainMenu";
        public const string GameScene = "Game";

        public static void LoadGame()
        {
            Core.GamePause.Set(false);
            SceneManager.LoadScene(GameScene);
        }

        public static void LoadMenu()
        {
            Core.GamePause.Set(false);
            SceneManager.LoadScene(MenuScene);
        }
    }
}
