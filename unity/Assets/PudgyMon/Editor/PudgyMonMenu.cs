using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
#if PUDGYMON_URP
using UnityEngine.Rendering.Universal;
#endif

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
        const string ScenePath = "Assets/PudgyMon/Scenes/Nest.unity";
        const string SettingsDir = "Assets/PudgyMon/Settings";
        const string RendererPath = SettingsDir + "/PudgyMonRenderer.asset";
        const string PipelinePath = SettingsDir + "/PudgyMonURP.asset";

        static PudgyMonProjectSetup()
        {
            EditorApplication.delayCall += EnsureProject;
        }

        static void EnsureProject()
        {
            PlayerSettings.companyName = "PudgyMon";
            PlayerSettings.productName = "PudgyMon Party Saga";
            PlayerSettings.bundleVersion = "0.1.0";
            EnsureBuildScene();
            EnsureUrp();
        }

        static void EnsureBuildScene()
        {
            var scenes = EditorBuildSettings.scenes;
            foreach (var s in scenes)
            {
                if (s.path == ScenePath)
                    return;
            }

            var list = new EditorBuildSettingsScene[scenes.Length + 1];
            scenes.CopyTo(list, 0);
            list[scenes.Length] = new EditorBuildSettingsScene(ScenePath, true);
            EditorBuildSettings.scenes = list;
        }

        static void EnsureUrp()
        {
#if PUDGYMON_URP
            if (!Directory.Exists(SettingsDir))
                Directory.CreateDirectory(SettingsDir);

            var renderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(RendererPath);
            if (renderer == null)
            {
                renderer = ScriptableObject.CreateInstance<UniversalRendererData>();
                AssetDatabase.CreateAsset(renderer, RendererPath);
            }

            var pipeline = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(PipelinePath);
            if (pipeline == null)
            {
                pipeline = UniversalRenderPipelineAsset.Create(renderer);
                AssetDatabase.CreateAsset(pipeline, PipelinePath);
            }

            if (GraphicsSettings.defaultRenderPipeline != pipeline)
                GraphicsSettings.defaultRenderPipeline = pipeline;
            if (QualitySettings.renderPipeline != pipeline)
                QualitySettings.renderPipeline = pipeline;

            EditorUtility.SetDirty(pipeline);
            EditorUtility.SetDirty(renderer);
            AssetDatabase.SaveAssets();
#endif
        }
    }
}
