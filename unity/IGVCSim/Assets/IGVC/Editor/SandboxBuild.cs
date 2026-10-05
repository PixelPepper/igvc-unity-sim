using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class SandboxBuild
{
    [MenuItem("IGVC/Build Sandbox Player")]
    public static void Build()
    {
        SoonerCourseBuild.CreateScene();
        EditorSceneManager.OpenScene("Assets/IGVC/GeneratedRobot/SoonerAutoNav.unity");
        R3aDriveBuild.BuildScene("Assets/IGVC/GeneratedRobot/SoonerAutoNav.unity","build-sandbox/IGVCSandbox.exe");
        Debug.Log("IGVC_SANDBOX_BUILD_OK");
    }
}
