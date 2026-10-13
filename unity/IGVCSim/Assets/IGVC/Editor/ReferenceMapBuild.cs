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

// Diagram-derived AutoNav authoring map (T-0089). Separate scene, editor-only reference path;
// no robot, controller, ROS or route export. Unity x = east (120 ft), z = north (100 ft), metres.
public static class ReferenceMapBuild
{
    private const string Generated = "Assets/IGVC/GeneratedReferenceMap";
    private const string ScenePath = "Assets/IGVC/Scenes/ReferenceAutoNav2027.unity";
    private static readonly CultureInfo Culture = CultureInfo.InvariantCulture;
    private static string Repository => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));

    // Rules page 10 dimensions. Drum size as reported by the interactive author from user
    // measurements (not independently confirmed here), not a rule value.
    public const float AreaX = 36.576f, AreaZ = 30.48f, Lane = 3.2f, Tape = .1016f;
    public const float RampHeight = .45f, RampRise = 3f, RampDeck = 1.2f, RampWidth = 3.7f;
    public const float DrumDiameter = .597f, DrumHeight = 1.008f, PotholeDiameter = .6096f;
    public const float SpeedCheck = 13.4112f, MinRuleRadius = 1.524f, MinPassage = 1.524f;
    // Layout: centreline margin keeps outer tape >= .2 m inside the area boundary.
    private const float Margin = Lane / 2 + Tape / 2 + .2f, Bend = 3.2f, Wave = 5f, Bulge = 4f;
    private static float XR => AreaX / 2 - Margin;
    private static float ZT => AreaZ / 2 - Margin;
    private static float StraightHalf => ZT - Bend;
    private const float RampStart = -(RampRise + RampDeck / 2), StartOffset = 4.6f, Step = .2f;

    private struct Obstacle { public string name, kind; public int side; public float s, offset; public Color color; }

    // Closed counter-clockwise centreline: right straight north, north connector west,
    // No Man's Land south, south connector east. Returns resampled points and NML range.
    public static List<Vector3> Centerline(out float nmlStart, out float nmlEnd)
    {
        var raw = new List<Vector3>();
        float h = StraightHalf, xL = -XR, span = (XR - Bend) * 2, k = 2 * Mathf.PI / span;
        void Arc(Vector2 c, float a0, float a1) { for (int i = 1; i <= 24; i++) { float a = Mathf.Lerp(a0, a1, i / 24f) * Mathf.Deg2Rad; raw.Add(new Vector3(c.x + Bend * Mathf.Cos(a), 0, c.y + Bend * Mathf.Sin(a))); } }
        for (int i = 0; i <= 40; i++) raw.Add(new Vector3(XR, 0, Mathf.Lerp(-h, h, i / 40f)));
        Arc(new Vector2(XR - Bend, h), 0, 90);
        for (int i = 1; i <= 160; i++) { float x = Mathf.Lerp(XR - Bend, xL + Bend, i / 160f); raw.Add(new Vector3(x, 0, ZT - Wave * (1 - Mathf.Cos(k * (XR - Bend - x))))); }
        Arc(new Vector2(xL + Bend, h), 90, 180);
        int nmlRaw = raw.Count - 1;
        float kn = 2 * Mathf.PI / (2 * h);
        for (int i = 1; i <= 100; i++) { float z = Mathf.Lerp(h, -h, i / 100f); raw.Add(new Vector3(xL + Bulge * (1 - Mathf.Cos(kn * (h - z))), 0, z)); }
        int nmlRawEnd = raw.Count - 1;
        Arc(new Vector2(xL + Bend, -h), 180, 270);
        for (int i = 1; i <= 160; i++) { float x = Mathf.Lerp(xL + Bend, XR - Bend, i / 160f); raw.Add(new Vector3(x, 0, -ZT + Wave * (1 - Mathf.Cos(k * (x - xL - Bend))))); }
        Arc(new Vector2(XR - Bend, -h), 270, 360);
        raw.RemoveAt(raw.Count - 1);
        var cumulative = new float[raw.Count + 1];
        for (int i = 0; i < raw.Count; i++) cumulative[i + 1] = cumulative[i] + Vector3.Distance(raw[i], raw[(i + 1) % raw.Count]);
        nmlStart = cumulative[nmlRaw]; nmlEnd = cumulative[nmlRawEnd];
        float length = cumulative[raw.Count]; int count = Mathf.RoundToInt(length / Step);
        var result = new List<Vector3>(count); int j = 0;
        for (int i = 0; i < count; i++)
        {
            float s = length * i / count;
            while (cumulative[j + 1] < s) j++;
            float t = (s - cumulative[j]) / Mathf.Max(1e-6f, cumulative[j + 1] - cumulative[j]);
            result.Add(Vector3.Lerp(raw[j], raw[(j + 1) % raw.Count], t));
        }
        return result;
    }

    public static float RampHeightAt(float x, float z)
    {
        float along = z - RampStart, total = 2 * RampRise + RampDeck;
        if (Mathf.Abs(x - XR) > RampWidth / 2 || along < 0 || along > total) return 0;
        return RampHeight * Mathf.Min(1, Mathf.Min(along, total - along) / RampRise);
    }

    private static float Length(IList<Vector3> p) { float l = 0; for (int i = 0; i < p.Count; i++) l += Vector3.Distance(Flat(p[i]), Flat(p[(i + 1) % p.Count])); return l; }
    private static Vector3 Flat(Vector3 v) => new Vector3(v.x, 0, v.z);
    private static int Index(IList<Vector3> p, float s) { float l = Length(p); return ((Mathf.RoundToInt(s / l * p.Count) % p.Count) + p.Count) % p.Count; }
    private static Vector3 Tangent(IList<Vector3> p, int i) => (Flat(p[(i + 1) % p.Count]) - Flat(p[(i - 1 + p.Count) % p.Count])).normalized;
    private static Vector3 Left(Vector3 t) => new Vector3(-t.z, 0, t.x);

    private static Material Mat(string name, Color color, float gloss = .1f)
    {
        string path = Generated + "/" + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (material == null) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        material.color = color; material.SetFloat("_Glossiness", gloss); EditorUtility.SetDirty(material);
        return material;
    }

    private static Mesh SaveMesh(Mesh mesh)
    {
        string path = Generated + "/" + mesh.name + ".asset";
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (existing == null) { AssetDatabase.CreateAsset(mesh, path); return mesh; }
        EditorUtility.CopySerialized(mesh, existing); UnityEngine.Object.DestroyImmediate(mesh); return existing;
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

    // Tape ribbon at lateral offset over sample range [from, to], following the ramp surface.
    private static Mesh Ribbon(string name, IList<Vector3> p, int from, int to, float offset)
    {
        var vertices = new List<Vector3>(); var triangles = new List<int>();
        int n = ((to - from) % p.Count + p.Count) % p.Count + 1;
        for (int k = 0; k < n; k++)
        {
            int i = (from + k) % p.Count; Vector3 left = Left(Tangent(p, i));
            foreach (float side in new[] { -Tape / 2, Tape / 2 })
            { Vector3 v = Flat(p[i]) + left * (offset + side); v.y = RampHeightAt(v.x, v.z) + .01f; vertices.Add(v); }
            if (k > 0) { int a = 2 * k - 2; triangles.AddRange(new[] { a + 1, a + 3, a + 2, a + 1, a + 2, a }); }
        }
        var mesh = new Mesh { name = name }; mesh.SetVertices(vertices); mesh.SetTriangles(triangles, 0);
        mesh.RecalculateNormals(); mesh.RecalculateBounds();
        return SaveMesh(mesh);
    }

    private static List<Obstacle> Obstacles(float length, float nmlStart, float nmlEnd)
    {
        var list = new List<Obstacle>();
        float inner = Lane / 2 - Tape / 2 - .15f - DrumDiameter / 2;
        // Connector intervals in path distance (after the bends, before the next bend).
        float bendArc = Mathf.PI / 2 * Bend, straight = 2 * StraightHalf;
        float northFrom = straight + bendArc, northTo = nmlStart - bendArc;
        float southFrom = nmlEnd + bendArc, southTo = length - bendArc;
        var yellow = new Color(.95f, .8f, .1f);
        void Cluster(string label, float s, int side)
        { for (int d = 0; d < 2; d++) list.Add(new Obstacle { name = label + " drum " + (d + 1), kind = "drum", s = s + d * .62f, offset = side * inner, side = side, color = yellow }); }
        float[] fractions = { .22f, .5f, .78f };
        for (int i = 0; i < 3; i++) Cluster("North connector cluster " + (i + 1), Mathf.Lerp(northFrom, northTo, fractions[i]), i % 2 == 0 ? 1 : -1);
        for (int i = 0; i < 3; i++) Cluster("South connector cluster " + (i + 1), Mathf.Lerp(southFrom, southTo, fractions[i]), i % 2 == 0 ? -1 : 1);
        var mixed = new[] { new Color(.95f, .42f, .05f), new Color(.92f, .92f, .9f), new Color(.1f, .35f, .85f), new Color(.15f, .6f, .2f) };
        (float f, float o)[] drums = { (.17f, 2.1f), (.5f, -2.3f), (.83f, 2.1f), (.5f, 3.2f) };
        for (int i = 0; i < drums.Length; i++)
            list.Add(new Obstacle { name = "No Man's Land drum " + (i + 1), kind = "drum", s = Mathf.Lerp(nmlStart, nmlEnd, drums[i].f), offset = drums[i].o, side = Math.Sign(drums[i].o), color = mixed[i % mixed.Length] });
        (float f, float o)[] holes = { (.1f, -1.9f), (.25f, -1.9f), (.42f, 1.9f), (.58f, 1.9f), (.75f, -1.9f), (.9f, -1.9f) };
        for (int i = 0; i < holes.Length; i++)
            list.Add(new Obstacle { name = "Simulated pothole " + (i + 1), kind = "pothole", s = Mathf.Lerp(nmlStart, nmlEnd, holes[i].f), offset = holes[i].o, side = Math.Sign(holes[i].o), color = Color.white });
        return list;
    }

    [MenuItem("IGVC/Reference Map/Create 2027 AutoNav Map")]
    public static void CreateMenu()
    {
        if (!Application.isBatchMode && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
        Generate();
        EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), ScenePath);
        AssetDatabase.SaveAssets();
    }

    private static void Generate()
    {
        Directory.CreateDirectory(Generated); Directory.CreateDirectory(Path.GetDirectoryName(ScenePath)); AssetDatabase.Refresh();
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var path = Centerline(out float nmlStart, out float nmlEnd); float length = Length(path);
        var root = Group("Reference AutoNav 2027 (diagram-derived, uncertified)");

        var asphalt = Group("Asphalt", root);
        var ground = Primitive(PrimitiveType.Cube, "Asphalt ground 120x100 ft", asphalt, Mat("Asphalt", new Color(.2f, .21f, .22f)), true);
        ground.transform.localPosition = new Vector3(0, -.1f, 0); ground.transform.localScale = new Vector3(AreaX, .2f, AreaZ);

        var tape = Group("White tape", root); var white = Mat("WhiteTape", new Color(.95f, .95f, .95f), .2f);
        int paintFrom = Index(path, nmlEnd), paintTo = Index(path, nmlStart);
        foreach (var (label, offset) in new[] { ("Tape left (inner)", Lane / 2), ("Tape right (outer)", -Lane / 2) })
        {
            var strip = new GameObject(label); strip.transform.SetParent(tape, false);
            strip.AddComponent<MeshFilter>().sharedMesh = Ribbon("Tape_" + (offset > 0 ? "Inner" : "Outer"), path, paintFrom, paintTo, offset);
            strip.AddComponent<MeshRenderer>().sharedMaterial = white;
        }

        var ramp = Group("Ramp (15% grade, 0.45 m)", root); var rampMaterial = Mat("Ramp", new Color(.45f, .4f, .34f));
        float slope = Mathf.Sqrt(RampRise * RampRise + RampHeight * RampHeight), angle = Mathf.Atan2(RampHeight, RampRise) * Mathf.Rad2Deg;
        void Surface(string name, float zTop, float yTop, float tilt, float len)
        {
            var item = Primitive(PrimitiveType.Cube, name, ramp, rampMaterial, true);
            item.transform.localRotation = Quaternion.Euler(tilt, 0, 0);
            item.transform.localPosition = new Vector3(XR, yTop, zTop) - item.transform.localRotation * Vector3.up * .05f;
            item.transform.localScale = new Vector3(RampWidth, .1f, len);
        }
        Surface("Ascent", RampStart + RampRise / 2, RampHeight / 2, -angle, slope);
        Surface("Deck", 0, RampHeight, 0, RampDeck);
        Surface("Descent", -RampStart - RampRise / 2, RampHeight / 2, angle, slope);

        var starts = Group("Start-finish lines", root); var checks = Group("Speed-check markers (44 ft)", root);
        var marker = Mat("SpeedCheckMarker", new Color(1f, .45f, 0f));
        foreach (var (label, z, direction) in new[] { ("North", StartOffset, 1), ("South", -StartOffset, -1) })
        {
            var finish = Primitive(PrimitiveType.Cube, label + " start-finish line", starts, white, false);
            finish.transform.localPosition = new Vector3(XR, .006f, z); finish.transform.localScale = new Vector3(Lane, .004f, Tape);
            int i = Index(path, Mathf.Repeat(PathDistance(path, new Vector3(XR, 0, z)) + direction * SpeedCheck, length));
            Vector3 left = Left(Tangent(path, i));
            foreach (int side in new[] { 1, -1 })
            {
                var post = Primitive(PrimitiveType.Cube, label + " speed-check post " + (side > 0 ? "left" : "right"), checks, marker, true);
                Vector3 at = Flat(path[i]) + left * side * (Lane / 2 + .4f);
                post.transform.localPosition = at + Vector3.up * .25f; post.transform.localScale = new Vector3(.08f, .5f, .08f);
            }
        }

        var drums = Group("Drums", root); var potholes = Group("Simulated potholes (painted white disks)", root);
        foreach (var o in Obstacles(length, nmlStart, nmlEnd))
        {
            int i = Index(path, Mathf.Repeat(o.s, length)); Vector3 at = Flat(path[i]) + Left(Tangent(path, i)) * o.offset;
            if (o.kind == "drum")
            {
                var drum = Primitive(PrimitiveType.Cylinder, o.name, drums, Mat("Drum_" + ColorUtility.ToHtmlStringRGB(o.color), o.color, .3f), true);
                drum.transform.localPosition = at + Vector3.up * DrumHeight / 2; drum.transform.localScale = new Vector3(DrumDiameter, DrumHeight / 2, DrumDiameter);
            }
            else
            {
                var hole = Primitive(PrimitiveType.Cylinder, o.name, potholes, white, false);
                hole.transform.localPosition = at + Vector3.up * .006f; hole.transform.localScale = new Vector3(PotholeDiameter, .002f, PotholeDiameter);
            }
        }

        var notes = Group("Annotations (EditorOnly)", root);
        notes.gameObject.tag = "EditorOnly";
        var icon = EditorGUIUtility.IconContent("sv_label_1").image as Texture2D;
        void Note(string name, Vector3 at)
        { var item = Group(name, notes); item.position = at; item.gameObject.tag = "EditorOnly"; if (icon != null) EditorGUIUtility.SetIconForObject(item.gameObject, icon); }
        float nml = nmlEnd - nmlStart;
        Note("Waypoint 1 - No Man's Land entrance", Flat(path[Index(path, nmlStart + .04f * nml)]));
        Note("Waypoint 2 - No Man's Land middle", Flat(path[Index(path, nmlStart + nml / 3)]));
        Note("Waypoint 3 - No Man's Land middle", Flat(path[Index(path, nmlStart + 2 * nml / 3)]));
        Note("Waypoint 4 - No Man's Land exit", Flat(path[Index(path, nmlEnd - .04f * nml)]));
        Note("Label - No Man's Land (unpainted)", new Vector3(-XR + 3, 0, 0));
        Note("Label - North connector", new Vector3(0, 0, ZT - Wave)); Note("Label - South connector", new Vector3(0, 0, -ZT + Wave));
        var reference = Group("Authoring reference path (editor-only, not a route)", notes); reference.gameObject.tag = "EditorOnly";
        var pathLine = reference.gameObject.AddComponent<LineRenderer>();
        pathLine.loop = true; pathLine.useWorldSpace = true; pathLine.widthMultiplier = .08f; pathLine.sharedMaterial = Mat("ReferencePath", new Color(.2f, .6f, 1f));
        pathLine.positionCount = path.Count; pathLine.SetPositions(path.Select(v => new Vector3(v.x, RampHeightAt(v.x, v.z) + .03f, v.z)).ToArray());
        pathLine.enabled = false;

        var lighting = Group("Lighting", root);
        var sun = new GameObject("Sun").AddComponent<Light>(); sun.transform.SetParent(lighting, false);
        sun.type = LightType.Directional; sun.intensity = 1f; sun.shadows = LightShadows.Soft; sun.transform.rotation = Quaternion.Euler(55, -35, 0);
        RenderSettings.skybox = null; RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat; RenderSettings.ambientLight = new Color(.6f, .62f, .66f);
        var camera = new GameObject("Overview camera").AddComponent<Camera>(); camera.transform.SetParent(root, false);
        camera.orthographic = true; camera.orthographicSize = AreaZ / 2 + 1; camera.transform.position = new Vector3(0, 40, 0);
        camera.transform.rotation = Quaternion.Euler(90, 0, 0); camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = new Color(.32f, .45f, .3f);
        camera.nearClipPlane = .3f; camera.farClipPlane = 100;
    }

    private static float PathDistance(IList<Vector3> p, Vector3 at)
    {
        int best = 0; for (int i = 1; i < p.Count; i++) if ((Flat(p[i]) - Flat(at)).sqrMagnitude < (Flat(p[best]) - Flat(at)).sqrMagnitude) best = i;
        float s = 0; for (int i = 0; i < best; i++) s += Vector3.Distance(Flat(p[i]), Flat(p[i + 1])); return s;
    }

    private static float DistanceToPolyline(Vector3 at, IList<Vector3> p, bool closed)
    {
        float best = float.MaxValue; int n = closed ? p.Count : p.Count - 1;
        for (int i = 0; i < n; i++)
        {
            Vector3 a = Flat(p[i]), b = Flat(p[(i + 1) % p.Count]), d = b - a, q = Flat(at);
            float t = Mathf.Clamp01(Vector3.Dot(q - a, d) / Mathf.Max(1e-9f, d.sqrMagnitude));
            best = Mathf.Min(best, Vector3.Distance(q, a + d * t));
        }
        return best;
    }

    private static string F(double v) => v.ToString("0.####", Culture);

    public static void GenerateAndValidate()
    {
        Generate();
        if (!EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), ScenePath)) throw new Exception("Reference map scene save failed");
        AssetDatabase.SaveAssets();
        EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        var failures = new List<string>(); var json = new StringBuilder("{\n  \"task\": \"T-0089\",\n  \"scene\": \"" + ScenePath + "\",\n");
        void Check(bool ok, string message) { if (!ok) failures.Add(message); }
        var all = UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        GameObject Find(string name) => all.FirstOrDefault(t => t.name == name)?.gameObject;

        int meshes = 0, materials = 0;
        foreach (var renderer in UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            // IsPersistent accepts built-in primitive meshes as well as generated assets.
            foreach (var m in renderer.sharedMaterials) { Check(m != null && EditorUtility.IsPersistent(m), "Missing durable material on " + renderer.name); materials++; }
            var filter = renderer.GetComponent<MeshFilter>();
            if (filter != null) { Check(filter.sharedMesh != null && EditorUtility.IsPersistent(filter.sharedMesh), "Missing durable mesh on " + renderer.name); meshes++; }
        }
        Check(Find("Asphalt ground 120x100 ft")?.GetComponent<BoxCollider>() != null, "Ground collider missing");
        foreach (var part in new[] { "Ascent", "Deck", "Descent" }) Check(Find(part)?.GetComponent<Collider>() != null, "Ramp collider missing: " + part);
        var drums = Find("Drums").transform.Cast<Transform>().ToList();
        var holes = Find("Simulated potholes (painted white disks)").transform.Cast<Transform>().ToList();
        foreach (var d in drums) Check(d.GetComponent<Collider>() != null, "Drum collider missing: " + d.name);
        foreach (var h in holes) Check(h.GetComponent<Collider>() == null, "Pothole must not collide: " + h.name);
        var notes = Find("Annotations (EditorOnly)").GetComponentsInChildren<Transform>(true);
        foreach (var n in notes) Check(n.CompareTag("EditorOnly"), "Annotation not EditorOnly: " + n.name);
        Check(notes.All(n => n.GetComponent<Collider>() == null), "Annotation has collider");

        // Tape: measured from saved mesh vertex pairs and ramp-surface conformance.
        float tapeMin = float.MaxValue, tapeMax = 0, tapeLift = float.MaxValue, tapeLiftMax = 0; var tapeEdges = new List<List<Vector3>>();
        foreach (var filter in Find("White tape").GetComponentsInChildren<MeshFilter>())
        {
            var v = filter.sharedMesh.vertices; var centres = new List<Vector3>();
            for (int i = 0; i + 1 < v.Length; i += 2)
            {
                float w = Vector3.Distance(Flat(v[i]), Flat(v[i + 1])); tapeMin = Mathf.Min(tapeMin, w); tapeMax = Mathf.Max(tapeMax, w);
                Vector3 c = (v[i] + v[i + 1]) / 2; float lift = c.y - RampHeightAt(c.x, c.z);
                tapeLift = Mathf.Min(tapeLift, lift); tapeLiftMax = Mathf.Max(tapeLiftMax, lift); centres.Add(c);
            }
            Check(filter.sharedMesh.normals.All(n => n.y > .9f), "Tape normals not upward");
            tapeEdges.Add(centres);
        }
        Check(Mathf.Abs(tapeMin - Tape) < .002f && Mathf.Abs(tapeMax - Tape) < .002f, "Tape width differs from 0.1016 m");
        Check(tapeLift > 0 && tapeLiftMax < .03f, "Tape does not follow ramp/ground surface");

        // Footprint from course-feature renderer bounds (ground slab excluded: it is the area itself).
        var bounds = new Bounds(Vector3.zero, Vector3.zero); bool first = true;
        foreach (var r in UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        { if (r.CompareTag("EditorOnly") || r.name == "Asphalt ground 120x100 ft") continue; if (first) { bounds = r.bounds; first = false; } else bounds.Encapsulate(r.bounds); }
        Check(bounds.min.x >= -AreaX / 2 - .001f && bounds.max.x <= AreaX / 2 + .001f && bounds.min.z >= -AreaZ / 2 - .001f && bounds.max.z <= AreaZ / 2 + .001f, "Course features outside 120 x 100 ft area");
        Check(bounds.size.x <= AreaX + .001f && bounds.size.z <= AreaZ + .001f, "Footprint exceeds 120 x 100 ft");

        // Ramp grade from saved ascent transform.
        var ascent = Find("Ascent").transform; float grade = Mathf.Tan(Mathf.Abs(Mathf.DeltaAngle(0, ascent.eulerAngles.x)) * Mathf.Deg2Rad);
        float rise = Mathf.Cos(Mathf.Atan(grade)) * ascent.localScale.z;
        Check(grade <= .15f + 1e-4f, "Ramp grade above 15%"); Check(Find("Deck").transform.localScale.x >= 3.048f, "Ramp narrower than 10 ft");

        // Reference path from the saved (disabled) editor-only line.
        var line = Find("Authoring reference path (editor-only, not a route)").GetComponent<LineRenderer>();
        var path = new Vector3[line.positionCount]; line.GetPositions(path); float length = Length(path);
        // Conservative: minimum circumradius over 0.2 m and 1 m sample windows (polyline corners only lower it).
        float minRadius = float.MaxValue;
        foreach (int w in new[] { 1, 5 })
            for (int i = 0; i < path.Length; i++)
            {
                Vector3 a = Flat(path[(i - w + path.Length) % path.Length]), b = Flat(path[i]), c = Flat(path[(i + w) % path.Length]);
                float cross = Mathf.Abs(Vector3.Cross(b - a, c - a).y); if (cross < 1e-6f) continue;
                minRadius = Mathf.Min(minRadius, Vector3.Distance(a, b) * Vector3.Distance(b, c) * Vector3.Distance(a, c) / (2 * cross));
            }
        Check(length > 0, "Reference path empty"); Check(minRadius >= MinRuleRadius, "Reference turn radius below 5 ft");
        Check(minRadius > Lane / 2 + Tape, "Inner tape would fold on tightest bend");
        // Self-intersection: centreline points far apart along the loop must keep two tapes apart.
        float separation = float.MaxValue, cumulative = 0; var along = new float[path.Length];
        for (int i = 1; i < path.Length; i++) along[i] = cumulative += Vector3.Distance(Flat(path[i - 1]), Flat(path[i]));
        for (int i = 0; i < path.Length; i++)
            for (int j = i + 1; j < path.Length; j++)
            {
                float gap = along[j] - along[i]; if (Mathf.Min(gap, length - gap) < 4 * Lane) continue;
                separation = Mathf.Min(separation, Vector3.Distance(Flat(path[i]), Flat(path[j])));
            }
        Check(separation >= Lane + Tape, "Lane corridors overlap or self-intersect");

        // Speed-check distance along path from each start line.
        var speed = new List<float>();
        foreach (var (start, post, dir) in new[] { ("North start-finish line", "North speed-check post left", 1), ("South start-finish line", "South speed-check post left", -1) })
        {
            float s0 = PathDistance(path, Find(start).transform.position), s1 = PathDistance(path, Find(post).transform.position);
            speed.Add(Mathf.Repeat(dir * (s1 - s0), length));
        }
        Check(speed.All(d => Mathf.Abs(d - SpeedCheck) < .3f), "Speed-check marker not 44 ft along path");

        // Obstacle clearances: tape, ramp, passage, waypoints.
        float tapeGap = float.MaxValue, passage = float.MaxValue, waypointGap = float.MaxValue;
        var waypoints = notes.Where(n => n.name.StartsWith("Waypoint")).Select(n => n.position).ToList();
        foreach (var o in drums.Concat(holes))
        {
            float r = o.localScale.x / 2;
            foreach (var edge in tapeEdges) tapeGap = Mathf.Min(tapeGap, DistanceToPolyline(o.position, edge, false) - r - Tape / 2);
            Check(RampHeightAt(o.position.x, o.position.z) == 0 && Mathf.Abs(o.position.x - XR) > RampWidth / 2 + r || Mathf.Abs(o.position.z) > -RampStart + r, "Obstacle on ramp: " + o.name);
            foreach (var w in waypoints) waypointGap = Mathf.Min(waypointGap, Vector3.Distance(Flat(o.position), Flat(w)) - r);
            if (o.GetComponent<Collider>() == null) continue;
            float d = DistanceToPolyline(o.position, path, true);
            bool lane = tapeEdges.Any(e => DistanceToPolyline(o.position, e, false) < Lane);
            // Lane drums: open side spans to opposite tape inner edge; open-area drums: corridor around reference path.
            passage = Mathf.Min(passage, lane ? d - r + Lane / 2 - Tape / 2 : 2 * (d - r));
            Check(o.position.x - r >= -AreaX / 2 && o.position.x + r <= AreaX / 2 && Mathf.Abs(o.position.z) + r <= AreaZ / 2, "Drum outside area: " + o.name);
        }
        Check(tapeGap > 0, "Obstacle overlaps tape"); Check(passage >= MinPassage, "Clear passage below 5 ft"); Check(waypointGap >= 1.5f, "Obstacle within 1.5 m of waypoint");

        json.Append("  \"area_m\": [" + F(AreaX) + ", " + F(AreaZ) + "],\n");
        json.Append("  \"footprint_m\": [" + F(bounds.size.x) + ", " + F(bounds.size.z) + "],\n");
        json.Append("  \"lane_width_m\": " + F(Lane) + ",\n  \"tape_width_m\": [" + F(tapeMin) + ", " + F(tapeMax) + "],\n");
        json.Append("  \"tape_surface_lift_m\": [" + F(tapeLift) + ", " + F(tapeLiftMax) + "],\n");
        json.Append("  \"ramp\": {\"height_m\": " + F(Find("Deck").transform.position.y + .05f) + ", \"grade\": " + F(grade) + ", \"rise_m\": " + F(rise) + ", \"width_m\": " + F(Find("Deck").transform.localScale.x) + "},\n");
        json.Append("  \"reference_path_m\": " + F(length) + ",\n  \"reference_path_ft\": " + F(length / .3048) + ",\n");
        json.Append("  \"reference_target_480_520_ft_met\": " + (length / .3048 >= 480 && length / .3048 <= 520 ? "true" : "false") + ",\n");
        json.Append("  \"min_reference_turn_radius_m\": " + F(minRadius) + ",\n  \"min_nonlocal_centreline_separation_m\": " + F(separation) + ",\n");
        json.Append("  \"drum_m\": {\"diameter\": " + F(DrumDiameter) + ", \"height\": " + F(DrumHeight) + ", \"provenance\": \"reported by interactive author from user measurements; not independently confirmed\"},\n");
        json.Append("  \"speed_check_path_distance_m\": [" + string.Join(", ", speed.Select(s => F(s))) + "],\n");
        json.Append("  \"drums\": " + drums.Count + ",\n  \"potholes\": " + holes.Count + ",\n");
        json.Append("  \"min_obstacle_tape_gap_m\": " + F(tapeGap) + ",\n  \"min_clear_passage_m\": " + F(passage) + ",\n  \"min_waypoint_obstacle_gap_m\": " + F(waypointGap) + ",\n");
        json.Append("  \"durable_meshes\": " + meshes + ",\n  \"durable_materials\": " + materials + ",\n");
        json.Append("  \"unverified\": [\"rule certification\", \"navigation success\", \"sensor appearance\", \"pothole/tire physics\", \"cropped south-edge fidelity\", \"drum dimensions\"],\n");

        string output = Path.Combine(Repository, "artifacts/agents/T-0089"); Directory.CreateDirectory(output);
        Render(Find("Overview camera").GetComponent<Camera>(), line, Path.Combine(output, "overview.png"), true);
        var oblique = new GameObject("Oblique preview camera (temporary)").AddComponent<Camera>();
        oblique.transform.position = new Vector3(AreaX * .55f, 14, -AreaZ * .75f); oblique.transform.LookAt(new Vector3(0, 0, 0));
        oblique.fieldOfView = 55; oblique.clearFlags = CameraClearFlags.SolidColor; oblique.backgroundColor = new Color(.55f, .68f, .82f);
        Render(oblique, line, Path.Combine(output, "oblique.png"), false);
        UnityEngine.Object.DestroyImmediate(oblique.gameObject);

        json.Append("  \"previews\": [\"overview.png (reference path shown)\", \"oblique.png\"],\n");
        json.Append("  \"failures\": [" + string.Join(", ", failures.Select(f => "\"" + f.Replace("\"", "'") + "\"")) + "],\n");
        json.Append("  \"passed\": " + (failures.Count == 0 ? "true" : "false") + "\n}\n");
        File.WriteAllText(Path.Combine(output, "unity-validation.json"), json.ToString());
        if (failures.Count > 0) throw new Exception("Reference map validation failed: " + string.Join("; ", failures));
        Debug.Log("IGVC_REFERENCE_MAP_OK " + F(length) + " m");
    }

    private static void Render(Camera camera, LineRenderer path, string file, bool showPath)
    {
        const int width = 1600, height = 1334;
        var previous = RenderTexture.active; var texture = new RenderTexture(width, height, 24);
        var image = new Texture2D(width, height, TextureFormat.RGB24, false);
        try
        {
            path.enabled = showPath; camera.targetTexture = texture; camera.Render();
            RenderTexture.active = texture; image.ReadPixels(new Rect(0, 0, width, height), 0, 0); image.Apply();
            File.WriteAllBytes(file, image.EncodeToPNG());
        }
        finally
        {
            path.enabled = false; camera.targetTexture = null; RenderTexture.active = previous;
            texture.Release(); UnityEngine.Object.DestroyImmediate(texture); UnityEngine.Object.DestroyImmediate(image);
        }
    }
}
