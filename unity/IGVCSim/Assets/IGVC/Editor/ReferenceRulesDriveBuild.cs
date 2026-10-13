using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using IGVC;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

// Drivable scene for the PROPOSED rule-dimensioned reference course (T-0091, selected variant "rules-485").
// Geometry comes ONLY from the root-pinned authoring input artifacts/agents/T-0091/unity-input.json, produced by
// tools/reference_rules_geometry.py (field metres, x east, y north). It is build-time authoring data: never
// copied into Resources/StreamingAssets or player data, and never given to autonomy. The existing R3-a robot
// scene (R3aDriveBuild.CreateScene) provides the robot, sensors and TransportProbe; the course root is
// translated so the north start-line centre is the odom origin with the robot heading north (Unity +z, ROS +x).
// Physical sizes (93 drums 0.597 x 1.008 m, 4 in tape, 0.30 m ramp) are taken from the input and checked.
// T-0089/T-0090 sources, scenes, players and their materials are never modified: materials are created or
// cloned into GeneratedReferenceRules; textures are shared read-only.
//   Build:   -executeMethod ReferenceRulesDriveBuild.Build   (scene + checks + artifacts/build-reference-rules)
//   Scene:   -executeMethod ReferenceRulesDriveBuild.CreateSceneOnly
public static class ReferenceRulesDriveBuild
{
    public const string DriveScene = "Assets/IGVC/Scenes/ReferenceRulesAutoNav2027Drive.unity";
    public const string PlayerOutput = "build-reference-rules/IGVCReferenceRules.exe";
    public const string InputPath = "artifacts/agents/T-0091/unity-input.json";
    public const string Variant = "rules-485";
    public const string Generated = "Assets/IGVC/GeneratedReferenceRules";
    public const string MapRootName = "Reference rules course 2027 (PROPOSED, larger footprint, uncertified)";
    public const int ExpectedDrums = 93;
    public const float Tape = .1016f, DrumDiameter = .597f, DrumHeight = 1.008f, RampRise = .30f;
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

    [Serializable] public class P { public float x, y; }
    [Serializable] public class TapeDto { public string side; public float width; public List<P> points; }
    [Serializable] public class DrumDto { public string id, colour; public float x, y; }
    [Serializable] public class RampDto { public float x0, x1, y0, y1, rise, run, deck; }
    [Serializable] public class LineDto { public string name; public float x, y, hx, hy, width; }
    [Serializable]
    public class Input
    {
        public string task, variant; public float fieldW, fieldH, spawnHeadingOffNorthDeg, tapeWidth, drumDiameter, drumHeight;
        public P spawn; public List<TapeDto> tapes; public List<DrumDto> drums; public RampDto ramp; public List<LineDto> startLines;
    }

    public static Vector2 Odom(Vector3 world) => new Vector2(world.z, -world.x);

    // Fail closed: missing/malformed input, wrong variant or invalid physical dimensions stop the build.
    public static Input LoadInput()
    {
        string file = Path.Combine(Repository, InputPath);
        if (!File.Exists(file)) throw new Exception("Pinned authoring input missing: " + InputPath);
        var input = JsonUtility.FromJson<Input>(File.ReadAllText(file)) ?? throw new Exception("Authoring input malformed");
        bool Finite(float v) => !float.IsNaN(v) && !float.IsInfinity(v);
        void Require(bool ok, string message) { if (!ok) throw new Exception("Authoring input invalid: " + message); }
        Require(input.task == "T-0091" && input.variant == Variant, "task/variant must be T-0091/" + Variant);
        Require(Finite(input.fieldW) && Finite(input.fieldH) && input.fieldW > 10 && input.fieldH > 10 && input.fieldW < 200 && input.fieldH < 200, "field size");
        Require(Mathf.Abs(input.tapeWidth - Tape) < 1e-4f && Mathf.Abs(input.drumDiameter - DrumDiameter) < 1e-4f && Mathf.Abs(input.drumHeight - DrumHeight) < 1e-4f, "physical sizes changed");
        Require(input.spawn != null && Finite(input.spawn.x) && Finite(input.spawn.y), "spawn");
        Require(input.drums != null && input.drums.Count == ExpectedDrums, "expected " + ExpectedDrums + " drums");
        Require(input.drums.All(d => DrumColors.ContainsKey(d.colour) && Finite(d.x) && Finite(d.y)), "drum colour/position");
        Require(input.drums.Select(d => d.id).Distinct().Count() == input.drums.Count, "duplicate drum id");
        Require(input.tapes != null && input.tapes.Count >= 2 && input.tapes.All(t => t.points != null && t.points.Count > 10 && t.points.All(q => Finite(q.x) && Finite(q.y))), "tapes");
        Require(input.ramp != null && Mathf.Abs(input.ramp.rise - RampRise) < 1e-4f && input.ramp.rise / input.ramp.run <= .15f + 1e-6f && input.ramp.y1 > input.ramp.y0 && input.ramp.x1 > input.ramp.x0, "ramp");
        Require(input.startLines != null && input.startLines.Count == 2 && input.startLines[0].name == "north", "start lines");
        Require(Mathf.Abs(input.spawnHeadingOffNorthDeg) < 2f, "spawn heading more than 2 deg off north");
        return input;
    }

