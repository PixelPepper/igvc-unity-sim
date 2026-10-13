using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using IGVC;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

// Drivable scene for the accepted image-traced map (T-0090). Combines the existing R3-a robot/sensor/ROS
// scene (R3aDriveBuild.CreateScene) with the accepted ReferenceAutoNav2027 scene, unchanged in geometry,
// so the robot can be driven by the existing sensor-led stack. The whole map is translated so the centre of
// the NORTH start line (image px 960.5, 439) is the robot's odom origin; the robot heads north (Unity +z,
// ROS +x). No course geometry is given to autonomy: the lane guard is simulator truth only.
//   Build:   -executeMethod ReferenceDriveBuild.Build   (scene + checks + artifacts/build-reference-drive)
//   Scene:   -executeMethod ReferenceDriveBuild.CreateSceneOnly
public static class ReferenceDriveBuild
{
    public const string DriveScene = "Assets/IGVC/Scenes/ReferenceAutoNav2027Drive.unity";
    public const string ReferenceScene = "Assets/IGVC/Scenes/ReferenceAutoNav2027.unity";
    public const string PlayerOutput = "build-reference-drive/IGVCReferenceDrive.exe";
    public const string MapRootName = "Reference AutoNav 2027 (image-traced, uncertified)";
    public const float SpawnPx = 960.5f, SpawnPy = 439f;
    private const string MeshFolder = "Assets/IGVC/Realism/Meshes";
    public static string Repository => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));

    // Files that existing generators (ProbeBuild/R3aDriveBuild) rewrite; restored byte-for-byte afterwards.
    private static readonly string[] Protected = {
        "unity/IGVCSim/Assets/IGVC/Scenes/TransportProbe.unity",
        "unity/IGVCSim/ProjectSettings/EditorBuildSettings.asset",
        "unity/IGVCSim/ProjectSettings/ProjectSettings.asset",
        "unity/IGVCSim/ProjectSettings/EditorSettings.asset",
        "unity/IGVCSim/ProjectSettings/QualitySettings.asset",
        "unity/IGVCSim/ProjectSettings/GraphicsSettings.asset",
        "unity/IGVCSim/Assets/IGVC/GeneratedRobot/R3aDrive.unity",
        "artifacts/checks/lidar-unity-mount.json" };

    public static readonly Dictionary<string, Color> DrumColors = new Dictionary<string, Color> {
        { "Yellow", new Color(.98f, .72f, .12f) }, { "Red", new Color(.85f, .08f, .06f) },
        { "Green", new Color(.1f, .62f, .25f) }, { "Black", new Color(.05f, .05f, .05f) } };

    public static Vector2 Odom(Vector3 world) => new Vector2(world.z, -world.x);

    public static void Build() => Run(true);
    public static void CreateSceneOnly() => Run(false);

    private static void Run(bool player)
    {
        var saved = Protected.ToDictionary(p => p, p => { string f = Path.Combine(Repository, p); return File.Exists(f) ? File.ReadAllBytes(f) : null; });
        var restored = new List<string>();
        try
        {
            CreateScene();
            ReferenceDriveChecks.Run();
            if (player) { R3aDriveBuild.BuildScene(DriveScene, PlayerOutput); Debug.Log("IGVC_REFERENCE_DRIVE_BUILD_OK " + PlayerOutput); }
        }
        finally
        {
            foreach (var entry in saved)
            {
                string file = Path.Combine(Repository, entry.Key);
                byte[] now = File.Exists(file) ? File.ReadAllBytes(file) : null;
                if (entry.Value == null) { if (now != null) { File.Delete(file); if (File.Exists(file + ".meta")) File.Delete(file + ".meta"); restored.Add(entry.Key + " (removed; absent before)"); } }
                else if (now == null || !now.SequenceEqual(entry.Value)) { File.WriteAllBytes(file, entry.Value); restored.Add(entry.Key); }
            }
            string report = Path.Combine(Repository, "artifacts/agents/T-0090"); Directory.CreateDirectory(report);
            File.WriteAllText(Path.Combine(report, "protected-restore.json"),
                "{\"restored\": [" + string.Join(", ", restored.Select(r => "\"" + r.Replace("\\", "/") + "\"")) + "]}\n");
            AssetDatabase.Refresh();
        }
    }

    // Persist a mesh asset, rewriting an existing one through explicit Mesh APIs (keeps GUID, re-uploads GPU data).
    private static Mesh SaveMesh(Mesh mesh)
    {
        Directory.CreateDirectory(MeshFolder);
        string path = MeshFolder + "/" + mesh.name + ".asset";
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (existing == null) { mesh.UploadMeshData(false); AssetDatabase.CreateAsset(mesh, path); return mesh; }
        existing.Clear(); existing.indexFormat = mesh.indexFormat;
        existing.SetVertices(mesh.vertices); existing.SetNormals(mesh.normals); existing.SetUVs(0, mesh.uv);
        existing.subMeshCount = mesh.subMeshCount;
        for (int i = 0; i < mesh.subMeshCount; i++) existing.SetTriangles(mesh.GetTriangles(i), i);
        existing.RecalculateTangents(); existing.RecalculateBounds(); existing.UploadMeshData(false);
        EditorUtility.SetDirty(existing); UnityEngine.Object.DestroyImmediate(mesh);
        return existing;
    }

    private static void Destroy(GameObject item) { if (item != null) UnityEngine.Object.DestroyImmediate(item); }

    public static void CreateScene()
    {
        RealismAssets.ConfigureTextures();
        if (!File.Exists(Path.Combine(Repository, "unity/IGVCSim", ReferenceScene))) ReferenceMapBuild.CreateMenu();

        // 1. Existing robot scene: R3-a, sensors, TransportProbe, ROS. Remove the probe's test props/light.
        R3aDriveBuild.CreateScene();
        var active = SceneManager.GetActiveScene();
        foreach (var name in new[] { "Test Pad", "Calibration Wall", "Left Marker", "Right Marker", "Sun" }) Destroy(GameObject.Find(name));
        for (int i = -5; i <= 5; i++) Destroy(GameObject.Find("Grid " + i));
        var transport = UnityEngine.Object.FindFirstObjectByType<TransportProbe>() ?? throw new Exception("TransportProbe missing");
        var robot = GameObject.Find("R3-a kinematic oracle")?.transform ?? throw new Exception("R3-a robot missing");

        // 2. Accepted map, unchanged geometry; drop its diagram annotations, camera and lighting.
        var reference = EditorSceneManager.OpenScene(ReferenceScene, OpenSceneMode.Additive);
        SceneManager.MergeScenes(reference, active);
        var map = GameObject.Find(MapRootName)?.transform ?? throw new Exception("Reference map root missing");
        foreach (var name in new[] { "Annotations (EditorOnly)", "Overview camera", "Lighting" }) Destroy(map.Find(name)?.gameObject);
        foreach (var t in UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (t != null && (t.CompareTag("EditorOnly") || t.GetComponent<TextMesh>() != null)) Destroy(t.gameObject);

        // 3. North start line centre -> odom origin; heading north = Unity +z = robot forward.
        map.position = -ReferenceMapBuild.World(SpawnPx, SpawnPy);

        // 4. Realistic surfaces and detailed drums (colliders unchanged).
        var ground = map.Find("Asphalt/Asphalt ground (full image extent)") ?? throw new Exception("Ground missing");
        ground.GetComponent<Renderer>().sharedMaterial = RealismAssets.Asphalt(new Vector2(ground.localScale.x, ground.localScale.z));
        var white = RealismAssets.Lit("ReferenceTapeWhite", new Color(.9f, .9f, .88f), .25f);
        foreach (var r in map.Find("White tape (4 in, traced)").GetComponentsInChildren<Renderer>()) r.sharedMaterial = white;
        foreach (var r in map.Find("Start-finish lines").GetComponentsInChildren<Renderer>()) r.sharedMaterial = white;
        var rampMaterial = RealismAssets.Lit("ReferenceRamp", new Color(.55f, .55f, .53f), .15f);
        foreach (var r in map.Find("Ramp (traced rectangle, 0.30 m)").GetComponentsInChildren<Renderer>()) r.sharedMaterial = rampMaterial;
        var drumMesh = SaveMesh(RealisticObstacles.DrumMesh("ReferenceDrum", ReferenceMapBuild.DrumDiameter, ReferenceMapBuild.DrumHeight));
        var band = RealismAssets.Lit("ReferenceDrumBand", new Color(.95f, .95f, .93f), .8f);
        var tire = RealismAssets.Lit("ReferenceDrumBase", new Color(.035f, .035f, .035f), .15f);
        var bodies = DrumColors.ToDictionary(c => c.Key, c => RealismAssets.Lit("ReferenceDrum_" + c.Key, c.Value, .5f));
        foreach (Transform drum in map.Find("Drums (traced)"))
        {
            string colour = drum.name.Split(' ')[0];
            if (!bodies.ContainsKey(colour)) throw new Exception("Unknown drum colour: " + drum.name);
            drum.GetComponent<Renderer>().enabled = false;   // keep its collider; the visual child replaces it
            var visual = new GameObject("Drum visual"); visual.transform.SetParent(drum, false);
            Vector3 s = drum.localScale; visual.transform.localScale = new Vector3(1 / s.x, 1 / s.y, 1 / s.z);
            visual.AddComponent<MeshFilter>().sharedMesh = drumMesh;
            var renderer = visual.AddComponent<MeshRenderer>(); renderer.sharedMaterials = new[] { bodies[colour], band, tire };
        }

        // 5. Lighting: one soft-shadow sun; procedural sky; presets applied at runtime by ReferenceDriveConditions.
        var sun = new GameObject("Sun").AddComponent<Light>();
        sun.type = LightType.Directional; sun.shadows = LightShadows.Soft; sun.intensity = 1.2f; sun.transform.rotation = Quaternion.Euler(60, 200, 0);
        var sensor = robot.GetComponentInChildren<Camera>(true) ?? throw new Exception("Robot RGB camera missing");
        var overview = GameObject.Find("Overview Camera")?.GetComponent<Camera>() ?? throw new Exception("Overview camera missing");
        new GameObject("Reference drive conditions").AddComponent<ReferenceDriveConditions>().Configure(sun, RealismAssets.Sky(), new[] { sensor, overview });
        RenderSettings.fog = false;

        // 6. Spectator: follow/orbit from above the course centre.
        Vector3 centre = ground.position;
        overview.transform.position = centre + new Vector3(18, 34, -26); overview.transform.LookAt(centre); overview.farClipPlane = 250;
        overview.gameObject.AddComponent<SpectatorCamera>().Configure(robot, overview.transform.position, centre);

        // 7. Simulator-only lane guard from the two saved tape meshes (both painted edges), and terrain support.
        var guard = new GameObject("Reference lane guard (simulator only)").AddComponent<LaneBoundaryGuard>();
        var segments = new List<LaneBoundaryGuard.Segment>();
        foreach (var filter in map.Find("White tape (4 in, traced)").GetComponentsInChildren<MeshFilter>())
        {
            var v = filter.sharedMesh.vertices;
            for (int side = 0; side < 2; side++)
                for (int i = side; i + 2 < v.Length; i += 2)
                    segments.Add(new LaneBoundaryGuard.Segment { a = Odom(filter.transform.TransformPoint(v[i])), b = Odom(filter.transform.TransformPoint(v[i + 2])) });
        }
        guard.Configure(segments.ToArray()); guard.Clear();
        if (!guard.CanOccupy(0, 0, 0)) throw new Exception("Robot footprint at the north start line overlaps traced tape");
        transport.ConfigureLaneGuard(guard);
        var supports = new List<Collider> { ground.GetComponent<Collider>() };
        foreach (var part in new[] { "Ascent", "Deck", "Descent" }) supports.Add(map.Find("Ramp (traced rectangle, 0.30 m)/" + part).GetComponent<Collider>());
        if (supports.Any(c => c == null)) throw new Exception("Support collider missing");
        transport.ConfigureTerrain(supports.ToArray());
        EditorUtility.SetDirty(transport);

        Physics.SyncTransforms();
        if (!Physics.Raycast(new Vector3(0, 2, 0), Vector3.down, out var hit, 4) || Mathf.Abs(hit.point.y) > .02f)
            throw new Exception("No ground at the odom origin");
        if (!EditorSceneManager.SaveScene(active, DriveScene)) throw new Exception("Drive scene save failed");
        AssetDatabase.SaveAssets();
    }
}
