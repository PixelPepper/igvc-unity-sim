using System;
using UnityEngine;

namespace IGVC
{
    public sealed class RobotInspectionView : MonoBehaviour
    {
        [SerializeField] private Vector3 center;
        [SerializeField] private long triangles;
        [SerializeField] private float groundOffset;
        [SerializeField] private Camera inspectionCamera;
        private string capture;
        private bool saved;
        private float yaw = 45;
        public void Configure(Vector3 target, long count, float offset, Camera camera)
        { center = target; triangles = count; groundOffset = offset; inspectionCamera = camera; }
        private void Start()
        {
            Application.runInBackground = true; Application.targetFrameRate = 60;
            var args = Environment.GetCommandLineArgs();
            for (int i = 0; i + 1 < args.Length; i++) if (args[i] == "--capture") capture = args[i + 1];
        }
        private void Update()
        {
            if (!saved && !string.IsNullOrEmpty(capture) && Time.realtimeSinceStartup > 3)
            { ScreenCapture.CaptureScreenshot(capture); saved = true; }
            float change = Input.GetAxisRaw("Horizontal");
            if (change != 0)
            {
                yaw += change * 60 * Time.unscaledDeltaTime;
                inspectionCamera.transform.position = center + new Vector3(Mathf.Sin(yaw * Mathf.Deg2Rad) * 2.26f, 1f, Mathf.Cos(yaw * Mathf.Deg2Rad) * 2.26f);
                inspectionCamera.transform.LookAt(center);
            }
        }
        private void OnGUI()
        {
            GUI.Box(new Rect(20, 20, 560, 130), "R3-a • CAD DESCRIPTION INSPECTION");
            GUI.Label(new Rect(35, 48, 530, 100), $"Robot description geometry • {triangles:N0} triangles\n"
                + $"Ground presentation offset: {groundOffset:F4} m • Left/right arrows orbit\n"
                + "Static inspection: no drivetrain, sensor simulation or Nav2 in this scene.\n"
                + "Exported mass, contacts, forward direction and sensor mounts need confirmation.");
        }
    }
}
