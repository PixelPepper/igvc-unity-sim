using System;
using System.Globalization;
using RosMessageTypes.BuiltinInterfaces;
using RosMessageTypes.Geometry;
using RosMessageTypes.Nav;
using RosMessageTypes.Rosgraph;
using RosMessageTypes.Sensor;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;

namespace IGVC
{
    public sealed class TransportProbe : MonoBehaviour
    {
        [SerializeField] private Transform robot;
        [SerializeField] private Camera sensorCamera;
        [SerializeField] private bool r3aMode;
        [SerializeField] private Transform leftWheel;
        [SerializeField] private Transform rightWheel;
        [SerializeField] private Transform lidarFrame;
        [SerializeField] private Transform cameraMount;
        [SerializeField] private LaneBoundaryGuard laneGuard;
        [SerializeField] private Collider[] supportSurfaces;
        private bool TerrainMode => supportSurfaces != null && supportSurfaces.Length > 0;
        [SerializeField] private Transform leftCasterSlider, rightCasterSlider;
        [SerializeField] private CasterSettings casterSettings;
        private CasterTerrainSupport casterSupport;
        private bool CasterMode => casterSupport != null;
        private Vector3 leftCasterRest, rightCasterRest;
        private double leftSliderVelocity, rightSliderVelocity;
        [SerializeField] private Transform leftCaster, rightCaster;
        [SerializeField] private CasterSwivelSettings swivelSettings;
        private CasterSwivel leftSwivel, rightSwivel;
        private double planarLinear;
        [SerializeField] private double defaultCameraPitch = .17453292519943295;
        private string courseIdentity = "reference";
        private double cameraPitch, targetPitch, cameraPitchVelocity;
        private readonly R3aKinematics drive = new R3aKinematics();
        private ROSConnection ros;
        private readonly ProbeMotion motion = new ProbeMotion();
        private long ticks;
        private double elapsed;
        private double nextScan;
        private double quitAt;
        private double captureAt;
        private string capturePath;
        private int runId;
        private ProbeCamera cameraPublisher;
        private ProbeDepthCamera depthPublisher;
        [Serializable] private sealed class StoppedCheckpoint
        {
            public double x, y, yaw, sim_time;
            public int run_id;
        }
        public double SimTime => ticks * 0.01;

        public void Configure(Transform body, Camera camera) { robot = body; sensorCamera = camera; }
        public void ConfigureR3a(Transform body, Camera camera, Transform left, Transform right, Transform lidar)
        { Configure(body, camera); r3aMode = true; leftWheel = left; rightWheel = right; lidarFrame = lidar; }
        public void ConfigureCameraMount(Transform mount) { cameraMount = mount; }
        public void ConfigureLaneGuard(LaneBoundaryGuard guard) { laneGuard = guard; }
        public void ConfigureTerrain(Collider[] surfaces) { supportSurfaces = surfaces; }
        public void ConfigureCasters(Transform left, Transform right, CasterSettings settings)
        { leftCasterSlider = left; rightCasterSlider = right; casterSettings = settings; }
        public void ConfigureCasterSwivel(Transform left,Transform right,CasterSwivelSettings settings)
        {leftCaster=left;rightCaster=right;swivelSettings=settings;}
        public void ConfigureCameraDefaultPitch(double value) { defaultCameraPitch = Math.Clamp(value, -Math.PI/6, Math.PI/6); }

