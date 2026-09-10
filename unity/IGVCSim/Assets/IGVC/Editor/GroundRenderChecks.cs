using System;
using System.IO;
using UnityEditor.SceneManagement;
using UnityEngine;

// Rendered metric-depth fixtures for independent terrain-estimator tests.
// This does not test contact physics or claim calibrated sensor behavior.
public static class GroundRenderChecks
{
    private const int Width = 320, Height = 240;

    [Serializable]
    private sealed class Fixture
    {
        public string name, encoding = "32FC1", byte_order = "little_endian", row_order = "top_left";
        public string depth_semantics = "optical_Z_metres; NaN invalid outside inclusive 0.2..10";
        public string frame = "odom", optical_frame = "camera_color_optical_frame";
        public string plane_equation = "normal_dot_point_plus_offset_equals_zero";
        public string rotation_layout = "row_major_3x3; world_point=R*optical_point+camera_origin_ros";
        public int width = Width, height = Height, valid_pixels, invalid_pixels;
        public double[] K, camera_origin_ros, rotation_optical_to_ros;
        public double[] expected_plane_normal_ros, expected_plane_point_ros;
        public double expected_plane_offset, slope_degrees, plane_height_at_ros_origin;
        public double[] obstacle_center_ros, obstacle_size_ros;
        public double obstacle_bottom_above_plane_at_center = 0.05;
        public double obstacle_top_above_plane_at_center = 0.65;
        public string obstacle_orientation = "axis_aligned_world_box";
        public double[] ground_top_center_ros, ground_local_dimensions_unity;
    }

    public static void BuildCourse()
    {
        Run();
        DepthChecks.BuildCourse();
    }

