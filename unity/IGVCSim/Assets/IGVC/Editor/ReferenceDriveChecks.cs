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

// Saved-scene validation and captures for the reference-map drive scene (T-0090). Reopens the saved scene
// and checks robot/sensor wiring, spawn, guard, support, the 95 drums and their detailed visuals, and that no
// diagram annotation is visible to sensors. Writes artifacts/agents/T-0090/drive-validation.json and
// drive-<preset>-{overview,sensor,oblique}.png. Throws on any failure.
public static class ReferenceDriveChecks
{
    private static readonly CultureInfo Culture = CultureInfo.InvariantCulture;

    public static void Run()
    {
        EditorSceneManager.OpenScene(ReferenceDriveBuild.DriveScene, OpenSceneMode.Single);
        var failures = new List<string>();
        void Check(bool ok, string message) { if (!ok) failures.Add(message); }
        var all = UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None);

        var transport = UnityEngine.Object.FindFirstObjectByType<TransportProbe>();
        Check(transport != null, "TransportProbe missing");
        var serialized = transport != null ? new SerializedObject(transport) : null;
        var guard = serialized?.FindProperty("laneGuard").objectReferenceValue as LaneBoundaryGuard;
        var supports = serialized?.FindProperty("supportSurfaces");
        Check(serialized != null && serialized.FindProperty("r3aMode").boolValue, "Probe is not in R3-a mode");
        Check(guard != null && guard.CopySegments().Length > 100, "Lane guard missing or empty");
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

        // Sensors must not see diagram annotations; only one sun and the expected cameras.
        Check(all.All(t => !t.CompareTag("EditorOnly")), "EditorOnly annotation present in drive scene");
        Check(all.All(t => t.GetComponent<TextMesh>() == null), "Text label present in drive scene");
        Check(!all.Any(t => t.name.StartsWith("Waypoint star")), "Waypoint star present");
        var lights = UnityEngine.Object.FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        Check(lights.Count(l => l.type == LightType.Directional) == 1 && lights.All(l => l.shadows == LightShadows.Soft), "Expected exactly one soft-shadow sun");
        var conditions = UnityEngine.Object.FindFirstObjectByType<ReferenceDriveConditions>();
        Check(conditions != null, "Conditions component missing");

        // Drums: 95, colliders kept, primitive renderer hidden, persistent 3-material detailed visual.
        var drums = all.FirstOrDefault(t => t.name == "Drums (traced)")?.Cast<Transform>().ToList() ?? new List<Transform>();
        Check(drums.Count == 95, "Expected 95 drums, found " + drums.Count);
        var counts = drums.GroupBy(d => d.name.Split(' ')[0]).ToDictionary(g => g.Key, g => g.Count());
        foreach (var d in drums)
        {
            Check(d.GetComponent<Collider>() != null, "Drum collider missing: " + d.name);
            Check(!d.GetComponent<Renderer>().enabled, "Primitive drum renderer still visible: " + d.name);
            var visual = d.Find("Drum visual");
            var filter = visual?.GetComponent<MeshFilter>(); var renderer = visual?.GetComponent<MeshRenderer>();
            Check(filter != null && filter.sharedMesh != null && EditorUtility.IsPersistent(filter.sharedMesh) && filter.sharedMesh.subMeshCount == 3, "Drum visual mesh not persistent: " + d.name);
            Check(renderer != null && renderer.sharedMaterials.Length == 3 && renderer.sharedMaterials.All(m => m != null && EditorUtility.IsPersistent(m)), "Drum visual materials not persistent: " + d.name);
            if (filter != null && filter.sharedMesh != null)
            {
                var b = filter.sharedMesh.bounds;   // must stay within the original cylinder envelope
                Check(b.extents.x <= ReferenceMapBuild.DrumDiameter / 2 + 1e-3f && b.extents.y <= ReferenceMapBuild.DrumHeight / 2 + 1e-3f, "Drum visual exceeds collider envelope: " + d.name);
            }
        }
        var map = all.FirstOrDefault(t => t.name == ReferenceDriveBuild.MapRootName);
        Check(map != null, "Map root missing");
        if (map != null)
            foreach (var r in map.GetComponentsInChildren<Renderer>(true))
                foreach (var m in r.sharedMaterials) Check(m != null && EditorUtility.IsPersistent(m), "Non-persistent material on " + r.name);

