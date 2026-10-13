using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using IGVC;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Independent checks of the SAVED rules drive scene (T-0091). Reopens the scene from disk and compares the actual
// transforms with the pinned authoring input: drum count/colours/positions/sizes, tape meshes, ramp, guard,
// spawn, robot mounts, persistent meshes/materials (all inside GeneratedReferenceRules), no annotations visible to
// sensors. Captures true Unity overview/oblique/sensor images under clear-noon and a low-sun overview.
// Writes artifacts/agents/T-0091/unity-validation.json (dimensions, hashes, camera data, failures). Throws on any
// failure. Never claims navigation or rule compliance.
public static class ReferenceRulesDriveChecks
{
    private static readonly CultureInfo Culture = CultureInfo.InvariantCulture;
    private static string F(double v) => v.ToString("0.#####", Culture);

    public static void Run()
    {
        var input = ReferenceRulesDriveBuild.LoadInput();
        EditorSceneManager.OpenScene(ReferenceRulesDriveBuild.DriveScene, OpenSceneMode.Single);
        var failures = new List<string>();
        void Check(bool ok, string message) { if (!ok) failures.Add(message); }
        var all = UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        var map = all.FirstOrDefault(t => t.name == ReferenceRulesDriveBuild.MapRootName);
        Check(map != null, "Map root missing");
        Vector3 origin = map != null ? map.position : Vector3.zero;
        Check(map != null && Mathf.Abs(origin.x + input.spawn.x) < 1e-3f && Mathf.Abs(origin.z + input.spawn.y) < 1e-3f, "Map not translated so the north start is the origin");
        Vector2 Field(Vector3 world) => new Vector2(world.x - origin.x, world.z - origin.z);

        // Robot, probe, guard, supports.
        var transport = UnityEngine.Object.FindFirstObjectByType<TransportProbe>();
        Check(transport != null, "TransportProbe missing");
        var serialized = transport != null ? new SerializedObject(transport) : null;
        var guard = serialized?.FindProperty("laneGuard").objectReferenceValue as LaneBoundaryGuard;
        var supports = serialized?.FindProperty("supportSurfaces");
        Check(serialized != null && serialized.FindProperty("r3aMode").boolValue, "Probe is not in R3-a mode");
        int guardSegments = guard?.CopySegments().Length ?? 0;
        Check(guardSegments > 1000, "Lane guard missing or too small: " + guardSegments);
        Check(guard != null && guard.CanOccupy(0, 0, 0), "Spawn footprint overlaps tape");
        Check(guard != null && !guard.CanOccupy(0, -1.6, 0) && !guard.CanOccupy(0, 1.6, 0), "Guard does not bound the start lane on both sides");
        Check(supports != null && supports.arraySize == 4, "Expected ground + three ramp support colliders");
        var robot = all.FirstOrDefault(t => t.name == "R3-a kinematic oracle");
        Check(robot != null, "R3-a robot missing");
        if (robot != null)
        {
            Check(Mathf.Abs(robot.position.x) < 1e-3f && Vector3.Angle(robot.forward, Vector3.forward) < .5f, "Robot not at origin heading north (+z)");
            Check(robot.GetComponentsInChildren<Camera>(true).Length >= 1, "Robot RGB camera missing");
        }
        Check(Physics.Raycast(new Vector3(0, 2, 0), Vector3.down, out var hit, 4) && Mathf.Abs(hit.point.y) < .02f, "No ground under spawn");

        // Nothing from authoring annotations reaches the sensors; one soft sun; conditions present.
        Check(all.All(t => !t.CompareTag("EditorOnly")), "EditorOnly object present in drive scene");
        Check(all.All(t => t.GetComponent<TextMesh>() == null), "Text label present in drive scene");
        Check(!all.Any(t => t.name.StartsWith("Waypoint star", StringComparison.OrdinalIgnoreCase) || t.name.StartsWith("Waypoint marker", StringComparison.OrdinalIgnoreCase)), "Waypoint marker present");
        var lights = UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        Check(lights.Count(l => l.type == LightType.Directional) == 1 && lights.All(l => l.shadows == LightShadows.Soft), "Expected exactly one soft-shadow sun");
        var conditions = UnityEngine.Object.FindFirstObjectByType<ReferenceDriveConditions>();
        Check(conditions != null, "Conditions component missing");

        // Drums: exact ids, colours, positions (<= 1 mm) and physical size against the pinned input.
        var drums = map?.Find("Drums")?.Cast<Transform>().ToList() ?? new List<Transform>();
        Check(drums.Count == ReferenceRulesDriveBuild.ExpectedDrums, "Expected " + ReferenceRulesDriveBuild.ExpectedDrums + " drums, found " + drums.Count);
        double maxDrumError = 0;
        foreach (var d in input.drums)
        {
            var t = drums.FirstOrDefault(x => x.name == d.colour + " drum " + d.id);
            if (t == null) { failures.Add("Drum missing: " + d.id); continue; }
            var at = Field(t.position); maxDrumError = Math.Max(maxDrumError, (at - new Vector2(d.x, d.y)).magnitude);
            Check(Mathf.Abs(t.lossyScale.x - ReferenceRulesDriveBuild.DrumDiameter) < 1e-4f && Mathf.Abs(t.lossyScale.y * 2 - ReferenceRulesDriveBuild.DrumHeight) < 1e-4f, "Drum size changed: " + d.id);
            Check(t.GetComponent<Collider>() != null && !t.GetComponent<Renderer>().enabled, "Drum collider/renderer state: " + d.id);
            var filter = t.Find("Drum visual")?.GetComponent<MeshFilter>(); var renderer = t.Find("Drum visual")?.GetComponent<MeshRenderer>();
            Check(filter != null && filter.sharedMesh != null && EditorUtility.IsPersistent(filter.sharedMesh) && filter.sharedMesh.subMeshCount == 3, "Drum visual mesh: " + d.id);
            Check(renderer != null && renderer.sharedMaterials.Length == 3, "Drum visual materials: " + d.id);
            if (filter != null && filter.sharedMesh != null)
            {
                var b = filter.sharedMesh.bounds;
                Check(b.extents.x <= ReferenceRulesDriveBuild.DrumDiameter / 2 + 1e-3f && b.extents.y <= ReferenceRulesDriveBuild.DrumHeight / 2 + 1e-3f, "Drum visual exceeds collider envelope: " + d.id);
            }
        }
        Check(maxDrumError <= 1e-3, "Drum position error " + F(maxDrumError) + " m");

        // Tape meshes: one per exported tape, vertex count, centre within 1 mm of the input polyline, 4 in wide.
        var tapes = map?.Find("White tape (4 in)")?.GetComponentsInChildren<MeshFilter>() ?? new MeshFilter[0];
        Check(tapes.Length == input.tapes.Count, "Tape mesh count " + tapes.Length + " != " + input.tapes.Count);
        double maxTapeError = 0, maxTapeWidthError = 0;
        for (int i = 0; i < Math.Min(tapes.Length, input.tapes.Count); i++)
        {
            var v = tapes[i].sharedMesh.vertices; var pts = input.tapes[i].points;
            Check(EditorUtility.IsPersistent(tapes[i].sharedMesh) && v.Length == 2 * pts.Count, "Tape mesh " + i + " not persistent or wrong size");
            for (int k = 0; k + 1 < v.Length && k / 2 < pts.Count; k += 2)
            {
                Vector2 a = Field(tapes[i].transform.TransformPoint(v[k])), b = Field(tapes[i].transform.TransformPoint(v[k + 1]));
                maxTapeError = Math.Max(maxTapeError, ((a + b) / 2 - new Vector2(pts[k / 2].x, pts[k / 2].y)).magnitude);
                maxTapeWidthError = Math.Max(maxTapeWidthError, Math.Abs((a - b).magnitude - ReferenceRulesDriveBuild.Tape));
            }
        }
        Check(maxTapeError <= 1e-3 && maxTapeWidthError <= 1e-3, "Tape geometry error " + F(maxTapeError) + " / width " + F(maxTapeWidthError));

        // Ramp colliders and every renderer's material persistent inside GeneratedReferenceRules.
        foreach (var part in new[] { "Ascent", "Deck", "Descent" }) Check(map?.Find("Ramp (0.30 m)/" + part)?.GetComponent<Collider>() != null, "Ramp collider missing: " + part);
        if (map != null)
            foreach (var r in map.GetComponentsInChildren<Renderer>(true))
                foreach (var m in r.sharedMaterials)
                    Check(m != null && EditorUtility.IsPersistent(m) && AssetDatabase.GetAssetPath(m).StartsWith(ReferenceRulesDriveBuild.Generated), "Material outside GeneratedReferenceRules on " + r.name);

        // Captures (true Unity renders): clear-noon overview/oblique/sensor, low-sun overview.
        string output = Path.Combine(ReferenceRulesDriveBuild.Repository, "artifacts/agents/T-0091/unity"); Directory.CreateDirectory(output);
        var captures = new List<string>(); var cameras = new List<string>();
        var ground = all.FirstOrDefault(t => t.name == "Asphalt ground (footprint)");
        if (conditions != null && robot != null && ground != null)
        {
            void Overview(Camera camera)
            {
                camera.orthographic = true; camera.orthographicSize = input.fieldH / 2 + 1;
                camera.transform.position = ground.position + Vector3.up * 60; camera.transform.rotation = Quaternion.Euler(90, 0, 0);
            }
            int ow = Mathf.RoundToInt(1000 * (input.fieldW + 2) / (input.fieldH + 2)), oh = 1000;
            conditions.Apply("clear-noon", "");
            captures.Add(Capture("clear-noon-overview", Overview, ow, oh, output, cameras));
            var eye = robot.GetComponentsInChildren<Camera>(true).First();
            captures.Add(Capture("clear-noon-sensor", camera => { camera.transform.SetPositionAndRotation(eye.transform.position, eye.transform.rotation); camera.fieldOfView = eye.fieldOfView; }, 640, 480, output, cameras));
            captures.Add(Capture("clear-noon-oblique", camera => { camera.transform.position = new Vector3(5, 4, -8); camera.transform.LookAt(new Vector3(-3, .5f, 8)); camera.fieldOfView = 60; }, 1600, 1000, output, cameras));
            conditions.Apply("low-sun", "");
            captures.Add(Capture("low-sun-overview", Overview, ow, oh, output, cameras));
        }
        else failures.Add("Captures skipped: conditions, robot or ground missing");

        string inputFile = Path.Combine(ReferenceRulesDriveBuild.Repository, ReferenceRulesDriveBuild.InputPath);
        string inputHash = BitConverter.ToString(System.Security.Cryptography.SHA256.Create().ComputeHash(File.ReadAllBytes(inputFile))).Replace("-", "").ToLowerInvariant();
        var json = new StringBuilder("{\n  \"task\": \"T-0091\",\n  \"scene\": \"" + ReferenceRulesDriveBuild.DriveScene + "\",\n");
        json.Append("  \"input\": \"" + ReferenceRulesDriveBuild.InputPath + "\", \"input_sha256\": \"" + inputHash + "\", \"variant\": \"" + input.variant + "\",\n");
        json.Append("  \"field_m\": [" + F(input.fieldW) + ", " + F(input.fieldH) + "], \"map_origin_world\": [" + F(origin.x) + ", " + F(origin.z) + "],\n");
        json.Append("  \"spawn_heading_off_north_deg\": " + F(input.spawnHeadingOffNorthDeg) + ", \"robot_heading\": \"Unity +z / ROS +x\",\n");
        json.Append("  \"drums\": " + drums.Count + ", \"max_drum_error_m\": " + F(maxDrumError) + ", \"max_tape_error_m\": " + F(maxTapeError) + ", \"max_tape_width_error_m\": " + F(maxTapeWidthError) + ",\n");
        json.Append("  \"guard_segments\": " + guardSegments + ",\n");
        json.Append("  \"captures\": [" + string.Join(", ", captures.Select(c => "\"" + c + "\"")) + "],\n");
        json.Append("  \"cameras\": [" + string.Join(", ", cameras) + "],\n");
        json.Append("  \"not_claimed\": [\"navigation success\", \"II.2 rule compliance (larger footprint, judged timing)\", \"driven-route curvature\", \"rain/fog/sensor noise\"],\n");
        json.Append("  \"failures\": [" + string.Join(", ", failures.Select(f => "\"" + f.Replace("\"", "'") + "\"")) + "],\n");
        json.Append("  \"passed\": " + (failures.Count == 0 ? "true" : "false") + "\n}\n");
        File.WriteAllText(Path.Combine(ReferenceRulesDriveBuild.Repository, "artifacts/agents/T-0091/unity-validation.json"), json.ToString());
        if (failures.Count > 0) throw new Exception("Reference rules drive validation failed: " + string.Join("; ", failures));
        Debug.Log("IGVC_REFERENCE_RULES_CHECKS_OK drums=" + drums.Count + " guard_segments=" + guardSegments);
    }