        // Generated ROS message registrars run after scene Awake; register topics in Start.
        private bool scoreLinesOnly;
        private void Start()
        {
            Application.runInBackground = true;
            Application.targetFrameRate = 60;
            QualitySettings.vSyncCount = 0;
            Time.fixedDeltaTime = 0.01f;
            Time.maximumDeltaTime = 0.1f;
            if (robot == null || sensorCamera == null) throw new InvalidOperationException("Probe references missing; rebuild the scene.");
            if (r3aMode && (leftWheel == null || rightWheel == null || lidarFrame == null || cameraMount == null))
                throw new InvalidOperationException("R3-a wheel/lidar references missing; rebuild the scene.");
            ros = ROSConnection.GetOrCreateInstance();
            string variantPath = Arg("--course-manifest", "");
            scoreLinesOnly = Arg("--line-guard", "enforce") == "scoring";
            if (!string.IsNullOrEmpty(variantPath))
            {
                if (!r3aMode || laneGuard == null) throw new InvalidOperationException("Variants require the course scene");
                var variant = CourseVariant.Load(variantPath, laneGuard);
                defaultCameraPitch = variant.camera_pitch_rad;
                courseIdentity = "seed-" + variant.seed + " course_hash=" + variant.runtime_hash;
                ConfigureTerrain(variant.support_surfaces);
            }
            defaultCameraPitch = Math.Clamp(ParseDouble(Arg("--camera-pitch-deg", (defaultCameraPitch * 180 / Math.PI).ToString(CultureInfo.InvariantCulture))) * Math.PI / 180, -Math.PI/6, Math.PI/6);
            cameraPitch = targetPitch = defaultCameraPitch;
            if (r3aMode)
            {
                if (leftCasterSlider == null || rightCasterSlider == null || casterSettings == null)
                    throw new InvalidOperationException("Caster slider references missing; rebuild the R3-a player");
                casterSettings.Validate();
                leftCasterRest = leftCasterSlider.localPosition;
                rightCasterRest = rightCasterSlider.localPosition;
                if(leftCaster==null || rightCaster==null || swivelSettings==null)
                    throw new InvalidOperationException("Caster swivel references missing; rebuild R3-a player");
                leftSwivel=swivelSettings.Create();rightSwivel=swivelSettings.Create();
                if (TerrainMode && Arg("--caster-suspension", "on") != "off")
                    casterSupport = new CasterTerrainSupport(casterSettings, supportSurfaces);
                ResetCasterSupport();
            }
            ApplyPose();
            ros.ConnectOnStart = false;
            ros.ShowHud = false;
            ros.NetworkTimeoutSeconds = 2;
            // Small bounded buffers absorb multiple fixed ticks between rendered frames.
            ros.RegisterPublisher<ClockMsg>("/clock", 10);
            ros.RegisterPublisher<OdometryMsg>("/sim/ground_truth/odom", 10);
            if (r3aMode) ros.RegisterPublisher<TransformStampedMsg>("/sim/body_transform", 10);
            ros.RegisterPublisher<JointStateMsg>("/joint_states", 10);
            if (CasterMode) ros.RegisterPublisher<JointStateMsg>("/sim/suspension_state", 10);
            ros.RegisterPublisher<LaserScanMsg>("/scan", 1);
            ros.RegisterPublisher<StringMsg>("/sim/status", 1);
            ros.Subscribe<TwistStampedMsg>("/sim/drive_command", m => motion.Command(
                m.twist.linear.x, m.twist.angular.z, m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
                SimTime, Time.realtimeSinceStartupAsDouble));
            if (r3aMode) ros.Subscribe<Float64Msg>("/sim/camera_pitch_command", m =>
            {
                if (!motion.Paused && !motion.Stopped && double.IsFinite(m.data))
                    targetPitch = Math.Clamp(m.data, -Math.PI / 6, Math.PI / 6);
            });
            ros.ImplementService<SetBoolRequest, SetBoolResponse>("/sim/pause", m =>
            {
                motion.SetPaused(m.data, SimTime);
                return new SetBoolResponse(true, m.data ? "Probe paused" : "Probe resumed; fresh command required");
            });
            ros.ImplementService<SetBoolRequest, SetBoolResponse>("/sim/estop", m =>
            {
                motion.SetStopped(m.data, SimTime);
                return new SetBoolResponse(true, m.data ? "Simulated stop latched" : "Stop cleared; fresh command required");
            });
            ros.ImplementService<TriggerRequest, TriggerResponse>("/sim/reset", _ =>
            {
                motion.Reset(SimTime);
                drive.Reset();
                if (laneGuard != null) laneGuard.Clear();
                cameraPitch = targetPitch = defaultCameraPitch;
                cameraPitchVelocity = 0;
                ResetCasterSupport();
                ApplyPose();
                runId++;
                return new TriggerResponse(true, "Probe pose reset; clock remains monotonic; run=" + runId);
            });
            quitAt = ParseDouble(Arg("--quit-after", "0"));
            capturePath = Arg("--capture", "");
            captureAt = ParseDouble(Arg("--capture-after", "5"));
            string checkpointPath = Arg("--resume-state", "");
            if (!string.IsNullOrEmpty(checkpointPath))
            {
                var saved = JsonUtility.FromJson<StoppedCheckpoint>(System.IO.File.ReadAllText(checkpointPath));
                if (!r3aMode || laneGuard == null || saved == null
                    || !double.IsFinite(saved.x) || !double.IsFinite(saved.y) || !double.IsFinite(saved.yaw)
                    || !double.IsFinite(saved.sim_time) || saved.sim_time <= 0 || saved.sim_time > 1e8
                    || Math.Abs(saved.x) > 100 || Math.Abs(saved.y) > 100 || saved.run_id < 0
                    || !laneGuard.CanOccupy(saved.x, saved.y, saved.yaw))
                    throw new InvalidOperationException("Invalid or paint-overlapping stopped checkpoint");
                ticks = (long)Math.Round(saved.sim_time / .01);
                runId = saved.run_id;
                drive.RestoreStoppedPose(saved.x, saved.y, saved.yaw);
                motion.Reset(SimTime);
                ResetCasterSupport();
                ApplyPose();
                Debug.Log("Restored stopped course checkpoint before ROS connection; wheel animation phases reset, no velocity restored.");
            }
            cameraPublisher = sensorCamera.gameObject.AddComponent<ProbeCamera>();
            cameraPublisher.Initialize(ros, this);
            depthPublisher = sensorCamera.gameObject.AddComponent<ProbeDepthCamera>();
            depthPublisher.Initialize(ros, this, sensorCamera);
            ros.Connect(Arg("--ros-ip", "127.0.0.1"), int.Parse(Arg("--ros-port", "10000"), CultureInfo.InvariantCulture));
            Debug.Log(r3aMode ? "IGVC R3-a kinematic oracle started; CAD geometry, provisional sensors, external ROS navigation, no contact physics."
                : "IGVC transport probe started; ideal motion, synthetic scan/RGB, no CAD or Nav2.");
        }

