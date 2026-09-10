using System;
using System.IO;
using IGVC;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class R3aDriveBuild
{
    [Serializable] private class CameraDefaults { public double default_simulation_pitch_rad; }
    public static void Capture()
    {
        EditorSceneManager.OpenScene("Assets/IGVC/GeneratedRobot/R3aDrive.unity");
        var camera = GameObject.Find("Overview Camera").GetComponent<Camera>();
        var target = new RenderTexture(1280, 800, 24);
        var pixels = new Texture2D(1280, 800, TextureFormat.RGB24, false);
        var previous = RenderTexture.active;
        try
        {
            camera.targetTexture = target; camera.Render(); RenderTexture.active = target;
            pixels.ReadPixels(new Rect(0, 0, 1280, 800), 0, 0); pixels.Apply();
            File.WriteAllBytes(Path.GetFullPath(Path.Combine(Application.dataPath, "../../../artifacts/checks/r3a-drive-editor.png")), pixels.EncodeToPNG());
            var lidar = GameObject.Find("lidar_link").transform;
            camera.nearClipPlane = .005f;
            camera.transform.position = lidar.position + new Vector3(.18f, .16f, .22f);
            camera.transform.LookAt(lidar.position - Vector3.up * .01f);
            camera.Render(); pixels.ReadPixels(new Rect(0, 0, 1280, 800), 0, 0); pixels.Apply();
            File.WriteAllBytes(Path.GetFullPath(Path.Combine(Application.dataPath, "../../../artifacts/checks/lidar-mount-editor.png")), pixels.EncodeToPNG());
            var mountedCamera = GameObject.Find("camera_link").transform;
            camera.transform.position = mountedCamera.position + new Vector3(.16f, .10f, .20f);
            camera.transform.LookAt(mountedCamera.position - Vector3.up * .015f);
            camera.Render(); pixels.ReadPixels(new Rect(0, 0, 1280, 800), 0, 0); pixels.Apply();
            File.WriteAllBytes(Path.GetFullPath(Path.Combine(Application.dataPath, "../../../artifacts/checks/camera-mount-editor.png")), pixels.EncodeToPNG());
        }
        finally
        {
            camera.targetTexture = null; RenderTexture.active = previous;
            target.Release(); UnityEngine.Object.DestroyImmediate(target); UnityEngine.Object.DestroyImmediate(pixels);
        }
    }
    public static void Build()
    {
        CreateScene();
        BuildScene("Assets/IGVC/GeneratedRobot/R3aDrive.unity", "build-drive/R3aDrive.exe");
        Debug.Log("IGVC_R3A_DRIVE_BUILD_OK");
    }

    public static void CreateScene()
    {
        ProbeChecks.Run();
        R3aKinematicsChecks.Run();
        CasterSwivelChecks.Run();
        ProbeBuild.CreateScene();
        var transport = UnityEngine.Object.FindFirstObjectByType<TransportProbe>();
        var placeholder = GameObject.Find("Ideal Probe Body");
        var sensor = placeholder.GetComponentInChildren<Camera>();
        var root = RobotInspectionBuild.CreateRobot(true);
        root.name = "R3-a kinematic oracle";
        var baseLink = root.transform.Find("base_link");
        var pitchMount = baseLink.Find("camera_mount_link");
        var cameraBody = pitchMount.Find("camera_link");
        var optical = cameraBody.Find("camera_color_optical_frame");
        sensor.transform.SetParent(cameraBody, false);
        sensor.transform.localPosition = optical.localPosition;
        sensor.transform.localRotation = Quaternion.identity;
        sensor.transform.localScale = Vector3.one;
        UnityEngine.Object.DestroyImmediate(placeholder);
        // Visual hierarchy has no colliders: contact/slip and self-occlusion are later fidelity work.
        transport.ConfigureR3a(root.transform, sensor, baseLink.Find("wheel_left"), baseLink.Find("wheel_right"), baseLink.Find("lidar_link"));
        transport.ConfigureCameraMount(pitchMount);
        var casterSettings=JsonUtility.FromJson<CasterSettings>(File.ReadAllText(Path.GetFullPath(Path.Combine(Application.dataPath,
            "../../../ros2/src/igvc_description/config/caster_suspension.json"))));
        casterSettings.Validate();
        Transform Slider(string side)
        {
            var caster=baseLink.Find(side+"_caster");
            if(caster==null || caster.localPosition.z>=0) throw new Exception("Rear caster visual missing");
            var slider=new GameObject(side+"_caster_suspension_link").transform;
            slider.SetParent(baseLink,false);slider.localPosition=caster.localPosition;
            caster.SetParent(slider,false);caster.localPosition=Vector3.zero;
            return slider;
        }
        transport.ConfigureCasters(Slider("left"),Slider("right"),casterSettings);
        var swivelSettings=JsonUtility.FromJson<CasterSwivelSettings>(File.ReadAllText(Path.GetFullPath(Path.Combine(Application.dataPath,
            "../../../ros2/src/igvc_description/config/caster_swivel.json"))));
        swivelSettings.Create();
        transport.ConfigureCasterSwivel(baseLink.Find("left_caster_suspension_link/left_caster"),
            baseLink.Find("right_caster_suspension_link/right_caster"),swivelSettings);
        var defaults = JsonUtility.FromJson<CameraDefaults>(File.ReadAllText(Path.GetFullPath(Path.Combine(Application.dataPath,
            "../../../ros2/src/igvc_description/config/camera_mount.json"))));
        transport.ConfigureCameraDefaultPitch(defaults.default_simulation_pitch_rad);
        if ((sensor.transform.forward - optical.up).magnitude > 1e-5f || (sensor.transform.up - optical.right).magnitude > 1e-5f)
            throw new Exception("Unity camera directions disagree with ROS optical frame");
        root.transform.position = new Vector3(0, .30385548f, (float)R3aKinematics.BaseOffsetX);
        var lidar = baseLink.Find("lidar_link");
        var lidarBounds = lidar.GetComponentInChildren<MeshRenderer>().bounds;
        if (lidar.localPosition.z <= 0 || lidarBounds.size.x < .05f || lidarBounds.size.x > .15f
            || lidarBounds.size.y < .02f || lidarBounds.size.y > .15f || lidarBounds.size.z < .05f || lidarBounds.size.z > .15f)
            throw new Exception("Lidar front placement or metre-scale bounds invalid");
        var mountEvidence = new LidarEvidence { scanFrameWorldUnity = lidar.position,
            scanForwardWorldUnity = lidar.forward, visualMinimumWorldUnity = lidarBounds.min,
            visualMaximumWorldUnity = lidarBounds.max };
        string report = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../artifacts/checks/lidar-unity-mount.json"));
        File.WriteAllText(report, JsonUtility.ToJson(mountEvidence, true));
        var overview = GameObject.Find("Overview Camera").GetComponent<Camera>();
        overview.transform.position = new Vector3(3, 2.4f, -3);
        overview.transform.LookAt(new Vector3(0, .55f, .4f));
        const string scene = "Assets/IGVC/GeneratedRobot/R3aDrive.unity";
        EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), scene);
        AssetDatabase.SaveAssets();
    }

    public static void BuildScene(string scene, string relativeOutput)
    {
        string output = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../artifacts/", relativeOutput));
        Directory.CreateDirectory(Path.GetDirectoryName(output));
        var result = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { scene },
            locationPathName = output, target = BuildTarget.StandaloneWindows64, options = BuildOptions.Development });
        if (result.summary.result != BuildResult.Succeeded) throw new Exception("R3-a drive build failed");
    }
    [Serializable] private class LidarEvidence
    {
        public Vector3 scanFrameWorldUnity, scanForwardWorldUnity, visualMinimumWorldUnity, visualMaximumWorldUnity;
    }
}