    public static void Build() => Run(true);
    public static void CreateSceneOnly() => Run(false);

    private static void Run(bool player)
    {
        var saved = Protected.ToDictionary(p => p, p => { string f = Path.Combine(Repository, p); return File.Exists(f) ? File.ReadAllBytes(f) : null; });
        var restored = new List<string>();
        try
        {
            CreateScene();
            ReferenceRulesDriveChecks.Run();
            if (player) { R3aDriveBuild.BuildScene(DriveScene, PlayerOutput); Debug.Log("IGVC_REFERENCE_RULES_BUILD_OK " + PlayerOutput); }
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
            string report = Path.Combine(Repository, "artifacts/agents/T-0091"); Directory.CreateDirectory(report);
            File.WriteAllText(Path.Combine(report, "unity-protected-restore.json"),
                "{\"restored\": [" + string.Join(", ", restored.Select(r => "\"" + r.Replace("\\", "/") + "\"")) + "]}\n");
            AssetDatabase.Refresh();
        }
    }

    // ---- persistent assets in GeneratedReferenceRules (explicit Mesh APIs + UploadMeshData; no stale GPU data)
    private static Mesh SaveMesh(Mesh mesh)
    {
        Directory.CreateDirectory(Path.Combine(Repository, "unity/IGVCSim", Generated, "Meshes"));
        string path = Generated + "/Meshes/" + mesh.name + ".asset";
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (existing == null) { mesh.UploadMeshData(false); AssetDatabase.CreateAsset(mesh, path); return mesh; }
        existing.Clear(); existing.indexFormat = mesh.indexFormat;
        existing.SetVertices(mesh.vertices); existing.SetNormals(mesh.normals);
        if (mesh.uv != null && mesh.uv.Length == mesh.vertexCount) existing.SetUVs(0, mesh.uv);
        existing.subMeshCount = mesh.subMeshCount;
        for (int i = 0; i < mesh.subMeshCount; i++) existing.SetTriangles(mesh.GetTriangles(i), i);
        // Tangents only when UVs and normals exist (ribbons have no UVs); same result on first build and rebuild.
        if (existing.uv != null && existing.uv.Length == existing.vertexCount && existing.normals != null && existing.normals.Length == existing.vertexCount) existing.RecalculateTangents();
        existing.RecalculateBounds(); existing.UploadMeshData(false);
        EditorUtility.SetDirty(existing); UnityEngine.Object.DestroyImmediate(mesh);
        return existing;
    }

    private static Material Material(string name, Func<Material> create, Action<Material> configure)
    {
        Directory.CreateDirectory(Path.Combine(Repository, "unity/IGVCSim", Generated, "Materials"));
        string path = Generated + "/Materials/" + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (material == null) { material = create(); AssetDatabase.CreateAsset(material, path); }
        configure(material); EditorUtility.SetDirty(material);
        return material;
    }

    private static Material Lit(string name, Color color, float smoothness) =>
        Material(name, () => new Material(Shader.Find("Standard")), m => { m.color = color; m.SetFloat("_Glossiness", smoothness); m.SetFloat("_Metallic", 0); });

