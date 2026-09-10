using System;
using System.IO;
using IGVC;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class ProbeBuild
{
    [MenuItem("IGVC/Create Transport Probe")]
    public static void CreateScene()
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        PlayerSettings.SetScriptingDefineSymbols(NamedBuildTarget.Standalone, "ROS2");
        PlayerSettings.companyName = "IGVC";
        PlayerSettings.productName = "IGVC Transport Probe";
        PlayerSettings.runInBackground = true;
        PlayerSettings.defaultScreenWidth = 1280;
        PlayerSettings.defaultScreenHeight = 800;
        PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
        EditorSettings.serializationMode = SerializationMode.ForceText;
        RenderSettings.ambientLight = new Color(0.6f, 0.65f, 0.7f);
        RenderSettings.skybox = null;
        var light = new GameObject("Sun").AddComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 1.3f;
        light.transform.rotation = Quaternion.Euler(50, -35, 0);
        Box("Test Pad", new Vector3(0, -0.1f, 3), new Vector3(14, 0.2f, 18), new Color(0.19f, 0.25f, 0.22f));
        Box("Calibration Wall", new Vector3(0, 1, 5), new Vector3(6, 2, 0.2f), new Color(0.65f, 0.68f, 0.7f));
        Box("Left Marker", new Vector3(-2, 0.65f, 3), new Vector3(0.6f, 1.3f, 0.6f), new Color(0.95f, 0.4f, 0.12f));
        Box("Right Marker", new Vector3(2, 0.4f, 2), new Vector3(0.7f, 0.8f, 0.7f), new Color(0.2f, 0.5f, 0.9f));
        for (int i = -5; i <= 5; i++)
            Box("Grid " + i, new Vector3(i, 0.005f, 3), new Vector3(0.015f, 0.01f, 16), new Color(0.4f, 0.45f, 0.4f));
        var body = Box("Ideal Probe Body", new Vector3(0, 0.35f, 0), new Vector3(0.7f, 0.5f, 1), new Color(0.05f, 0.65f, 0.8f));
        body.layer = 2; // Exclude the placeholder robot from the scan raycast mask.
        var sensor = new GameObject("RGB Probe Camera").AddComponent<Camera>();
        sensor.transform.SetParent(body.transform, false);
        sensor.transform.localPosition = new Vector3(0, 0.7f, 0.45f);
        sensor.transform.localScale = Vector3.one;
        sensor.fieldOfView = 54;
        sensor.clearFlags = CameraClearFlags.SolidColor;
        sensor.backgroundColor = new Color(0.45f, 0.65f, 0.85f);
        var overview = new GameObject("Overview Camera").AddComponent<Camera>();
        overview.transform.position = new Vector3(8, 8, -8);
        overview.transform.LookAt(new Vector3(0, 0, 2));
        overview.clearFlags = CameraClearFlags.SolidColor;
        overview.backgroundColor = new Color(0.08f, 0.12f, 0.17f);
        new GameObject("Transport Probe").AddComponent<TransportProbe>().Configure(body.transform, sensor);
        Directory.CreateDirectory("Assets/IGVC/Scenes");
        EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), "Assets/IGVC/Scenes/TransportProbe.unity");
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene("Assets/IGVC/Scenes/TransportProbe.unity", true) };
        AssetDatabase.SaveAssets();
    }

    public static void Build()
    {
        CreateScene();
        string output = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../artifacts/build/IGVCProbe.exe"));
        Directory.CreateDirectory(Path.GetDirectoryName(output));
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes = new[] { "Assets/IGVC/Scenes/TransportProbe.unity" }, locationPathName = output,
            target = BuildTarget.StandaloneWindows64, options = BuildOptions.Development });
        if (report.summary.result != BuildResult.Succeeded) throw new Exception("Probe player build failed: " + report.summary.result);
        Debug.Log("IGVC_BUILD_OK " + output);
    }

    private static GameObject Box(string name, Vector3 position, Vector3 scale, Color color)
    {
        var box = GameObject.CreatePrimitive(PrimitiveType.Cube);
        box.name = name; box.transform.position = position; box.transform.localScale = scale;
        var material = new Material(Shader.Find("Standard")) { color = color };
        Directory.CreateDirectory("Assets/IGVC/Materials");
        string path = "Assets/IGVC/Materials/" + name.Replace(" ", "_") + ".mat";
        var existing = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (existing == null) { AssetDatabase.CreateAsset(material, path); existing = material; }
        else UnityEngine.Object.DestroyImmediate(material);
        box.GetComponent<Renderer>().sharedMaterial = existing;
        return box;
    }
}