        private void FixedUpdate()
        {
            if (!motion.Paused) ticks++;
            motion.Step(motion.Paused ? 0 : 0.01, Time.realtimeSinceStartupAsDouble, !ros.HasConnectionError);
            if (r3aMode && !motion.Paused)
            {
                if (laneGuard != null && !laneGuard.AllowsMotion(drive.AxleX, drive.AxleY, drive.Yaw, motion.Linear, motion.Angular, .01) && !scoreLinesOnly)
                    motion.RejectMotion(SimTime);
                planarLinear = motion.Linear;
                if (TerrainMode)
                {
                    double mid = drive.Yaw + motion.Angular*.005;
                    var baseOffset=new Vector3(0,.30385548f,-.25591f);
                    float oldHeight=(robot.position-robot.rotation*baseOffset).y;
                    bool accepted=false;
                    for(int attempt=0;attempt<6;attempt++)
                    {
                        double half = motion.Angular * .005;
                        double sinc = Math.Abs(half) < 1e-4 ? 1-half*half/6+half*half*half*half/120 : Math.Sin(half)/half;
                        var next = new Vector3((float)-(drive.AxleY+planarLinear*sinc*Math.Sin(mid)*.01),0,
                            (float)(drive.AxleX+planarLinear*sinc*Math.Cos(mid)*.01));
                        float nextYaw=(float)(-(drive.Yaw+motion.Angular*.01)*Mathf.Rad2Deg);
                        Vector3 bodyPosition; Quaternion bodyRotation;
                        CasterTerrainSupport.Candidate sprung = null;
                        if (CasterMode)
                        {
                            if (!casterSupport.TryPreview(next,nextYaw,.01,false,out sprung)) break;
                            bodyPosition=sprung.Position;bodyRotation=sprung.Rotation;
                        }
                        else if (!TerrainSupport.TryPose(next,nextYaw,supportSurfaces,out bodyPosition,out bodyRotation)) break;
                        double rise=(bodyPosition-bodyRotation*baseOffset).y-oldHeight;
                        double distance=Math.Sqrt(planarLinear*planarLinear*sinc*sinc*.0001+rise*rise);
                        double budget=Math.Abs(motion.Linear)*.01;
                        if(distance<=budget+1e-7)
                        {
                            accepted=true;
                            if(CasterMode) CommitCasters(sprung);
                            break;
                        }
                        planarLinear*=budget/distance*.9999;
                    }
                    if(!accepted)
                    {
                        motion.RejectMotion(SimTime);planarLinear=0;
                        if(CasterMode && casterSupport.TryPreview(new Vector3((float)-drive.AxleY,0,(float)drive.AxleX),
                            (float)(-drive.Yaw*Mathf.Rad2Deg),.01,false,out var settled)) CommitCasters(settled);
                    }
                }
                drive.Step(planarLinear, motion.Angular, 0.01);
            }
            if (r3aMode)
            {
                double previous = cameraPitch;
                if (motion.Paused || motion.Stopped) targetPitch = cameraPitch;
                else cameraPitch += Math.Clamp(targetPitch - cameraPitch, -.01, .01);
                cameraPitchVelocity = (cameraPitch - previous) / .01;
            }
            ApplyPose();
            if(r3aMode) UpdateCasterSwivels();
            if (ros.HasConnectionError) return;
            ros.Publish("/clock", new ClockMsg(Stamp()));
            if (ticks % 2 == 0 && !motion.Paused)
            {
                var odom = new OdometryMsg { header = Header("odom"), child_frame_id = "base_footprint" };
                double x = r3aMode ? drive.AxleX : motion.X, y = r3aMode ? drive.AxleY : motion.Y;
                double yaw = r3aMode ? drive.Yaw : motion.Yaw;
                odom.pose.pose.position = new PointMsg(x, y, 0);
                odom.pose.pose.orientation = new QuaternionMsg(0, 0, Math.Sin(yaw / 2), Math.Cos(yaw / 2));
                odom.twist.twist.linear.x = r3aMode ? planarLinear : motion.Linear;
                odom.twist.twist.angular.z = motion.Angular;
                ros.Publish("/sim/ground_truth/odom", odom);
                if (r3aMode)
                {
                    Quaternion flat = Quaternion.Euler(0,(float)(-drive.Yaw*Mathf.Rad2Deg),0);
                    Quaternion relative = Quaternion.Inverse(flat)*robot.rotation;
                    Vector3 offset = Quaternion.Inverse(flat)*(robot.position-new Vector3((float)-drive.AxleY,0,(float)drive.AxleX));
                    var body = new TransformStampedMsg { header=Header("base_footprint"),child_frame_id="base_link" };
                    body.transform.translation=new Vector3Msg(offset.z,-offset.x,offset.y);
                    body.transform.rotation=new QuaternionMsg(-relative.z,relative.x,-relative.y,relative.w);
                    ros.Publish("/sim/body_transform",body);
                }
                // Synthetic feedback in this transport fixture; not encoder simulation.
                ros.Publish("/joint_states", r3aMode
                    ? new JointStateMsg(Header("base_link"), new[] { "leftWheel", "rightWheel", "leftCaster", "rightCaster", "camera_pitch_joint", "left_caster_suspension_joint", "right_caster_suspension_joint" },
                        new[] { drive.LeftWheelPosition, drive.RightWheelPosition, leftSwivel.Angle, rightSwivel.Angle, cameraPitch, CasterMode ? casterSupport.Current.LeftJoint : 0, CasterMode ? casterSupport.Current.RightJoint : 0 },
                        new[] { (planarLinear - R3aKinematics.TrackWidth * motion.Angular / 2) / R3aKinematics.WheelRadius,
                            -(planarLinear + R3aKinematics.TrackWidth * motion.Angular / 2) / R3aKinematics.WheelRadius, leftSwivel.Velocity, rightSwivel.Velocity, cameraPitchVelocity, leftSliderVelocity, rightSliderVelocity }, new double[0])
                    : new JointStateMsg(Header("base_link"), new[] { "left_wheel_joint", "right_wheel_joint" }, new double[2],
                        new[] { (motion.Linear - 0.4 * motion.Angular) / 0.15, (motion.Linear + 0.4 * motion.Angular) / 0.15 }, new double[0]));
                if (CasterMode)
                {
                    var state=casterSupport.Current;
                    ros.Publish("/sim/suspension_state",new JointStateMsg(Header("base_link"),
                        new[]{"rear_body_height","left_compression","right_compression"},
                        new[]{state.Height,state.Left,state.Right},new[]{state.Velocity,state.LeftRate,state.RightRate},new double[0]));
                }
            }
            if (!motion.Paused && SimTime >= nextScan) { nextScan = SimTime + 1.0 / 5.5; PublishScan(); }
        }