    // Asphalt: a NEW material using the shared Asphalt031 textures read-only (RealismAssets.Asphalt would retile
    // the T-0090 ReferenceAsphalt material, so it is deliberately not called).
    private static Material Asphalt(Vector2 groundSize) => Material("RulesAsphalt", () => new Material(Shader.Find("Standard")), m =>
    {
        Texture2D Load(string file) => AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/IGVC/Realism/Textures/Asphalt031/" + file)
                                       ?? throw new Exception("Realism texture not imported: Asphalt031/" + file);
        m.SetTexture("_MainTex", Load("Albedo.jpg"));
        m.SetTexture("_BumpMap", Load("Normal.jpg")); m.SetFloat("_BumpScale", 1f); m.EnableKeyword("_NORMALMAP");
        m.SetTexture("_MetallicGlossMap", Load("MetallicSmoothness.png")); m.SetFloat("_GlossMapScale", 1f); m.EnableKeyword("_METALLICGLOSSMAP");
        m.SetTexture("_OcclusionMap", Load("Occlusion.jpg")); m.SetFloat("_OcclusionStrength", .8f);
        m.mainTextureScale = groundSize / 3f; m.color = new Color(.55f, .55f, .55f, 1);
    });

    private static Material Sky() => Material("RulesSky", () => new Material(Shader.Find("Skybox/Procedural")), m =>
    {
        m.SetFloat("_SunSize", .04f); m.SetColor("_SkyTint", new Color(.5f, .55f, .62f));
        m.SetColor("_GroundColor", new Color(.36f, .37f, .36f)); m.SetFloat("_Exposure", 1.25f); m.SetFloat("_AtmosphereThickness", .9f);
    });

    private static GameObject Primitive(PrimitiveType type, string name, Transform parent, Material material)
    {
        var item = GameObject.CreatePrimitive(type); item.name = name; item.transform.SetParent(parent, false);
        item.GetComponent<Renderer>().sharedMaterial = material;
        return item;
    }

    private static Transform Group(string name, Transform parent)
    { var t = new GameObject(name).transform; t.SetParent(parent, false); return t; }

    public static float RampHeightAt(RampDto r, float x, float y)
    {
        if (x < r.x0 || x > r.x1 || y < r.y0 || y > r.y1) return 0;
        return r.rise * Mathf.Min(1, Mathf.Min(y - r.y0, r.y1 - y) / r.run);
    }