    private static string Capture(string name, Action<Camera> setup, int width, int height, string output, List<string> cameras)
    {
        var camera = new GameObject("Capture camera (temporary)").AddComponent<Camera>();
        var previous = RenderTexture.active; var texture = new RenderTexture(width, height, 24);
        var image = new Texture2D(width, height, TextureFormat.RGB24, false);
        try
        {
            camera.clearFlags = CameraClearFlags.Skybox; camera.nearClipPlane = .05f; camera.farClipPlane = 300;
            setup(camera); camera.aspect = width / (float)height; camera.targetTexture = texture; camera.Render();
            RenderTexture.active = texture; image.ReadPixels(new Rect(0, 0, width, height), 0, 0); image.Apply();
            string file = "rules-" + name + ".png"; File.WriteAllBytes(Path.Combine(output, file), image.EncodeToPNG());
            var p = camera.transform.position; var e = camera.transform.eulerAngles;
            cameras.Add("{\"file\": \"" + file + "\", \"position\": [" + F(p.x) + ", " + F(p.y) + ", " + F(p.z) + "], \"euler\": [" + F(e.x) + ", " + F(e.y) + ", " + F(e.z) +
                        "], \"orthographic\": " + (camera.orthographic ? "true" : "false") + ", \"size_or_fov\": " + F(camera.orthographic ? camera.orthographicSize : camera.fieldOfView) +
                        ", \"pixels\": [" + width + ", " + height + "]}");
            return file;
        }
        finally
        {
            camera.targetTexture = null; RenderTexture.active = previous; texture.Release();
            UnityEngine.Object.DestroyImmediate(texture); UnityEngine.Object.DestroyImmediate(image); UnityEngine.Object.DestroyImmediate(camera.gameObject);
        }
    }
}
