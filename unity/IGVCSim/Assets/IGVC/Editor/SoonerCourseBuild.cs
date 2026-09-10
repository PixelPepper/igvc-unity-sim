using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

// Imports only the saved environment. Robot motion and ROS authority stay with R3-a.
public static class SoonerCourseBuild
{
    private const string Source = "Assets/IGVC/External/SoonerAutoNav/IGVC_2026_AutoNav.unity";
    private const string ScenePath = "Assets/IGVC/GeneratedRobot/SoonerAutoNav.unity";

    [MenuItem("IGVC/Create Sooner AutoNav Course")]
    public static void CreateScene()
    {
        if (!File.Exists(Source)) throw new Exception("Run tools/import_sooner_course.py first.");
        R3aDriveBuild.CreateScene();
        Directory.CreateDirectory("Assets/Resources");
        if (AssetDatabase.LoadAssetAtPath<Material>("Assets/Resources/IGVCVariantPalette.mat")==null)
            AssetDatabase.CreateAsset(new Material(Shader.Find("Unlit/Color")),"Assets/Resources/IGVCVariantPalette.mat");
        PlayerSettings.productName = "IGVC R3-a AutoNav";
        var destination = SceneManager.GetActiveScene();
        foreach (var root in destination.GetRootGameObjects())
            if (root.name == "Test Pad" || root.name == "Calibration Wall" || root.name.EndsWith("Marker") || root.name.StartsWith("Grid "))
                UnityEngine.Object.DestroyImmediate(root);

        var imported = EditorSceneManager.OpenScene(Source, OpenSceneMode.Additive);
        var environment = imported.GetRootGameObjects().Single(g => g.name == "#Environment");
        SceneManager.MoveGameObjectToScene(environment, destination);
        EditorSceneManager.CloseScene(imported, true);
        SceneManager.SetActiveScene(destination);
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(.35f, .38f, .42f);
        RenderSettings.reflectionIntensity = 0;
        GameObject.Find("Sun").GetComponent<Light>().intensity = .9f;
        environment.name = "SoonerRobotics AutoNav 2026 (local reference)";
        // Preserve source metre scale/layout; express the source robot spawn in our odom frame.
        // Source spawn (-2.61, -20.57), heading +90 Unity degrees. Ground datum is y=-.001.
        var alignment = new GameObject("Course frame (source spawn to odom origin)").transform;
        environment.transform.SetParent(alignment, true);
        alignment.rotation = Quaternion.Euler(0, -90, 0);
        alignment.position = -(alignment.rotation * new Vector3(-2.61f, -.001f, -20.57f));

        var reference = environment.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "Course Reference Size");
        if (reference != null) UnityEngine.Object.DestroyImmediate(reference.gameObject);
        var materials = new System.Collections.Generic.Dictionary<Material, Material>();
        foreach (var renderer in environment.GetComponentsInChildren<MeshRenderer>(true))
        {
            renderer.gameObject.layer = 0;
            renderer.sharedMaterials = renderer.sharedMaterials.Select(m => ConvertMaterial(m, materials)).ToArray();
            var filter = renderer.GetComponent<MeshFilter>();
            if (filter == null || filter.sharedMesh == null) throw new Exception("Missing course mesh: " + renderer.name);
            // Saved FBX barrels have no collision shapes; add static mesh shapes for LaserScan.
            if (renderer.GetComponent<Collider>() == null && renderer.name != "RoadNetworkBuilder")
                renderer.gameObject.AddComponent<MeshCollider>().sharedMesh = filter.sharedMesh;
        }
        foreach (var t in environment.GetComponentsInChildren<Transform>(true))
            if (GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject) != 0)
                throw new Exception("Missing imported script: " + t.name);
        var road = environment.GetComponentsInChildren<MeshFilter>().Single(f => f.name == "RoadNetworkBuilder");
        UnityEngine.Object.FindFirstObjectByType<IGVC.TransportProbe>().ConfigureLaneGuard(CourseLaneBuild.Add(road));
        if (road.sharedMesh.vertexCount != 2400) throw new Exception("Unexpected baked course road geometry");
        var overview = GameObject.Find("Overview Camera").GetComponent<Camera>();
        var bounds = road.GetComponent<Renderer>().bounds;
        overview.transform.position = bounds.center + new Vector3(28, 44, -32);
        overview.transform.LookAt(bounds.center);
        overview.farClipPlane = 250;
        overview.gameObject.AddComponent<IGVC.SpectatorCamera>().Configure(
            GameObject.Find("R3-a kinematic oracle").transform, overview.transform.position, bounds.center);
        EditorSceneManager.SaveScene(destination, ScenePath);
        AssetDatabase.SaveAssets();
        Physics.SyncTransforms();
        if (!Physics.Raycast(new Vector3(0, 2, 0), Vector3.down, out var ground, 4))
            throw new Exception("No course ground below R3-a spawn");
        if (Mathf.Abs(ground.point.y) > .02f) throw new Exception("Course spawn ground datum mismatch");
        var evidence = new Evidence { roadVertices = road.sharedMesh.vertexCount,
            meshRenderers = environment.GetComponentsInChildren<MeshRenderer>(true).Length,
            colliders = environment.GetComponentsInChildren<Collider>(true).Length,
            roadBoundsCenter = bounds.center, roadBoundsSize = bounds.size, spawnGroundY = ground.point.y };
        File.WriteAllText(Artifact("sooner-course-import.json"), JsonUtility.ToJson(evidence, true));
        Capture(overview, "sooner-course-overview.png");
        overview.transform.position = new Vector3(3, 2.6f, -4);
        overview.transform.LookAt(new Vector3(0, .5f, 1));
        Capture(overview, "sooner-course-spawn.png");
        Debug.Log("IGVC_SOONER_COURSE_IMPORT_OK " + JsonUtility.ToJson(evidence));
    }

    public static void Build()
    {
        CourseRampChecks.Run();
        CreateScene();
        // Restore saved whole-course view in the player.
        EditorSceneManager.OpenScene(ScenePath);
        var savedRoad = GameObject.Find("RoadNetworkBuilder").GetComponent<MeshFilter>().sharedMesh;
        if (savedRoad == null || savedRoad.vertexCount != 2400)
            throw new Exception("Baked road mesh lost during scene serialization");
        R3aDriveBuild.BuildScene(ScenePath, "build-course/IGVCCourse.exe");
        Debug.Log("IGVC_SOONER_COURSE_BUILD_OK");
    }

    private static Material ConvertMaterial(Material source, System.Collections.Generic.Dictionary<Material, Material> cache)
    {
        if (source == null) throw new Exception("Missing source course material");
        if (cache.TryGetValue(source, out var existing)) return existing;
        // Read saved URP properties through serialization even when its shader is unavailable.
        var serialized = new SerializedObject(source);
        var props = serialized.FindProperty("m_SavedProperties");
        Color color = source.HasProperty("_Color") ? source.color : Color.white;
        Texture texture = null; Vector2 scale = Vector2.one, offset = Vector2.zero;
        var colors = props.FindPropertyRelative("m_Colors");
        for (int i = 0; i < colors.arraySize; i++)
        {
            var pair = colors.GetArrayElementAtIndex(i);
            if (pair.FindPropertyRelative("first").stringValue == "_BaseColor") color = pair.FindPropertyRelative("second").colorValue;
        }
        var textures = props.FindPropertyRelative("m_TexEnvs");
        for (int i = 0; i < textures.arraySize; i++)
        {
            var pair = textures.GetArrayElementAtIndex(i);
            var key = pair.FindPropertyRelative("first").stringValue;
            var value = pair.FindPropertyRelative("second");
            if ((key == "_BaseMap" || key == "_MainTex") && value.FindPropertyRelative("m_Texture").objectReferenceValue != null)
            {
                texture = (Texture)value.FindPropertyRelative("m_Texture").objectReferenceValue;
                scale = value.FindPropertyRelative("m_Scale").vector2Value;
                offset = value.FindPropertyRelative("m_Offset").vector2Value;
            }
        }
        var material = new Material(Shader.Find(source.name.Contains("Lane") ? "Unlit/Transparent" : "Standard"));
        material.name = source.name + " (Built-in)";
        material.color = color; material.mainTexture = texture; material.mainTextureScale = scale; material.mainTextureOffset = offset;
        if (material.HasProperty("_Glossiness")) material.SetFloat("_Glossiness", .1f);
        string folder = "Assets/IGVC/GeneratedRobot/CourseMaterials";
        Directory.CreateDirectory(folder);
        string path = folder + "/" + source.name.Replace('/', '_') + ".mat";
        var previous = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (previous == null) AssetDatabase.CreateAsset(material, path);
        else { EditorUtility.CopySerialized(material, previous); UnityEngine.Object.DestroyImmediate(material); material = previous; }
        cache.Add(source, material);
        return material;
    }

    private static string Artifact(string name) => Path.GetFullPath(Path.Combine(Application.dataPath, "../../../artifacts/checks", name));
    private static void Capture(Camera camera, string name)
    {
        var target = new RenderTexture(1280, 800, 24);
        var pixels = new Texture2D(1280, 800, TextureFormat.RGB24, false);
        var previous = RenderTexture.active;
        try { camera.targetTexture = target; camera.Render(); RenderTexture.active = target;
            pixels.ReadPixels(new Rect(0, 0, 1280, 800), 0, 0); pixels.Apply(); File.WriteAllBytes(Artifact(name), pixels.EncodeToPNG()); }
        finally { camera.targetTexture = null; RenderTexture.active = previous; target.Release();
            UnityEngine.Object.DestroyImmediate(target); UnityEngine.Object.DestroyImmediate(pixels); }
    }
    [Serializable] private class Evidence
    {
        public int roadVertices, meshRenderers, colliders;
        public Vector3 roadBoundsCenter, roadBoundsSize;
        public float spawnGroundY;
    }
}