        private void ApplyPose()
        {
            if (r3aMode)
            {
                robot.position = new Vector3((float)-drive.BaseY, .30385548f, (float)drive.BaseX);
                robot.rotation = Quaternion.Euler(0, (float)(-drive.Yaw * Mathf.Rad2Deg), 0);
                if (CasterMode)
                    robot.SetPositionAndRotation(casterSupport.Current.Position,casterSupport.Current.Rotation);
                else if (TerrainMode)
                {
                    if (!TerrainSupport.TryPose(new Vector3((float)-drive.AxleY,0,(float)drive.AxleX),
                        (float)(-drive.Yaw*Mathf.Rad2Deg),supportSurfaces,out Vector3 position,out Quaternion rotation))
                        throw new InvalidOperationException("Terrain support unavailable; body pose must not fall back to flat ground");
                    robot.SetPositionAndRotation(position,rotation);
                }
                leftCasterSlider.localPosition=leftCasterRest+Vector3.up*(float)(CasterMode ? casterSupport.Current.LeftJoint : 0);
                rightCasterSlider.localPosition=rightCasterRest+Vector3.up*(float)(CasterMode ? casterSupport.Current.RightJoint : 0);
                ApplyCasterSwivels();
                leftWheel.localRotation = Quaternion.AngleAxis((float)(drive.LeftWheelPosition * Mathf.Rad2Deg), Vector3.right);
                rightWheel.localRotation = Quaternion.AngleAxis((float)(drive.RightWheelPosition * Mathf.Rad2Deg), Vector3.left);
                cameraMount.localRotation = Quaternion.AngleAxis((float)(cameraPitch * Mathf.Rad2Deg), Vector3.right);
                return;
            }
            robot.position = new Vector3((float)-motion.Y, 0.35f, (float)motion.X);
            robot.rotation = Quaternion.Euler(0, (float)(-motion.Yaw * Mathf.Rad2Deg), 0);
        }