    public static void Run()
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var shader = Resources.Load<Shader>("IGVCMetricDepth");
        if (shader == null || !shader.isSupported || !SystemInfo.SupportsRenderTextureFormat(RenderTextureFormat.RFloat))
            throw new InvalidOperationException("Metric depth shader/RFloat unavailable");
        string directory = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../artifacts/checks/ground-fixtures"));
        Directory.CreateDirectory(directory);
        RenderCase(directory, shader, "flat", 0, 0);
        RenderCase(directory, shader, "raised", 0.195, 0);
        RenderCase(directory, shader, "inclined", 0.195, 10);
        Debug.Log("IGVC_GROUND_RENDER_FIXTURES_OK cases=3 path=" + directory);
    }

    private static Vector3 Ros(Vector3 unity) => new Vector3(unity.z, -unity.x, unity.y);
    private static double[] Values(Vector3 value) => new[] { (double)value.x, value.y, value.z };

    private static void RenderCase(string directory, Shader shader, string name, double originHeight, double slopeDegrees)
    {
        var camera = new GameObject("Terrain fixture camera").AddComponent<Camera>();
        var ground = GameObject.CreatePrimitive(PrimitiveType.Cube);
        var obstacle = GameObject.CreatePrimitive(PrimitiveType.Cube);
        var target = new RenderTexture(Width, Height, 24, RenderTextureFormat.RFloat, RenderTextureReadWrite.Linear);
        var texture = new Texture2D(Width, Height, TextureFormat.RFloat, false, true);
        var previous = RenderTexture.active;
        try
        {
            camera.enabled = false;
            camera.transform.SetPositionAndRotation(new Vector3(0, 1.1f, 0), Quaternion.Euler(10, 0, 0));
            camera.fieldOfView = 54;
            camera.aspect = 4f / 3;
            camera.nearClipPlane = 0.05f;
            camera.farClipPlane = 10.01f;
            camera.allowHDR = false;
            camera.allowMSAA = false;
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = Color.clear;

            // Negative Unity-X rotation raises the top surface toward forward +Z.
            // Its infinite top plane passes through world (0, originHeight, 0).
            double slope = slopeDegrees * Math.PI / 180;
            var planePoint = new Vector3(0, (float)originHeight, 0);
            var topCenter = new Vector3(0, (float)(originHeight + 4 * Math.Tan(slope)), 4);
            ground.name = "Ground top plane " + name;
            ground.transform.rotation = Quaternion.Euler((float)-slopeDegrees, 0, 0);
            ground.transform.localScale = new Vector3(6, 0.1f, 12);
            ground.transform.position = topCenter - ground.transform.up * 0.05f;
            var normal = Ros(ground.transform.up).normalized;
            var analyticNormal = new Vector3((float)-Math.Sin(slope), 0, (float)Math.Cos(slope));
            double offset = -Vector3.Dot(normal, Ros(planePoint));
            if (Vector3.Distance(normal, analyticNormal) > 1e-6
                || Math.Abs(Vector3.Dot(normal, Ros(topCenter)) + offset) > 1e-6)
                throw new Exception("Fixture plane transform does not match analytic slope");

            double obstacleGround = originHeight + 3 * Math.Tan(slope);
            obstacle.name = "Positive obstacle";
            obstacle.transform.position = new Vector3(0.8f, (float)(obstacleGround + 0.35), 3);
            obstacle.transform.localScale = new Vector3(0.4f, 0.6f, 0.4f);
            Physics.SyncTransforms();
            if (!target.Create()) throw new Exception("Ground fixture render texture creation failed");
            camera.targetTexture = target;
            camera.RenderWithShader(shader, "");
            RenderTexture.active = target;
            texture.ReadPixels(new Rect(0, 0, Width, Height), 0, 0);
            texture.Apply();
            var raw = texture.GetRawTextureData<float>();
            var right = Ros(camera.transform.right);
            var down = Ros(-camera.transform.up);
            var forward = Ros(camera.transform.forward);
            double focal = Height / (2 * Math.Tan(camera.fieldOfView * Math.PI / 360));
            var fixture = new Fixture
            {
                name = name,
                K = new[] { focal, 0, 159.5, 0, focal, 119.5, 0, 0, 1.0 },
                camera_origin_ros = Values(Ros(camera.transform.position)),
                rotation_optical_to_ros = new[] { (double)right.x, down.x, forward.x, right.y, down.y, forward.y, right.z, down.z, forward.z },
                expected_plane_normal_ros = Values(normal),
                expected_plane_point_ros = Values(Ros(planePoint)),
                expected_plane_offset = offset,
                slope_degrees = slopeDegrees,
                plane_height_at_ros_origin = originHeight,
                obstacle_center_ros = Values(Ros(obstacle.transform.position)),
                obstacle_size_ros = new[] { 0.4, 0.4, 0.6 },
                ground_top_center_ros = Values(Ros(topCenter)),
                ground_local_dimensions_unity = new[] { 6.0, 0.1, 12.0 }
            };
            using (var stream = new BinaryWriter(File.Create(Path.Combine(directory, name + ".bin"))))
                for (int row = 0; row < Height; row++)
                    for (int col = 0; col < Width; col++)
                    {
                        float depth = raw[(Height - 1 - row) * Width + col];
                        bool valid = float.IsFinite(depth) && depth >= 0.2f && depth <= 10f;
                        if (valid) fixture.valid_pixels++; else fixture.invalid_pixels++;
                        stream.Write(valid ? depth : float.NaN);
                    }
            if (fixture.valid_pixels < 100) throw new Exception("Ground fixture has insufficient rendered depth: " + name);
            File.WriteAllText(Path.Combine(directory, name + ".json"), JsonUtility.ToJson(fixture, true));
        }
        finally
        {
            RenderTexture.active = previous;
            camera.targetTexture = null;
            target.Release();
            UnityEngine.Object.DestroyImmediate(target);
            UnityEngine.Object.DestroyImmediate(texture);
            UnityEngine.Object.DestroyImmediate(camera.gameObject);
            UnityEngine.Object.DestroyImmediate(ground);
            UnityEngine.Object.DestroyImmediate(obstacle);
        }
    }
}