    // White tape ribbon centred on the exported tape centreline (field coords), following the ramp surface.
    private static Mesh Ribbon(string name, List<P> centre, RampDto ramp)
    {
        var vertices = new List<Vector3>(); var triangles = new List<int>(); var normals = new List<Vector3>();
        for (int i = 0; i < centre.Count; i++)
        {
            var a = centre[Mathf.Max(i - 1, 0)]; var b = centre[Mathf.Min(i + 1, centre.Count - 1)];
            Vector3 t = new Vector3(b.x - a.x, 0, b.y - a.y).normalized, left = new Vector3(-t.z, 0, t.x);
            foreach (float side in new[] { -Tape / 2, Tape / 2 })
            {
                Vector3 v = new Vector3(centre[i].x, 0, centre[i].y) + left * side; v.y = RampHeightAt(ramp, v.x, v.z) + .01f;
                vertices.Add(v); normals.Add(Vector3.up);
            }
            if (i > 0) { int k = 2 * i - 2; triangles.AddRange(new[] { k + 1, k + 3, k + 2, k + 1, k + 2, k }); }
        }
        var mesh = new Mesh { name = name, indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
        mesh.SetVertices(vertices); mesh.SetTriangles(triangles, 0); mesh.SetNormals(normals); mesh.RecalculateBounds();
        return SaveMesh(mesh);
    }

    private static void Destroy(GameObject item) { if (item != null) UnityEngine.Object.DestroyImmediate(item); }

    public static void CreateScene()
    {
        var input = LoadInput();
        RealismAssets.ConfigureTextures();

        // 1. Existing robot scene: R3-a, sensors, TransportProbe, ROS. Remove only the probe's test props/light.
        R3aDriveBuild.CreateScene();
        var active = SceneManager.GetActiveScene();
        foreach (var name in new[] { "Test Pad", "Calibration Wall", "Left Marker", "Right Marker", "Sun" }) Destroy(GameObject.Find(name));
        for (int i = -5; i <= 5; i++) Destroy(GameObject.Find("Grid " + i));
        var transport = UnityEngine.Object.FindFirstObjectByType<TransportProbe>() ?? throw new Exception("TransportProbe missing");
        var robot = GameObject.Find("R3-a kinematic oracle")?.transform ?? throw new Exception("R3-a robot missing");

        // 2. Course root in field coordinates (Unity x = field x east, Unity z = field y north), translated so the
        //    north start-line centre is the odom origin.
        var map = new GameObject(MapRootName).transform;
        map.position = new Vector3(-input.spawn.x, 0, -input.spawn.y);

        var groundSize = new Vector2(input.fieldW, input.fieldH);
        var ground = Primitive(PrimitiveType.Cube, "Asphalt ground (footprint)", Group("Asphalt", map), Asphalt(groundSize));
        ground.transform.localPosition = new Vector3(input.fieldW / 2, -.1f, input.fieldH / 2);
        ground.transform.localScale = new Vector3(input.fieldW, .2f, input.fieldH);

        var white = Lit("RulesTapeWhite", new Color(.9f, .9f, .88f), .25f);
        var tapes = Group("White tape (4 in)", map);
        for (int i = 0; i < input.tapes.Count; i++)
        {
            var strip = new GameObject("Tape " + i + " " + input.tapes[i].side); strip.transform.SetParent(tapes, false);
            strip.AddComponent<MeshFilter>().sharedMesh = Ribbon("RulesTape_" + i, input.tapes[i].points, input.ramp);
            strip.AddComponent<MeshRenderer>().sharedMaterial = white;
        }
        var starts = Group("Start-finish lines", map);
        foreach (var line in input.startLines)
        {
            var bar = Primitive(PrimitiveType.Cube, line.name + " start-finish line", starts, white);
            UnityEngine.Object.DestroyImmediate(bar.GetComponent<Collider>());
            bar.transform.localPosition = new Vector3(line.x, .006f + RampHeightAt(input.ramp, line.x, line.y), line.y);
            bar.transform.localRotation = Quaternion.LookRotation(new Vector3(line.hx, 0, line.hy));
            bar.transform.localScale = new Vector3(line.width, .004f, Tape);
        }

        // 3. Ramp: ascent from the south end toward +z, deck, descent (three support colliders).
        var r = input.ramp; var rampRoot = Group("Ramp (0.30 m)", map); var rampMaterial = Lit("RulesRamp", new Color(.55f, .55f, .53f), .15f);
        float width = r.x1 - r.x0, xc = (r.x0 + r.x1) / 2, slope = Mathf.Sqrt(r.run * r.run + r.rise * r.rise), angle = Mathf.Atan2(r.rise, r.run) * Mathf.Rad2Deg;
        void Surface(string name, float zCentre, float yCentre, float tilt, float len)
        {
            var item = Primitive(PrimitiveType.Cube, name, rampRoot, rampMaterial);
            item.transform.localRotation = Quaternion.Euler(tilt, 0, 0);
            item.transform.localPosition = new Vector3(xc, yCentre, zCentre) - item.transform.localRotation * Vector3.up * .05f;
            item.transform.localScale = new Vector3(width, .1f, len);
        }
        Surface("Ascent", r.y0 + r.run / 2, r.rise / 2, -angle, slope);
        Surface("Deck", (r.y0 + r.y1) / 2, r.rise, 0, r.deck);
        Surface("Descent", r.y1 - r.run / 2, r.rise / 2, angle, slope);

        // 4. Drums: cylinder colliders at physical size; primitive renderer hidden, detailed persistent visual child.
        var drumMesh = SaveMesh(RealisticObstacles.DrumMesh("RulesDrum", DrumDiameter, DrumHeight));
        var band = Lit("RulesDrumBand", new Color(.95f, .95f, .93f), .8f);
        var tire = Lit("RulesDrumBase", new Color(.035f, .035f, .035f), .15f);
        var bodies = DrumColors.ToDictionary(c => c.Key, c => Lit("RulesDrum_" + c.Key, c.Value, .5f));
        var drums = Group("Drums", map);
        foreach (var d in input.drums)
        {
            var drum = Primitive(PrimitiveType.Cylinder, d.colour + " drum " + d.id, drums, bodies[d.colour]);
            drum.transform.localPosition = new Vector3(d.x, RampHeightAt(r, d.x, d.y) + DrumHeight / 2, d.y);
            drum.transform.localScale = new Vector3(DrumDiameter, DrumHeight / 2, DrumDiameter);
            drum.GetComponent<Renderer>().enabled = false;
            var visual = new GameObject("Drum visual"); visual.transform.SetParent(drum.transform, false);
            Vector3 s = drum.transform.localScale; visual.transform.localScale = new Vector3(1 / s.x, 1 / s.y, 1 / s.z);
            visual.AddComponent<MeshFilter>().sharedMesh = drumMesh;
            visual.AddComponent<MeshRenderer>().sharedMaterials = new[] { bodies[d.colour], band, tire };
        }

        // 5. Lighting: one soft-shadow sun, procedural sky; presets applied at runtime by ReferenceDriveConditions.
        var sun = new GameObject("Sun").AddComponent<Light>();
        sun.type = LightType.Directional; sun.shadows = LightShadows.Soft; sun.intensity = 1.2f; sun.transform.rotation = Quaternion.Euler(60, 200, 0);
        var sensor = robot.GetComponentInChildren<Camera>(true) ?? throw new Exception("Robot RGB camera missing");
        var overview = GameObject.Find("Overview Camera")?.GetComponent<Camera>() ?? throw new Exception("Overview camera missing");
        new GameObject("Reference drive conditions").AddComponent<ReferenceDriveConditions>().Configure(sun, Sky(), new[] { sensor, overview });
        RenderSettings.fog = false;
        Vector3 centre = ground.transform.position;
        overview.transform.position = centre + new Vector3(24, 46, -34); overview.transform.LookAt(centre); overview.farClipPlane = 300;
        overview.gameObject.AddComponent<SpectatorCamera>().Configure(robot, overview.transform.position, centre);

        // 6. Simulator-only lane guard from both edges of every SAVED tape mesh, plus terrain supports.
        var guard = new GameObject("Reference rules lane guard (simulator only)").AddComponent<LaneBoundaryGuard>();
        var segments = new List<LaneBoundaryGuard.Segment>();
        foreach (var filter in tapes.GetComponentsInChildren<MeshFilter>())
        {
            var v = filter.sharedMesh.vertices;
            for (int side = 0; side < 2; side++)
                for (int i = side; i + 2 < v.Length; i += 2)
                    segments.Add(new LaneBoundaryGuard.Segment { a = Odom(filter.transform.TransformPoint(v[i])), b = Odom(filter.transform.TransformPoint(v[i + 2])) });
        }
        guard.Configure(segments.ToArray()); guard.Clear();
        if (!guard.CanOccupy(0, 0, 0)) throw new Exception("Robot footprint at the north start line overlaps tape");
        transport.ConfigureLaneGuard(guard);
        var supports = new List<Collider> { ground.GetComponent<Collider>() };
        foreach (var part in new[] { "Ascent", "Deck", "Descent" }) supports.Add(rampRoot.Find(part)?.GetComponent<Collider>());
        if (supports.Any(c => c == null)) throw new Exception("Support collider missing");
        transport.ConfigureTerrain(supports.ToArray());
        EditorUtility.SetDirty(transport);

        Physics.SyncTransforms();
        if (!Physics.Raycast(new Vector3(0, 2, 0), Vector3.down, out var hit, 4) || Mathf.Abs(hit.point.y) > .02f)
            throw new Exception("No ground at the odom origin");
        Directory.CreateDirectory(Path.Combine(Repository, "unity/IGVCSim/Assets/IGVC/Scenes"));
        if (!EditorSceneManager.SaveScene(active, DriveScene)) throw new Exception("Rules drive scene save failed");
        AssetDatabase.SaveAssets();
    }
}
