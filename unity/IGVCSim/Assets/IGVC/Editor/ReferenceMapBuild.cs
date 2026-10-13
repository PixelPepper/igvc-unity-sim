using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

// Image-first AutoNav authoring map (T-0089). A faithful reconstruction of the supplied 2027 course
// diagram from root's literal pixel trace (artifacts/agents/T-0089/inputs/image-trace.json), embedded
// below so generation has no runtime file dependency. Separate scene; no robot, controller, ROS, route
// or autonomy export. Unity x = image right, z = image up; isotropic 0.035 m per image pixel.
// This is an authoring interpretation of a hand-drawn diagram, not a rule-certified course: the
// diagram's printed "480-520 ft" and "44 ft" are annotations, not measurements of this map.
public static class ReferenceMapBuild
{
    private const string Generated = "Assets/IGVC/GeneratedReferenceMap";
    private const string ScenePath = "Assets/IGVC/Scenes/ReferenceAutoNav2027.unity";
    private static readonly CultureInfo Culture = CultureInfo.InvariantCulture;
    private static string Repository => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));

    // Provenance of the authorized inputs (root-supplied SHA-256, verified by the author on read).
    public const string ImageSha256 = "67ca76bb94954549223de2804d6b33ceda7eecdf5c138c3b78c2f5336c4e068b";
    public const string TraceSha256 = "b3ddd39101c58cc400790559b219b244eca99aadfbb10ae5d880db19e6dff239";

    // Pixel -> metres mapping: x = (px - 548) * S, z = (580 - py) * S. Ground covers the full image.
    public const float S = .035f, OriginPx = 548, OriginPy = 580;
    public const int ImageWidth = 1049, ImageHeight = 1160;
    public const float Tape = .1016f, DrumDiameter = .597f, DrumHeight = 1.008f;
    public const float RampHeight = .30f, RampDeck = .4f;

    // ---- Literal trace (image pixels; human-visible tracing estimates, not exact extraction) ----
    private static readonly int[,] OuterTape = {
        {142,248},{147,213},{162,181},{190,158},{230,129},{271,106},{316,79},{349,68},{384,61},{414,67},{451,82},{493,99},
        {537,117},{578,133},{614,145},{644,141},{680,128},{724,114},{772,94},{822,74},{864,64},{901,63},{937,76},{967,98},
        {987,128},{1001,163},{1005,209},{1004,305},{1003,438},{1003,503},{1004,637},{1005,711},{1006,841},{1005,986},{1003,1040},{991,1076},
        {973,1101},{945,1125},{916,1140},{882,1142},{846,1131},{810,1116},{769,1101},{729,1083},{689,1063},{650,1049},{611,1042},{577,1047},
        {539,1060},{499,1076},{459,1092},{422,1110},{386,1130},{348,1122},{311,1100},{275,1078},{239,1054},{205,1037},{175,1012},{159,989},
        {148,957},{142,925}};
    // Outer controls reconstructed below the diagram's ~1100 px crop (not visible in the source).
    private static readonly int[] OuterInferred = { 37, 38, 39, 40, 41, 50, 51, 52 };
    private static readonly int[,] InnerTape = {
        {199,248},{202,228},{229,216},{274,199},{319,181},{354,173},{389,170},{427,177},{469,190},{511,203},{555,216},{591,229},
        {619,232},{648,226},{687,211},{730,196},{773,180},{815,165},{849,150},{880,137},{899,137},{911,154},{916,180},{917,241},
        {917,327},{917,439},{916,503},{916,637},{917,711},{918,848},{918,986},{915,1018},{902,1042},{881,1052},{849,1047},{814,1031},
        {774,1014},{734,995},{694,975},{657,957},{626,946},{601,946},{568,955},{529,970},{488,983},{448,998},{415,1006},{383,1010},
        {350,1006},{314,995},{279,983},{242,967},{217,954},{202,944},{200,926}};
    private static readonly int[,] YellowDrums = {
        {155,226},{201,227},{274,169},{313,97},{333,87},{351,85},{334,108},{338,129},{390,120},{390,140},{367,161},{389,159},
        {408,167},{425,90},{448,94},{449,113},{467,106},{447,133},{518,133},{496,182},{566,176},{625,185},{681,176},{813,99},
        {799,152},{881,128},{986,129},{221,265},{166,311},{123,357},{201,362},{164,406},{94,471},{233,472},{153,503},{171,505},
        {186,505},{143,584},{164,585},{184,586},{146,674},{164,676},{184,675},{93,698},{228,715},{164,727},{128,786},{194,788},
        {161,861},{112,930},{154,944},{199,946},{915,491},{1002,493},{918,647},{1007,649},{248,1018},{359,1027},{383,1032},{406,1027},
        {383,1052},{379,1073},{324,1069},{318,1088},{297,1093},{436,1068},{434,1093},{454,1101},{503,1003},{515,1068},{578,1008},{617,1002},
        {660,1003},{802,1036},{887,1063},{993,1038},{820,1093}};
    private static readonly int[,] RedDrums = { {107,272},{230,421},{94,525},{235,656},{89,747},{217,889} };
    private static readonly int[,] GreenDrums = { {100,332},{230,363},{91,584},{232,594},{94,812},{223,837} };
    // Black circles have no legend in the diagram: represented as editable black drums (interpretation).
    private static readonly int[,] BlackDrums = { {230,311},{96,401},{237,532},{94,646},{224,775},{99,866} };
    private static readonly int[,] Waypoints = { {169,250},{164,539},{159,633},{177,928} };
    private static readonly int[] RampRectPx = { 900, 503, 1016, 637 };   // left, top, right, bottom
    private static readonly int[] NorthStartPx = { 917, 439 }, SouthStartPx = { 917, 711 };
    private static readonly int[] NorthSpeedPx = { 917, 197 }, SouthSpeedPx = { 917, 986 };

    private static readonly (string name, int[,] points, Color color)[] DrumGroups = {
        ("Yellow", YellowDrums, new Color(.98f, .72f, .12f)), ("Red", RedDrums, new Color(.85f, .08f, .06f)),
        ("Green", GreenDrums, new Color(.1f, .62f, .25f)), ("Black", BlackDrums, new Color(.04f, .04f, .04f)) };

    public static Vector3 World(float px, float py) => new Vector3((px - OriginPx) * S, 0, (OriginPy - py) * S);
    public static Vector2 Pixel(Vector3 world) => new Vector2(world.x / S + OriginPx, OriginPy - world.z / S);
    private static Vector3 Flat(Vector3 v) => new Vector3(v.x, 0, v.z);
    private static float GroundX0 => World(0, 0).x;
    private static float GroundX1 => World(ImageWidth, 0).x;
    private static float GroundZ0 => World(0, ImageHeight).z;
    private static float GroundZ1 => World(0, 0).z;

    // ---- Ramp: traced rectangle, ascent along +z (south to north), symmetric slopes, deck centred ----
    private static float RampX0 => World(RampRectPx[0], 0).x;
    private static float RampX1 => World(RampRectPx[2], 0).x;
    private static float RampZ0 => World(0, RampRectPx[3]).z;   // south end
    private static float RampZ1 => World(0, RampRectPx[1]).z;   // north end
    public static float RampSlopeRun => ((RampZ1 - RampZ0) - RampDeck) / 2;
    public static float RampHeightAt(float x, float z)
    {
        if (x < RampX0 || x > RampX1 || z < RampZ0 || z > RampZ1) return 0;
        float along = Mathf.Min(z - RampZ0, RampZ1 - z);
        return RampHeight * Mathf.Min(1, along / RampSlopeRun);
    }

    // Smooth interpolating curve through literal controls: uniform Catmull-Rom, except near-vertical long
    // segments (the straight right edges), which stay exactly straight. Open polyline: the left side is the
    // unpainted No Man's Land, so no boundary is drawn across it.
    public static List<Vector3> Curve(int[,] controls)
    {
        int n = controls.GetLength(0);
        Vector3 P(int i) { i = Mathf.Clamp(i, 0, n - 1); return World(controls[i, 0], controls[i, 1]); }
        bool Straight(int i) => i >= 0 && i < n - 1 && Mathf.Abs(controls[i + 1, 0] - controls[i, 0]) <= 2 && Mathf.Abs(controls[i + 1, 1] - controls[i, 1]) >= 60;
        var result = new List<Vector3> { P(0) };
        for (int i = 0; i < n - 1; i++)
        {
            Vector3 p0 = P(i - 1), p1 = P(i), p2 = P(i + 1), p3 = P(i + 2);
            // Keep the tangent at a straight segment's ends aligned with it.
            if (Straight(i - 1)) p0 = p1 - (p2 - p1);
            if (Straight(i + 1)) p3 = p2 + (p2 - p1);
            int steps = Mathf.Max(2, Mathf.CeilToInt(Vector3.Distance(p1, p2) / .08f));
            for (int k = 1; k <= steps; k++)
            {
                float t = k / (float)steps, t2 = t * t, t3 = t2 * t;
                result.Add(Straight(i) ? Vector3.Lerp(p1, p2, t)
                    : .5f * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3));
            }
        }
        return result;
    }

    private static Material Mat(string name, Color color, float gloss = .1f)
    {
        string path = Generated + "/" + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (material == null) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        material.color = color; material.SetFloat("_Glossiness", gloss); EditorUtility.SetDirty(material);
        return material;
    }

    // Persist a generated mesh, keeping an existing asset's GUID. The existing asset is rewritten through
    // explicit Mesh APIs and re-uploaded: copying serialized data into it (EditorUtility.CopySerialized)
    // updated the saved/CPU data but left the old GPU buffers in place, so renders showed stale geometry.
    private static Mesh SaveMesh(Mesh mesh)
    {
        string path = Generated + "/" + mesh.name + ".asset";
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (existing == null) { mesh.UploadMeshData(false); AssetDatabase.CreateAsset(mesh, path); return mesh; }
        existing.Clear();
        existing.indexFormat = mesh.indexFormat;
        existing.SetVertices(mesh.vertices);
        existing.SetNormals(mesh.normals);
        existing.subMeshCount = mesh.subMeshCount;
        for (int i = 0; i < mesh.subMeshCount; i++) existing.SetTriangles(mesh.GetTriangles(i), i);
        existing.RecalculateBounds();
        existing.UploadMeshData(false);
        EditorUtility.SetDirty(existing);
        UnityEngine.Object.DestroyImmediate(mesh);
        return existing;
    }

    private static Transform Group(string name, Transform parent = null)
    { var t = new GameObject(name).transform; if (parent != null) t.SetParent(parent, false); return t; }

    private static GameObject Primitive(PrimitiveType type, string name, Transform parent, Material material, bool collider)
    {
        var item = GameObject.CreatePrimitive(type); item.name = name; item.transform.SetParent(parent, false);
        item.GetComponent<Renderer>().sharedMaterial = material;
        if (!collider) UnityEngine.Object.DestroyImmediate(item.GetComponent<Collider>());
        return item;
    }

    // White tape ribbon centred on a traced boundary, following the ground/ramp surface.
    private static Mesh Ribbon(string name, IList<Vector3> centre)
    {
        var vertices = new List<Vector3>(); var triangles = new List<int>(); var normals = new List<Vector3>();
        for (int i = 0; i < centre.Count; i++)
        {
            Vector3 t = (Flat(centre[Mathf.Min(i + 1, centre.Count - 1)]) - Flat(centre[Mathf.Max(i - 1, 0)])).normalized;
            Vector3 left = new Vector3(-t.z, 0, t.x);
            foreach (float side in new[] { -Tape / 2, Tape / 2 })
            { Vector3 v = Flat(centre[i]) + left * side; v.y = RampHeightAt(v.x, v.z) + .01f; vertices.Add(v); normals.Add(Vector3.up); }
            if (i > 0) { int a = 2 * i - 2; triangles.AddRange(new[] { a + 1, a + 3, a + 2, a + 1, a + 2, a }); }
        }
        var mesh = new Mesh { name = name }; mesh.SetVertices(vertices); mesh.SetTriangles(triangles, 0);
        mesh.SetNormals(normals); mesh.RecalculateBounds();
        return SaveMesh(mesh);
    }

    // Flat five-point star (annotation only).
    private static Mesh StarMesh()
    {
        var v = new List<Vector3> { Vector3.zero }; var t = new List<int>();
        for (int i = 0; i < 10; i++)
        {
            float a = Mathf.PI / 2 + i * Mathf.PI / 5, r = i % 2 == 0 ? .55f : .22f;
            v.Add(new Vector3(r * Mathf.Cos(a), 0, r * Mathf.Sin(a)));
        }
        for (int i = 0; i < 10; i++) t.AddRange(new[] { 0, 1 + (i + 1) % 10, 1 + i });
        var mesh = new Mesh { name = "WaypointStar" }; mesh.SetVertices(v); mesh.SetTriangles(t, 0);
        mesh.SetNormals(Enumerable.Repeat(Vector3.up, v.Count).ToList()); mesh.RecalculateBounds();
        return SaveMesh(mesh);
    }

    private static bool ConfirmUnsavedScenes() => Application.isBatchMode || EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo();

    [MenuItem("IGVC/Reference Map/Create 2027 AutoNav Map")]
    public static void CreateMenu()
    {
        if (!ConfirmUnsavedScenes()) return;
        Generate();
        EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), ScenePath);
        AssetDatabase.SaveAssets();
    }

    private static void Generate()
    {
        Directory.CreateDirectory(Generated); Directory.CreateDirectory(Path.GetDirectoryName(ScenePath)); AssetDatabase.Refresh();
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var root = Group("Reference AutoNav 2027 (image-traced, uncertified)");

        var asphalt = Group("Asphalt", root);
        var ground = Primitive(PrimitiveType.Cube, "Asphalt ground (full image extent)", asphalt, Mat("Asphalt", new Color(.2f, .21f, .22f)), true);
        ground.transform.localPosition = new Vector3((GroundX0 + GroundX1) / 2, -.1f, (GroundZ0 + GroundZ1) / 2);
        ground.transform.localScale = new Vector3(GroundX1 - GroundX0, .2f, GroundZ1 - GroundZ0);

        var tape = Group("White tape (4 in, traced)", root); var white = Mat("WhiteTape", new Color(.95f, .95f, .95f), .2f);
        foreach (var (label, controls) in new[] { ("Tape outer boundary", OuterTape), ("Tape inner boundary", InnerTape) })
        {
            var strip = new GameObject(label); strip.transform.SetParent(tape, false);
            strip.AddComponent<MeshFilter>().sharedMesh = Ribbon(label.Contains("outer") ? "Tape_Outer" : "Tape_Inner", Curve(controls));
            strip.AddComponent<MeshRenderer>().sharedMaterial = white;
        }

        var ramp = Group("Ramp (traced rectangle, 0.30 m)", root); var rampMaterial = Mat("Ramp", new Color(.62f, .6f, .58f));
        float width = RampX1 - RampX0, xc = (RampX0 + RampX1) / 2, run = RampSlopeRun;
        float slope = Mathf.Sqrt(run * run + RampHeight * RampHeight), angle = Mathf.Atan2(RampHeight, run) * Mathf.Rad2Deg;
        void Surface(string name, float zCentre, float yCentre, float tilt, float len)
        {
            var item = Primitive(PrimitiveType.Cube, name, ramp, rampMaterial, true);
            item.transform.localRotation = Quaternion.Euler(tilt, 0, 0);
            item.transform.localPosition = new Vector3(xc, yCentre, zCentre) - item.transform.localRotation * Vector3.up * .05f;
            item.transform.localScale = new Vector3(width, .1f, len);
        }
        // Ascent from the south end rises toward +z (negative x-rotation lifts +z); descent mirrors it.
        Surface("Ascent", RampZ0 + run / 2, RampHeight / 2, -angle, slope);
        Surface("Deck", (RampZ0 + RampZ1) / 2, RampHeight, 0, RampDeck);
        Surface("Descent", RampZ1 - run / 2, RampHeight / 2, angle, slope);

        // Physical start-finish lines across the right lane at the traced positions.
        var starts = Group("Start-finish lines", root);
        foreach (var (label, px) in new[] { ("North", NorthStartPx), ("South", SouthStartPx) })
        {
            Vector3 inner = World(px[0], px[1]), outer = World(1004, px[1]);
            var line = Primitive(PrimitiveType.Cube, label + " start-finish line", starts, white, false);
            line.transform.localPosition = new Vector3((inner.x + outer.x) / 2, .006f + RampHeightAt(inner.x, inner.z), inner.z);
            line.transform.localScale = new Vector3(outer.x - inner.x, .004f, Tape);
        }

        var drums = Group("Drums (traced)", root);
        foreach (var (name, points, color) in DrumGroups)
        {
            var material = Mat("Drum_" + name, color, .3f);
            for (int i = 0; i < points.GetLength(0); i++)
            {
                var drum = Primitive(PrimitiveType.Cylinder, name + " drum " + (i + 1).ToString("00"), drums, material, true);
                Vector3 at = World(points[i, 0], points[i, 1]);
                drum.transform.localPosition = at + Vector3.up * (RampHeightAt(at.x, at.z) + DrumHeight / 2);
                drum.transform.localScale = new Vector3(DrumDiameter, DrumHeight / 2, DrumDiameter);
            }
        }

        // Annotations: EditorOnly and colliderless; visible in the preview renders only.
        var notes = Group("Annotations (EditorOnly)", root); notes.gameObject.tag = "EditorOnly";
        var blue = Mat("AnnotationBlue", new Color(.12f, .25f, .62f));
        var star = StarMesh();
        for (int i = 0; i < Waypoints.GetLength(0); i++)
        {
            var w = new GameObject("Waypoint star " + (i + 1)); w.transform.SetParent(notes, false); w.tag = "EditorOnly";
            w.transform.localPosition = World(Waypoints[i, 0], Waypoints[i, 1]) + Vector3.up * .03f;
            w.AddComponent<MeshFilter>().sharedMesh = star; w.AddComponent<MeshRenderer>().sharedMaterial = blue;
        }
        foreach (var (label, px) in new[] { ("North start-finish marker", NorthStartPx), ("South start-finish marker", SouthStartPx),
                                            ("North 44 ft speed-check marker (diagram)", NorthSpeedPx), ("South 44 ft speed-check marker (diagram)", SouthSpeedPx) })
        {
            var block = Primitive(PrimitiveType.Cube, label, notes, blue, false); block.tag = "EditorOnly";
            Vector3 at = World(px[0], px[1]);
            block.transform.localPosition = at + Vector3.up * (RampHeightAt(at.x, at.z) + .03f); block.transform.localScale = new Vector3(.8f, .02f, .25f);
        }
        var font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        foreach (var (text, px) in new[] { ("North Start / Finish", new[] { 760, 439 }), ("South Start / Finish", new[] { 760, 711 }),
                                           ("No Man's Land", new[] { 370, 517 }), ("Ramp", new[] { 958, 540 }) })
        {
            var label = new GameObject("Label - " + text); label.transform.SetParent(notes, false); label.tag = "EditorOnly";
            label.transform.localPosition = World(px[0], px[1]) + Vector3.up * .5f; label.transform.localRotation = Quaternion.Euler(90, 0, 0);
            var mesh = label.AddComponent<TextMesh>(); mesh.text = text; mesh.characterSize = .25f; mesh.fontSize = 48;
            mesh.anchor = TextAnchor.MiddleCenter; mesh.color = new Color(.05f, .05f, .05f);
            if (font != null) { mesh.font = font; label.GetComponent<MeshRenderer>().sharedMaterial = font.material; }
        }

        var lighting = Group("Lighting", root);
        var sun = new GameObject("Sun").AddComponent<Light>(); sun.transform.SetParent(lighting, false);
        sun.type = LightType.Directional; sun.intensity = 1f; sun.shadows = LightShadows.Soft; sun.transform.rotation = Quaternion.Euler(60, -30, 0);
        RenderSettings.skybox = null; RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat; RenderSettings.ambientLight = new Color(.6f, .62f, .66f);
        var camera = new GameObject("Overview camera").AddComponent<Camera>(); camera.transform.SetParent(root, false);
        camera.orthographic = true; camera.orthographicSize = (GroundZ1 - GroundZ0) / 2;
        camera.transform.position = new Vector3((GroundX0 + GroundX1) / 2, 40, (GroundZ0 + GroundZ1) / 2);
        camera.transform.rotation = Quaternion.Euler(90, 0, 0); camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = new Color(.32f, .45f, .3f);
        camera.nearClipPlane = .3f; camera.farClipPlane = 100;
    }

    private static float DistanceToPolyline(Vector3 at, IList<Vector3> p)
    {
        float best = float.MaxValue;
        for (int i = 0; i + 1 < p.Count; i++)
        {
            Vector3 a = Flat(p[i]), b = Flat(p[i + 1]), d = b - a, q = Flat(at);
            float t = Mathf.Clamp01(Vector3.Dot(q - a, d) / Mathf.Max(1e-9f, d.sqrMagnitude));
            best = Mathf.Min(best, Vector3.Distance(q, a + d * t));
        }
        return best;
    }

    private static float PolylineLength(IList<Vector3> p) { float l = 0; for (int i = 0; i + 1 < p.Count; i++) l += Vector3.Distance(Flat(p[i]), Flat(p[i + 1])); return l; }
    private static string F(double v) => v.ToString("0.####", Culture);
    private static string Q(string s) => "\"" + s.Replace("\\", "/").Replace("\"", "'") + "\"";

    public static void GenerateAndValidate()
    {
        if (!ConfirmUnsavedScenes()) return;
        Generate();
        if (!EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), ScenePath)) throw new Exception("Reference map scene save failed");
        AssetDatabase.SaveAssets();
        EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        var failures = new List<string>();
        void Check(bool ok, string message) { if (!ok) failures.Add(message); }
        var all = UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        GameObject Find(string name) => all.FirstOrDefault(t => t.name == name)?.gameObject;

        // Durable assets on every saved renderer.
        int meshes = 0, materials = 0;
        foreach (var renderer in UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            if (renderer is MeshRenderer && renderer.GetComponent<TextMesh>() != null) continue;   // labels use the built-in font material
            foreach (var m in renderer.sharedMaterials) { Check(m != null && EditorUtility.IsPersistent(m), "Missing durable material on " + renderer.name); materials++; }
            var filter = renderer.GetComponent<MeshFilter>();
            if (filter != null) { Check(filter.sharedMesh != null && EditorUtility.IsPersistent(filter.sharedMesh), "Missing durable mesh on " + renderer.name); meshes++; }
        }
        Check(Find("Asphalt ground (full image extent)")?.GetComponent<BoxCollider>() != null, "Ground collider missing");
        foreach (var part in new[] { "Ascent", "Deck", "Descent" }) Check(Find(part)?.GetComponent<Collider>() != null, "Ramp collider missing: " + part);

        // Drums: per-colour counts match the trace tables; saved positions back to source pixels within 1 px.
        var drums = Find("Drums (traced)").transform.Cast<Transform>().ToList();
        float worstPixel = 0; var counts = new StringBuilder();
        foreach (var (name, points, _) in DrumGroups)
        {
            var group = drums.Where(d => d.name.StartsWith(name + " drum ")).OrderBy(d => d.name, StringComparer.Ordinal).ToList();
            Check(group.Count == points.GetLength(0), name + " drum count " + group.Count + " != trace " + points.GetLength(0));
            counts.Append((counts.Length > 0 ? ", " : "") + Q(name) + ": " + group.Count);
            for (int i = 0; i < Mathf.Min(group.Count, points.GetLength(0)); i++)
            {
                Vector2 back = Pixel(group[i].position); float err = Vector2.Distance(back, new Vector2(points[i, 0], points[i, 1]));
                worstPixel = Mathf.Max(worstPixel, err);
            }
        }
        foreach (var d in drums) Check(d.GetComponent<Collider>() != null, "Drum collider missing: " + d.name);
        Check(worstPixel <= 1f, "Drum position more than 1 px from trace");

        // Annotations: EditorOnly, no colliders; stars at traced waypoints within 1 px.
        var notes = Find("Annotations (EditorOnly)").GetComponentsInChildren<Transform>(true);
        foreach (var n in notes) Check(n.CompareTag("EditorOnly"), "Annotation not EditorOnly: " + n.name);
        Check(notes.All(n => n.GetComponent<Collider>() == null), "Annotation has collider");
        var stars = notes.Where(n => n.name.StartsWith("Waypoint star ")).OrderBy(n => n.name, StringComparer.Ordinal).ToList();
        Check(stars.Count == Waypoints.GetLength(0), "Waypoint star count");
        float worstStar = 0;
        for (int i = 0; i < Mathf.Min(stars.Count, Waypoints.GetLength(0)); i++)
            worstStar = Mathf.Max(worstStar, Vector2.Distance(Pixel(stars[i].position), new Vector2(Waypoints[i, 0], Waypoints[i, 1])));
        Check(worstStar <= 1f, "Waypoint star more than 1 px from trace");

        // Tape: width from saved vertex pairs, surface conformance, and traced-control fidelity.
        float tapeMin = float.MaxValue, tapeMax = 0, liftMin = float.MaxValue, liftMax = 0; var edges = new Dictionary<string, List<Vector3>>();
        foreach (var filter in Find("White tape (4 in, traced)").GetComponentsInChildren<MeshFilter>())
        {
            var v = filter.sharedMesh.vertices; var centres = new List<Vector3>();
            for (int i = 0; i + 1 < v.Length; i += 2)
            {
                float w = Vector3.Distance(Flat(v[i]), Flat(v[i + 1])); tapeMin = Mathf.Min(tapeMin, w); tapeMax = Mathf.Max(tapeMax, w);
                Vector3 c = (v[i] + v[i + 1]) / 2; float lift = c.y - RampHeightAt(c.x, c.z);
                liftMin = Mathf.Min(liftMin, lift); liftMax = Mathf.Max(liftMax, lift); centres.Add(c);
            }
            edges[filter.name] = centres;
        }
        Check(Mathf.Abs(tapeMin - Tape) < .002f && Mathf.Abs(tapeMax - Tape) < .002f, "Tape width differs from 0.1016 m");
        Check(liftMin > 0 && liftMax < .03f, "Tape does not follow ground/ramp surface");
        float controlError = 0;
        foreach (var (name, controls) in new[] { ("Tape outer boundary", OuterTape), ("Tape inner boundary", InnerTape) })
            for (int i = 0; i < controls.GetLength(0); i++)
                controlError = Mathf.Max(controlError, DistanceToPolyline(World(controls[i, 0], controls[i, 1]), edges[name]) / S);
        Check(controlError <= 1f, "Tape misses a traced control by more than 1 px");

        // Lane width as measured between the two traced boundaries (inner samples to outer polyline).
        var laneWidths = edges["Tape inner boundary"].Select(p => DistanceToPolyline(p, edges["Tape outer boundary"])).OrderBy(x => x).ToList();
        float laneMin = laneWidths.First(), laneMedian = laneWidths[laneWidths.Count / 2], laneMax = laneWidths.Last();

        // Footprint inside the ground (image extent).
        var bounds = new Bounds(); bool first = true;
        foreach (var r in UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        { if (r.CompareTag("EditorOnly") || r.name.StartsWith("Asphalt ground")) continue; if (first) { bounds = r.bounds; first = false; } else bounds.Encapsulate(r.bounds); }
        Check(bounds.min.x >= GroundX0 - .001f && bounds.max.x <= GroundX1 + .001f && bounds.min.z >= GroundZ0 - .001f && bounds.max.z <= GroundZ1 + .001f, "Course features outside the image ground");

        // Ramp: deck height and BOTH slope grades from the saved transforms.
        float Grade(string part) => Mathf.Tan(Mathf.Abs(Mathf.DeltaAngle(0, Find(part).transform.eulerAngles.x)) * Mathf.Deg2Rad);
        float ascent = Grade("Ascent"), descent = Grade("Descent");
        var deck = Find("Deck").transform; float deckTop = deck.position.y + .05f;
        Check(ascent <= .15f + 1e-4f && descent <= .15f + 1e-4f, "Ramp grade above 15%");
        Check(Mathf.Abs(deckTop - RampHeight) < .005f, "Ramp deck height differs from 0.30 m");
        Check(Mathf.Abs(ascent - descent) < 1e-3f, "Ramp slopes not symmetric");

        // Measured drum-to-tape gaps (reported; fidelity, not clearance rules, controls placement).
        float tapeGap = float.MaxValue;
        foreach (var d in drums) foreach (var e in edges.Values) tapeGap = Mathf.Min(tapeGap, DistanceToPolyline(d.position, e) - DrumDiameter / 2 - Tape / 2);

        var json = new StringBuilder("{\n  \"task\": \"T-0089\",\n  \"scene\": " + Q(ScenePath) + ",\n");
        json.Append("  \"interpretation\": \"image-first authoring reconstruction of the supplied diagram; not rule-certified\",\n");
        json.Append("  \"source_image_sha256\": " + Q(ImageSha256) + ",\n  \"trace_sha256\": " + Q(TraceSha256) + ",\n");
        json.Append("  \"mapping\": \"x=(px-548)*0.035, z=(580-py)*0.035 m (isotropic)\",\n");
        json.Append("  \"ground_m\": [" + F(GroundX1 - GroundX0) + ", " + F(GroundZ1 - GroundZ0) + "],\n");
        json.Append("  \"footprint_m\": [" + F(bounds.size.x) + ", " + F(bounds.size.z) + "],\n");
        json.Append("  \"tape_width_m\": [" + F(tapeMin) + ", " + F(tapeMax) + "],\n  \"tape_surface_lift_m\": [" + F(liftMin) + ", " + F(liftMax) + "],\n");
        json.Append("  \"tape_max_control_error_px\": " + F(controlError) + ",\n");
        json.Append("  \"tape_lengths_m\": {\"outer\": " + F(PolylineLength(edges["Tape outer boundary"])) + ", \"inner\": " + F(PolylineLength(edges["Tape inner boundary"])) + "},\n");
        json.Append("  \"measured_lane_width_m\": {\"min\": " + F(laneMin) + ", \"median\": " + F(laneMedian) + ", \"max\": " + F(laneMax) + "},\n");
        json.Append("  \"outer_inferred_control_indices\": [" + string.Join(", ", OuterInferred) + "],\n");
        json.Append("  \"ramp\": {\"deck_height_m\": " + F(deckTop) + ", \"ascent_grade\": " + F(ascent) + ", \"descent_grade\": " + F(descent) + ", \"slope_run_m\": " + F(RampSlopeRun) + ", \"deck_m\": " + F(RampDeck) + ", \"width_m\": " + F(deck.localScale.x) + "},\n");
        json.Append("  \"drum_counts\": {" + counts + "},\n  \"drum_max_pixel_error\": " + F(worstPixel) + ",\n  \"waypoint_star_max_pixel_error\": " + F(worstStar) + ",\n");
        json.Append("  \"drum_m\": {\"diameter\": " + F(DrumDiameter) + ", \"height\": " + F(DrumHeight) + ", \"provenance\": \"reported by interactive author from user measurements; not independently confirmed\"},\n");
        json.Append("  \"black_marker_interpretation\": \"black diagram circles have no legend; represented as editable black drums\",\n");
        json.Append("  \"min_drum_tape_gap_m\": " + F(tapeGap) + ",\n  \"durable_meshes\": " + meshes + ",\n  \"durable_materials\": " + materials + ",\n");
        json.Append("  \"diagram_annotations_not_measured\": [\"AutoNav Course 480-520 ft long\", \"44ft Min speed check\", \"4 in white reflective tape lines\"],\n");
        json.Append("  \"unverified\": [\"course route length\", \"rule compliance (area, lane width, turn radius, passages, 44 ft)\", \"cropped lower outer boundary\", \"tracing accuracy vs source pixels\", \"sensor appearance\", \"navigation\", \"drum dimensions\"],\n");

        string output = Path.Combine(Repository, "artifacts/agents/T-0089"); Directory.CreateDirectory(output);
        var overview = Render(Find("Overview camera").GetComponent<Camera>(), Path.Combine(output, "overview.png"), ImageWidth, ImageHeight);
        // Render check: the portrait overview is pixel-aligned with the source image, so every traced tape
        // control must actually appear as white tape in what the GPU drew (catches stale or wrong mesh
        // uploads that CPU/saved-asset checks cannot see). A drum or label may cover a few controls.
        int tapeControls = 0, tapeRendered = 0;
        foreach (var controls in new[] { OuterTape, InnerTape })
            for (int i = 0; i < controls.GetLength(0); i++)
            {
                tapeControls++;
                int cx = controls[i, 0], cy = ImageHeight - 1 - controls[i, 1];
                bool white = false;
                for (int dy = -2; dy <= 2 && !white; dy++)
                    for (int dx = -2; dx <= 2 && !white; dx++)
                    {
                        int x = cx + dx, y = cy + dy;
                        if (x < 0 || y < 0 || x >= ImageWidth || y >= ImageHeight) continue;
                        Color32 c = overview[y * ImageWidth + x];
                        white = Math.Min(c.r, Math.Min(c.g, c.b)) >= 200;
                    }
                if (white) tapeRendered++;
            }
        float renderedFraction = tapeRendered / (float)Math.Max(1, tapeControls);
        Check(renderedFraction >= .9f, "Rendered overview shows tape at only " + tapeRendered + "/" + tapeControls + " traced controls (stale or wrong render)");
        json.Append("  \"render_tape_controls_white\": [" + tapeRendered + ", " + tapeControls + "],\n");
        var oblique = new GameObject("Oblique preview camera (temporary)").AddComponent<Camera>();
        Vector3 centre = new Vector3((GroundX0 + GroundX1) / 2, 0, (GroundZ0 + GroundZ1) / 2);
        oblique.transform.position = centre + new Vector3(18, 16, -30); oblique.transform.LookAt(centre);
        oblique.fieldOfView = 55; oblique.clearFlags = CameraClearFlags.SolidColor; oblique.backgroundColor = new Color(.55f, .68f, .82f);
        Render(oblique, Path.Combine(output, "oblique.png"), 1600, 1334);
        UnityEngine.Object.DestroyImmediate(oblique.gameObject);

        json.Append("  \"previews\": [\"overview.png (portrait 1049x1160, no reference route)\", \"oblique.png (1600x1334)\"],\n");
        json.Append("  \"failures\": [" + string.Join(", ", failures.Select(Q)) + "],\n");
        json.Append("  \"passed\": " + (failures.Count == 0 ? "true" : "false") + "\n}\n");
        File.WriteAllText(Path.Combine(output, "unity-validation.json"), json.ToString());
        if (failures.Count > 0) throw new Exception("Reference map validation failed: " + string.Join("; ", failures));
        Debug.Log("IGVC_REFERENCE_MAP_OK drums=" + drums.Count + " control_error_px=" + F(controlError));
    }

    // Renders to file and returns the rendered pixels (row 0 = bottom, as ReadPixels stores them).
    private static Color32[] Render(Camera camera, string file, int width, int height)
    {
        var previous = RenderTexture.active; var texture = new RenderTexture(width, height, 24);
        var image = new Texture2D(width, height, TextureFormat.RGB24, false);
        try
        {
            camera.aspect = width / (float)height; camera.targetTexture = texture; camera.Render();
            RenderTexture.active = texture; image.ReadPixels(new Rect(0, 0, width, height), 0, 0); image.Apply();
            File.WriteAllBytes(file, image.EncodeToPNG());
            return image.GetPixels32();
        }
        finally
        {
            camera.targetTexture = null; camera.ResetAspect(); RenderTexture.active = previous;
            texture.Release(); UnityEngine.Object.DestroyImmediate(texture); UnityEngine.Object.DestroyImmediate(image);
        }
    }
}
