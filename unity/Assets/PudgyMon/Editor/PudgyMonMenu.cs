using UnityEditor;
using UnityEditor.SceneManagement;

namespace PudgyMon.EditorTools
{
    static class PudgyMonMenu
    {
        const string ScenePath = "Assets/PudgyMon/Scenes/Nest.unity";

        [MenuItem("PudgyMon/Open Nest Scene")]
        static void OpenNest()
        {
            if (EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
                EditorSceneManager.OpenScene(ScenePath);
        }

        [MenuItem("PudgyMon/Play Nest")]
        static void PlayNest()
        {
            OpenNest();
            EditorApplication.isPlaying = true;
        }
    }

    [InitializeOnLoad]
    static class PudgyMonProjectSetup
    {
        static PudgyMonProjectSetup()
        {
            EditorApplication.delayCall += EnsureBuildScene;
        }

        static void EnsureBuildScene()
        {
            PlayerSettings.companyName = "PudgyMon";
            PlayerSettings.productName = "PudgyMon Party Saga";
            PlayerSettings.bundleVersion = "0.1.0";

            const string scenePath = "Assets/PudgyMon/Scenes/Nest.unity";
            var scenes = EditorBuildSettings.scenes;
            foreach (var s in scenes)
            {
                if (s.path == scenePath)
                    return;
            }

            var list = new EditorBuildSettingsScene[scenes.Length + 1];
            scenes.CopyTo(list, 0);
            list[scenes.Length] = new EditorBuildSettingsScene(scenePath, true);
            EditorBuildSettings.scenes = list;
        }
    }
}
