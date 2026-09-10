using System;
using RosMessageTypes.Sensor;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;
using UnityEngine.Rendering;

namespace IGVC
{
    [RequireComponent(typeof(Camera))]
    public sealed class ProbeCamera : MonoBehaviour
    {
        private ROSConnection ros;
        private TransportProbe probe;
        private Camera cameraComponent;
        private RenderTexture target;
        private bool pending;
        private bool alive;
        private double nextCapture;
        private int captures;
        private int completions;
        private int errors;
        private double totalReadbackSeconds;
        public string Diagnostics => $"rgb requested={captures} completed={completions} errors={errors} meanReadbackMs={(completions > 0 ? totalReadbackSeconds * 1000 / completions : 0):F1}";
        public void Initialize(ROSConnection connection, TransportProbe owner)
        {
            ros = connection;
            probe = owner;
            cameraComponent = GetComponent<Camera>();
            target = new RenderTexture(640, 480, 24, RenderTextureFormat.ARGB32);
            target.Create();
            cameraComponent.targetTexture = target;
            cameraComponent.aspect = 640f / 480;
            cameraComponent.enabled = false;
            ros.RegisterPublisher<ImageMsg>("/camera/color/image_raw", 1);
            ros.RegisterPublisher<CameraInfoMsg>("/camera/color/camera_info", 1);
            alive = true;
        }
        private void LateUpdate()
        {
            if (!alive || pending || ros.HasConnectionError || probe.IsPaused || probe.SimTime < nextCapture) return;
            nextCapture = probe.SimTime + 1.0 / 15;
            var header = probe.Header("camera_color_optical_frame");
            double requestedAt = Time.realtimeSinceStartupAsDouble;
            captures++;
            cameraComponent.Render();
            pending = true;
            AsyncGPUReadback.Request(target, 0, TextureFormat.RGB24, request =>
            {
                pending = false;
                completions++;
                totalReadbackSeconds += Time.realtimeSinceStartupAsDouble - requestedAt;
                if (request.hasError) errors++;
                if (!alive || request.hasError || ros.HasConnectionError) return;
                var source = request.GetData<byte>();
                var pixels = new byte[640 * 480 * 3];
                // Unity readback starts at the lower row; ROS images start at the upper row.
                for (int row = 0; row < 480; row++)
                    Unity.Collections.NativeArray<byte>.Copy(source, row * 1920, pixels, (479 - row) * 1920, 1920);
                ros.Publish("/camera/color/image_raw", new ImageMsg(header, 480, 640, "rgb8", 0, 1920, pixels));
                ros.Publish("/camera/color/camera_info", Calibration(header));
            });
        }
        private CameraInfoMsg Calibration(HeaderMsg header)
        {
            // Exact intrinsics for this ideal Unity pinhole, not the physical OAK device calibration.
            double f = 480 / (2 * Math.Tan(cameraComponent.fieldOfView * Math.PI / 360));
            return new CameraInfoMsg { header = header, width = 640, height = 480, distortion_model = "plumb_bob",
                D = new double[5], K = new[] { f, 0, 319.5, 0, f, 239.5, 0, 0, 1.0 },
                R = new[] { 1.0, 0, 0, 0, 1, 0, 0, 0, 1 },
                P = new[] { f, 0, 319.5, 0, 0, f, 239.5, 0, 0, 0, 1, 0 } };
        }
        private void OnDestroy()
        {
            alive = false;
            if (cameraComponent != null) cameraComponent.targetTexture = null;
            if (pending) AsyncGPUReadback.WaitAllRequests();
            if (target != null) { target.Release(); Destroy(target); }
        }
    }
}