        private void ResetCasterSupport()
        {
            leftSliderVelocity=rightSliderVelocity=0;
            leftSwivel?.Reset();rightSwivel?.Reset();
            if(!CasterMode)return;
            if(!casterSupport.TryPreview(new Vector3((float)-drive.AxleY,0,(float)drive.AxleX),
                (float)(-drive.Yaw*Mathf.Rad2Deg),0,true,out var initial))
                throw new InvalidOperationException("Initial caster supports unavailable or exceed travel/slope limits");
            casterSupport.Commit(initial);
        }

        private void CommitCasters(CasterTerrainSupport.Candidate next)
        {
            leftSliderVelocity=(next.LeftJoint-casterSupport.Current.LeftJoint)/.01;
            rightSliderVelocity=(next.RightJoint-casterSupport.Current.RightJoint)/.01;
            casterSupport.Commit(next);
        }

        private void UpdateCasterSwivels()
        {
            // Nominal pivot velocities from the accepted planar axle twist. Project into
            // the tilted body plane for yaw about the URDF swivel's local +Z axis.
            Quaternion footprint=Quaternion.Euler(0,(float)(-drive.Yaw*Mathf.Rad2Deg),0);
            Quaternion toBody=Quaternion.Inverse(robot.rotation)*footprint;
            void Advance(CasterSwivel swivel,Vector3 rest)
            {
                double pivotX=R3aKinematics.BaseOffsetX+rest.z, pivotY=-rest.x;
                var velocity=toBody*new Vector3((float)(-motion.Angular*pivotX),0,
                    (float)(planarLinear-motion.Angular*pivotY));
                if(!swivel.Step(velocity.z,-velocity.x,motion.Paused ? 0 : .01))
                    throw new InvalidOperationException("Invalid caster swivel velocity/state");
            }
            Advance(leftSwivel,leftCasterRest);Advance(rightSwivel,rightCasterRest);
            ApplyCasterSwivels();
        }

