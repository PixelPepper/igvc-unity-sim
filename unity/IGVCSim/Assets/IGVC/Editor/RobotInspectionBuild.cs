using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Xml.Linq;
using IGVC;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

// Static description inspection only: no guessed articulation or physical controller.
public static class RobotInspectionBuild
{
    private const string Generated = "Assets/IGVC/GeneratedRobot";
    private static readonly CultureInfo Culture = CultureInfo.InvariantCulture;
    private static string Repository => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
    public static Vector3 RosVector(Vector3 value) => new Vector3(-value.y, value.z, value.x);
    public static Quaternion RosRotation(Vector3 rpy)
    {
        var ros = Quaternion.AngleAxis(rpy.z * Mathf.Rad2Deg, Vector3.forward)
            * Quaternion.AngleAxis(rpy.y * Mathf.Rad2Deg, Vector3.up)
            * Quaternion.AngleAxis(rpy.x * Mathf.Rad2Deg, Vector3.right);
        return new Quaternion(ros.y, -ros.z, -ros.x, ros.w);
    }
    private static Vector3 Vector(string text, Vector3 fallback)
    {
        if (string.IsNullOrWhiteSpace(text)) return fallback;
        var p = text.Split(new[] { ' ', '\t', '\n' }, StringSplitOptions.RemoveEmptyEntries);
        if (p.Length != 3) throw new InvalidDataException("Expected xyz/rpy triple");
        return new Vector3(float.Parse(p[0], Culture), float.Parse(p[1], Culture), float.Parse(p[2], Culture));
    }
    private static void Origin(Transform target, XElement origin)
    {
        target.localPosition = RosVector(Vector((string)origin?.Attribute("xyz"), Vector3.zero));
        target.localRotation = RosRotation(Vector((string)origin?.Attribute("rpy"), Vector3.zero));
    }
    private static void CheckFrames()
    {
        void Equal(Vector3 actual, Vector3 expected) { if ((actual - expected).magnitude > .00001f) throw new Exception("ROS/Unity frame conversion failed"); }
        Equal(RosVector(Vector3.right), Vector3.forward);
        Equal(RosVector(Vector3.up), Vector3.left);
        Equal(RosVector(Vector3.forward), Vector3.up);
        Equal(RosRotation(new Vector3(0, 0, Mathf.PI / 2)) * Vector3.forward, Vector3.left);
        Equal(RosRotation(new Vector3(Mathf.PI / 2, Mathf.PI / 2, 0)) * Vector3.up, Vector3.right);
    }
    private static Mesh ImportMesh(string source, string name)
    {
        using var reader = new BinaryReader(File.OpenRead(source));
        reader.ReadBytes(80); uint count = reader.ReadUInt32();
        if (reader.BaseStream.Length != 84L + count * 50L) throw new InvalidDataException("Only validated binary STL supported: " + source);
        var vertices = new List<Vector3>(); var normals = new List<Vector3>();
        var indices = new int[checked((int)count * 3)];
        var unique = new Dictionary<(Vector3 position, Vector3 normal), int>();
        Vector3 ReadVector() => new Vector3(reader.ReadSingle(), reader.ReadSingle(), reader.ReadSingle());
        for (int face = 0; face < count; face++)
        {
            Vector3 normal = RosVector(ReadVector()).normalized;
            var faceIndices = new int[3];
            for (int v = 0; v < 3; v++)
            {
                Vector3 position = RosVector(ReadVector());
                var key = (position, normal);
                if (!unique.TryGetValue(key, out int index))
                { index = vertices.Count; unique.Add(key, index); vertices.Add(position); normals.Add(normal); }
                faceIndices[v] = index;
            }
            // Reflection flips the cross product; swap once so it agrees with converted normals.
            indices[face * 3] = faceIndices[0]; indices[face * 3 + 1] = faceIndices[2]; indices[face * 3 + 2] = faceIndices[1];
            reader.ReadUInt16();
        }
        var mesh = new Mesh { name = name, indexFormat = IndexFormat.UInt32 };
        mesh.SetVertices(vertices); mesh.SetNormals(normals); mesh.triangles = indices; mesh.RecalculateBounds();
        string destination = Generated + "/" + name + ".asset";
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(destination);
        if (existing == null) AssetDatabase.CreateAsset(mesh, destination);
        else { EditorUtility.CopySerialized(mesh, existing); UnityEngine.Object.DestroyImmediate(mesh); mesh = existing; }
        return mesh;
    }
    [MenuItem("IGVC/Create Robot Inspection")]
    public static void CreateScene()
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var root = CreateRobot(false);
        RenderSettings.skybox = null; RenderSettings.ambientLight = new Color(.7f, .72f, .76f);
        var renderers = root.GetComponentsInChildren<MeshRenderer>();
        var bounds = renderers[0].bounds; foreach (var renderer in renderers.Skip(1)) bounds.Encapsulate(renderer.bounds);
        float groundOffset = -bounds.min.y;
        root.transform.position = Vector3.up * groundOffset;
        var center = bounds.center + Vector3.up * groundOffset;
        var floor = GameObject.CreatePrimitive(PrimitiveType.Plane); floor.name = "Metre-scale inspection floor";
        floor.transform.localScale = Vector3.one * .4f;
        var floorMaterial = AssetDatabase.LoadAssetAtPath<Material>(Generated + "/Floor.mat");
        if (floorMaterial == null) { floorMaterial = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(floorMaterial, Generated + "/Floor.mat"); }
        floorMaterial.color = new Color(.13f, .17f, .2f); floorMaterial.SetFloat("_Glossiness", .1f);
        EditorUtility.SetDirty(floorMaterial);
        floor.GetComponent<Renderer>().sharedMaterial = floorMaterial;
        var sun = new GameObject("Sun").AddComponent<Light>(); sun.type = LightType.Directional;
        sun.intensity = .85f; sun.transform.rotation = Quaternion.Euler(50, -30, 0);
        var camera = new GameObject("Inspection Camera").AddComponent<Camera>();
        camera.transform.position = center + new Vector3(1.6f, 1.0f, 1.6f); camera.transform.LookAt(center);
        camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = new Color(.07f, .1f, .14f);
        long triangles = renderers.Sum(r => (long)r.GetComponent<MeshFilter>().sharedMesh.triangles.Length / 3);
        root.AddComponent<RobotInspectionView>().Configure(center, triangles, groundOffset, camera);
        EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), Generated + "/RobotInspection.unity");
        AssetDatabase.SaveAssets();
        string report = Path.Combine(Repository, "artifacts/checks/robot-unity-import.json");
        Directory.CreateDirectory(Path.GetDirectoryName(report));
        File.WriteAllText(report, $"{{\"visuals\":{renderers.Length},\"triangles\":{triangles},\"frame_checks_passed\":5,\"ground_offset_m\":{groundOffset.ToString("R", Culture)},\"mode\":\"static_inspection\"}}");
    }
    public static GameObject CreateRobot(bool simplified)
    {
        CheckFrames();
        var package = Path.GetFullPath(Path.Combine(Repository, "ros2/src/igvc_description"));
        var document = XDocument.Load(Path.Combine(package, "urdf/r3_a.urdf"));
        var robot = document.Root;
        if (robot?.Name.LocalName != "robot") throw new InvalidDataException("Expanded robot URDF missing");
        Directory.CreateDirectory(Generated); AssetDatabase.Refresh();
        var root = new GameObject("R3-a description (uncalibrated CAD)");
        var links = robot.Elements("link").ToDictionary(x => (string)x.Attribute("name"), x => new GameObject((string)x.Attribute("name")).transform);
        foreach (var link in links.Values) link.SetParent(root.transform, false);
        foreach (var joint in robot.Elements("joint"))
        {
            var child = links[(string)joint.Element("child").Attribute("link")];
            child.SetParent(links[(string)joint.Element("parent").Attribute("link")], false);
            Origin(child, joint.Element("origin"));
        }
        var material = new Material(Shader.Find("Standard")) { color = new Color(.65f, .7f, .75f) };
        string materialPath = Generated + "/Robot.mat";
        var savedMaterial = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
        if (savedMaterial == null) { AssetDatabase.CreateAsset(material, materialPath); savedMaterial = material; }
        else { EditorUtility.CopySerialized(material, savedMaterial); UnityEngine.Object.DestroyImmediate(material); }
        long triangles = 0;
        foreach (var link in robot.Elements("link"))
        foreach (var visual in link.Elements("visual"))
        {
            var reference = visual.Element("geometry")?.Element("mesh");
            if (reference == null) throw new InvalidDataException("Inspection importer currently requires mesh visuals");
            var uri = (string)reference.Attribute("filename");
            const string prefix = "package://igvc_description/";
            if (uri == null || !uri.StartsWith(prefix, StringComparison.Ordinal)) throw new InvalidDataException("Unexpected mesh package");
            string source = Path.GetFullPath(Path.Combine(package, uri.Substring(prefix.Length)));
            if (!source.StartsWith(package + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Mesh escapes package");
            string name = (string)link.Attribute("name");
            if (simplified && uri.StartsWith(prefix + "meshes/visual/", StringComparison.Ordinal))
                source = Path.Combine(package, "meshes/simplified", Path.GetFileName(source));
            if (simplified && uri.EndsWith("/base_static_source_basis.stl", StringComparison.Ordinal))
                source = Path.Combine(package, "meshes/camera_mount/base_static_source_basis_simplified.stl");
            string detail = (string)visual.Attribute("name") ?? "body";
            var mesh = ImportMesh(source, name + "_" + detail + (simplified ? "_simplified" : ""));
            triangles += mesh.triangles.Length / 3;
            var view = new GameObject(name + " visual"); view.transform.SetParent(links[name], false);
            Origin(view.transform, visual.Element("origin"));
            var scale = Vector((string)reference.Attribute("scale"), Vector3.one);
            view.transform.localScale = new Vector3(scale.y, scale.z, scale.x);
            view.AddComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = view.AddComponent<MeshRenderer>();
            renderer.sharedMaterial = savedMaterial;
            if (name == "lidar_link" || name == "camera_link")
            {
                string lidarMaterialPath = Generated + "/" + name + "_" + detail + ".mat";
                var lidarMaterial = AssetDatabase.LoadAssetAtPath<Material>(lidarMaterialPath);
                if (lidarMaterial == null) { lidarMaterial = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(lidarMaterial, lidarMaterialPath); }
                lidarMaterial.color = detail == "lens_rings" ? new Color(.3f, .35f, .4f)
                    : detail == "lens_glass" ? new Color(.03f, .08f, .14f) : new Color(.055f, .065f, .07f);
                lidarMaterial.SetFloat("_Glossiness", detail == "body" ? .25f : .7f);
                EditorUtility.SetDirty(lidarMaterial); renderer.sharedMaterial = lidarMaterial;
            }
        }
        if (simplified && triangles > 250000) throw new InvalidDataException("Robot plus sensors visual triangle budget exceeded");
        return root;
    }
    public static void Build()
    {
        CreateScene();
        Directory.CreateDirectory(Path.Combine(Repository, "artifacts/build-robot"));
        var result = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { Generated + "/RobotInspection.unity" },
            locationPathName = Path.Combine(Repository, "artifacts/build-robot/R3aInspection.exe"),
            target = BuildTarget.StandaloneWindows64, options = BuildOptions.Development });
        if (result.summary.result != BuildResult.Succeeded) throw new Exception("Robot inspection build failed");
        Debug.Log("IGVC_ROBOT_BUILD_OK");
    }
}