        // Captures with each explicit preset (editor-applied; the player applies them from --reference-conditions).
        string output = Path.Combine(ReferenceDriveBuild.Repository, "artifacts/agents/T-0090"); Directory.CreateDirectory(output);
        var captures = new List<string>();
        if (conditions != null && robot != null)
            foreach (var preset in new[] { "clear-noon", "overcast", "low-sun" })
            {
                conditions.Apply(preset, "");
                var ground = all.First(t => t.name.StartsWith("Asphalt ground"));
                captures.Add(Capture(preset + "-overview", camera =>
                {
                    camera.orthographic = true; camera.orthographicSize = ground.localScale.z / 2;
                    camera.transform.position = ground.position + Vector3.up * 40; camera.transform.rotation = Quaternion.Euler(90, 0, 0);
                }, 1049, 1160, output));
                var eye = robot.GetComponentsInChildren<Camera>(true).First();
                captures.Add(Capture(preset + "-sensor", camera =>
                {
                    camera.transform.SetPositionAndRotation(eye.transform.position, eye.transform.rotation); camera.fieldOfView = eye.fieldOfView;
                }, 640, 480, output));
                captures.Add(Capture(preset + "-oblique", camera =>
                {
                    camera.transform.position = new Vector3(4, 3, -6); camera.transform.LookAt(new Vector3(-2, .5f, 6)); camera.fieldOfView = 60;
                }, 1600, 1334, output));
            }

        var json = new StringBuilder("{\n  \"task\": \"T-0090\",\n  \"scene\": \"" + ReferenceDriveBuild.DriveScene + "\",\n");
        json.Append("  \"spawn\": \"north start line centre px (960.5, 439) = odom (0,0), heading north (Unity +z / ROS +x)\",\n");
        json.Append("  \"guard_segments\": " + (guard?.CopySegments().Length ?? 0) + ",\n");
        json.Append("  \"drums\": {" + string.Join(", ", counts.Select(c => "\"" + c.Key + "\": " + c.Value)) + "},\n");
        json.Append("  \"captures\": [" + string.Join(", ", captures.Select(c => "\"" + c + "\"")) + "],\n");
        json.Append("  \"not_claimed\": [\"navigation success\", \"full-lap audit (no generator centreline)\", \"rain/fog/sensor noise\", \"physical drum dimensions\"],\n");
        json.Append("  \"failures\": [" + string.Join(", ", failures.Select(f => "\"" + f.Replace("\"", "'") + "\"")) + "],\n");
        json.Append("  \"passed\": " + (failures.Count == 0 ? "true" : "false") + "\n}\n");
        File.WriteAllText(Path.Combine(output, "drive-validation.json"), json.ToString());
        if (failures.Count > 0) throw new Exception("Reference drive validation failed: " + string.Join("; ", failures));
        Debug.Log("IGVC_REFERENCE_DRIVE_CHECKS_OK drums=" + drums.Count + " guard_segments=" + (guard?.CopySegments().Length ?? 0));
    }

    private static string Capture(string name, Action<Camera> setup, int width, int height, string output)
    {
        var camera = new GameObject("Capture camera (temporary)").AddComponent<Camera>();
        var previous = RenderTexture.active; var texture = new RenderTexture(width, height, 24);
        var image = new Texture2D(width, height, TextureFormat.RGB24, false);
        try
        {
            camera.clearFlags = CameraClearFlags.Skybox; camera.nearClipPlane = .05f; camera.farClipPlane = 250;
            setup(camera); camera.aspect = width / (float)height; camera.targetTexture = texture; camera.Render();
            RenderTexture.active = texture; image.ReadPixels(new Rect(0, 0, width, height), 0, 0); image.Apply();
            string file = "drive-" + name + ".png"; File.WriteAllBytes(Path.Combine(output, file), image.EncodeToPNG());
            return file;
        }
        finally
        {
            camera.targetTexture = null; RenderTexture.active = previous; texture.Release();
            UnityEngine.Object.DestroyImmediate(texture); UnityEngine.Object.DestroyImmediate(image); UnityEngine.Object.DestroyImmediate(camera.gameObject);
        }
    }
}