        private void ApplyCasterSwivels()
        {
            // ROS +Z yaw is Unity -Y yaw; preserve the canonical URDF joint signs.
            leftCaster.localRotation=Quaternion.AngleAxis((float)(-leftSwivel.Angle*Mathf.Rad2Deg),Vector3.up);
            rightCaster.localRotation=Quaternion.AngleAxis((float)(-rightSwivel.Angle*Mathf.Rad2Deg),Vector3.up);
        }

        private void PublishScan()
        {
            const int count = 360;
            var scan = new LaserScanMsg { header = Header("lidar_link"), angle_min = -Mathf.PI,
                angle_max = Mathf.PI - 2 * Mathf.PI / count, angle_increment = 2 * Mathf.PI / count,
                scan_time = 1f / 5.5f, time_increment = 0, range_min = 0.15f, range_max = 12,
                ranges = new float[count], intensities = new float[0] };
            Vector3 origin = r3aMode ? lidarFrame.position : robot.position + Vector3.up * 0.35f;
            for (int i = 0; i < count; i++)
            {
                double angle = (r3aMode ? 0 : motion.Yaw) + scan.angle_min + i * scan.angle_increment;
                Vector3 direction = new Vector3((float)-Math.Sin(angle), 0, (float)Math.Cos(angle));
                if (r3aMode) direction = lidarFrame.TransformDirection(direction);
                scan.ranges[i] = Physics.Raycast(origin, direction, out RaycastHit hit, 12, 1 << 0)
                    ? (hit.distance >= 0.15f ? hit.distance : float.NaN) : float.PositiveInfinity;
            }
            ros.Publish("/scan", scan);
        }

        private void Update()
        {
            elapsed = Time.realtimeSinceStartupAsDouble;
            if (elapsed >= quitAt && quitAt > 0) Application.Quit();
            if (capturePath.Length > 0 && elapsed >= captureAt)
            {
                ScreenCapture.CaptureScreenshot(capturePath);
                capturePath = "";
            }
            if (Time.frameCount % 60 == 0 && !ros.HasConnectionError)
                ros.Publish("/sim/status", new StringMsg($"{(r3aMode ? "r3a_kinematic_oracle" : "probe")} run={runId} course={courseIdentity} terrain_support={TerrainMode} caster_suspension={CasterMode} camera_pitch={cameraPitch:F4} paused={motion.Paused} estop={motion.Stopped} line_guard={(scoreLinesOnly ? "scoring" : "enforce")} line_blocks={laneGuard?.BlockedSteps ?? 0} sim={SimTime:F2} {cameraPublisher.Diagnostics} {depthPublisher.Diagnostics}"));
        }

        private void OnGUI()
        {
            GUI.Box(new Rect(20, 20, 570, 135), r3aMode ? "R3-a • KINEMATIC ORACLE" : "IGVC • TRANSPORT PROBE");
            GUI.Label(new Rect(35, 48, 460, 100), $"ROS: {(ros.HasConnectionError ? "connecting" : "connected")}   |   sim: {SimTime:F2} s\n"
                    + $"ROS axle pose: x {(r3aMode ? drive.AxleX : motion.X):F2} m, y {(r3aMode ? drive.AxleY : motion.Y):F2} m\n"
                + $"Pause: {motion.Paused}   Stop: {motion.Stopped}   Run: {runId}\n"
                + (CasterMode ? $"Rear spring/damper • L {casterSupport.Current.Left*1000:F1} / R {casterSupport.Current.Right*1000:F1} mm • provisional"
                    : TerrainMode ? "EXPERIMENTAL rigid terrain support • no traction" : r3aMode ? "CAD robot • ideal motion • provisional RGB/lidar • no contacts" : "Ideal test body • terminal control • synthetic RGB and lidar"));
        }
        public bool IsPaused => motion.Paused;
        public int RunId => runId;
        public TimeMsg Stamp() => new TimeMsg((int)(ticks / 100), (uint)(ticks % 100 * 10000000));
        public HeaderMsg Header(string frame) => new HeaderMsg(Stamp(), frame);
        private static double ParseDouble(string text) => double.Parse(text, CultureInfo.InvariantCulture);
        private static string Arg(string key, string fallback)
        {
            string[] args = Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++) if (args[i] == key) return args[i + 1];
            return fallback;
        }
    }
}
