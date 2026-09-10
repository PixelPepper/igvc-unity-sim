using System;
using UnityEngine;

namespace IGVC
{
    /// <summary>Overview-camera-only controls, independent of ROS and sensor capture.</summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(Camera))]
    public sealed class SpectatorCamera : MonoBehaviour
    {
        [SerializeField] private Transform robot;
        [SerializeField] private Vector3 overviewPosition;
        [SerializeField] private Vector3 overviewTarget;
        private const float MinimumDistance = 1.5f;
        private const float MaximumDistance = 80f;
        private Vector3 target;
        private float distance = 5f;
        private float pitch = 25f;
        private float yaw;
        private bool following = true;
        private bool initialized;
        private bool dragging;
        private CursorLockMode previousLock;
        private bool previousVisibility;

        public bool IsFollowing => following;

        // Serialized configuration survives the editor-generated scene/player build.
        public void Configure(Transform robot, Vector3 overviewPosition, Vector3 overviewTarget)
        {
            if (robot == null) throw new ArgumentNullException(nameof(robot));
            if (robot == transform || transform.IsChildOf(robot))
                throw new ArgumentException("Spectator camera must be independent of the robot hierarchy.");
            if (!Finite(overviewPosition) || !Finite(overviewTarget)
                || (overviewPosition - overviewTarget).sqrMagnitude < 0.01f)
                throw new ArgumentException("Overview requires distinct finite position and target.");
            this.robot = robot;
            this.overviewPosition = overviewPosition;
            this.overviewTarget = overviewTarget;
            initialized = false;
        }

        private void Start()
        {
            if (robot == null)
            {
                Debug.LogError("SpectatorCamera requires Configure with a robot reference.", this);
                enabled = false;
                return;
            }
            Initialize();
        }

        private void Initialize()
        {
            following = true;
            distance = 5f;
            pitch = 25f;
            yaw = 0; // Relative to the robot's physical forward heading in follow mode.
            target = RobotTarget();
            initialized = true;
            ApplyView();
        }

        private void LateUpdate()
        {
            if (robot == null) { ReleaseCursor(); return; }
            if (!initialized) Initialize();
            if (!Application.isFocused)
            {
                ReleaseCursor();
                if (following) target = Vector3.Lerp(target, RobotTarget(), 1f - Mathf.Exp(-12f * Time.unscaledDeltaTime));
                ApplyView();
                return;
            }

            if (Input.GetKeyDown(KeyCode.F)) SetFollow(!following);
            if (Input.GetKeyDown(KeyCode.H)) ShowOverview();
            if (Input.GetKeyDown(KeyCode.Escape)) ReleaseCursor();
            bool mouseHeld = Input.GetMouseButton(1) || Input.GetMouseButton(2);
            if (Input.GetMouseButtonDown(1) || Input.GetMouseButtonDown(2)) CaptureCursor();
            if (!mouseHeld) ReleaseCursor();

            float scroll = Input.mouseScrollDelta.y;
            if (scroll != 0) distance = Mathf.Clamp(distance * Mathf.Exp(-scroll * 0.15f), MinimumDistance, MaximumDistance);
            if (dragging && Input.GetMouseButton(1))
            {
                // Legacy mouse axes are per-frame displacement, not a rate to scale by dt.
                yaw = Mathf.Repeat(yaw + Input.GetAxisRaw("Mouse X") * 3f + 180f, 360f) - 180f;
                pitch = Mathf.Clamp(pitch - Input.GetAxisRaw("Mouse Y") * 3f, -10f, 85f);
            }
            if (dragging && Input.GetMouseButton(2))
            {
                if (following) SetFollow(false);
                target -= (transform.right * Input.GetAxisRaw("Mouse X")
                    + transform.up * Input.GetAxisRaw("Mouse Y")) * (distance * 0.025f);
            }
            if (following)
            {
                float blend = 1f - Mathf.Exp(-12f * Time.unscaledDeltaTime);
                target = Vector3.Lerp(target, RobotTarget(), blend);
            }
            ApplyView();
        }

        public void SetFollow(bool value)
        {
            if (robot == null) return;
            if (!initialized) Initialize();
            if (following == value) return;
            // Keep world view heading when detaching; reattach directly behind the robot.
            if (!value) yaw += robot.eulerAngles.y;
            else
            {
                yaw = 0;
                pitch = 25f;
                distance = 5f;
                target = RobotTarget();
            }
            following = value;
            ApplyView();
        }

        public void ShowOverview()
        {
            if (robot == null) return;
            if (!initialized) Initialize();
            Vector3 direction = overviewTarget - overviewPosition;
            if (direction.sqrMagnitude < 0.01f) return;
            following = false;
            target = overviewTarget;
            distance = Mathf.Clamp(direction.magnitude, MinimumDistance, MaximumDistance);
            direction.Normalize();
            pitch = Mathf.Clamp(-Mathf.Asin(Mathf.Clamp(direction.y, -1f, 1f)) * Mathf.Rad2Deg, -10f, 85f);
            yaw = Mathf.Atan2(direction.x, direction.z) * Mathf.Rad2Deg;
            ApplyView();
        }

        private Vector3 RobotTarget() => robot.position + Vector3.up * 0.6f;

        private void ApplyView()
        {
            float heading = yaw + (following && robot != null ? robot.eulerAngles.y : 0);
            Quaternion orientation = Quaternion.Euler(pitch, heading, 0);
            transform.SetPositionAndRotation(target + orientation * Vector3.back * distance, orientation);
        }

        private void CaptureCursor()
        {
            if (dragging || !Application.isFocused) return;
            previousLock = Cursor.lockState;
            previousVisibility = Cursor.visible;
            dragging = true;
            Cursor.lockState = CursorLockMode.Locked;
            Cursor.visible = false;
        }

        private void ReleaseCursor()
        {
            if (!dragging) return;
            dragging = false;
            Cursor.lockState = previousLock;
            Cursor.visible = previousVisibility;
        }

        private void OnApplicationFocus(bool focused) { if (!focused) ReleaseCursor(); }
        private void OnApplicationPause(bool paused) { if (paused) ReleaseCursor(); }
        private void OnDisable() => ReleaseCursor();
        private void OnDestroy() => ReleaseCursor();

        private void OnGUI()
        {
            if (!initialized) return;
            float width = Mathf.Min(640f, Screen.width - 40f);
            GUI.Box(new Rect(20, Screen.height - 70, width, 50),
                "View: " + (following ? "follow robot" : "free orbit")
                + "  |  Scroll: zoom  |  RMB: orbit  |  MMB: pan\nF: toggle follow  |  H: whole course  |  Esc: release cursor");
        }

        private static bool Finite(Vector3 value) => float.IsFinite(value.x)
            && float.IsFinite(value.y) && float.IsFinite(value.z);
    }
}
