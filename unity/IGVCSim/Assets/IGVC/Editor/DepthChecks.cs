using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class DepthChecks
{
    public static void BuildCourse(){Run();SoonerCourseBuild.Build();}
    public static void Run()
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
        var camera=new GameObject("Depth calibration camera").AddComponent<Camera>();
        camera.enabled=false;camera.fieldOfView=54;camera.aspect=4f/3;
        camera.nearClipPlane=.05f;camera.farClipPlane=10.01f;
        camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.clear;
        var wall=GameObject.CreatePrimitive(PrimitiveType.Cube);
        wall.transform.position=new Vector3(0,0,4.05f);wall.transform.localScale=new Vector3(4,3,.1f);
        var marker=GameObject.CreatePrimitive(PrimitiveType.Cube);
        marker.transform.position=new Vector3(-.6f,.5f,2.05f);marker.transform.localScale=new Vector3(.4f,.4f,.1f);
        var target=new RenderTexture(320,240,24,RenderTextureFormat.RFloat,RenderTextureReadWrite.Linear);
        target.Create();camera.targetTexture=target;
        var texture=new Texture2D(320,240,TextureFormat.RFloat,false,true);
        var previous=RenderTexture.active;
        var checks=new List<string>();
        Action<bool,string> check=(condition,name)=>{if(!condition)throw new Exception("Depth check failed: "+name);checks.Add(name);};
        try
        {
            var shader=Resources.Load<Shader>("IGVCMetricDepth");
            check(shader!=null&&shader.isSupported,"shader_supported");
            camera.RenderWithShader(shader,"");RenderTexture.active=target;
            texture.ReadPixels(new Rect(0,0,320,240),0,0);texture.Apply();
            var data=texture.GetRawTextureData<float>();
            check(Math.Abs(data[120*320+160]-4)<.001,"central_wall_is_4m");
            check(Math.Abs(data[120*320+230]-4)<.001,"off_axis_is_optical_z_not_ray_range");
            check(Math.Abs(data[(239-60)*320+89]-2)<.001,"upper_left_marker_at_2m");
            check(Math.Abs(data[(239-180)*320+89]-4)<.001,"asymmetric_rows_distinguishable");
            check(data[239*320+319]==0,"sky_clear_is_invalid_sentinel");
            File.WriteAllText(Path.GetFullPath("../../artifacts/checks/depth-render.json"),"{\"passed\":true,\"checks\":[\""+string.Join("\",\"",checks)+"\"]}");
            Debug.Log("IGVC_DEPTH_RENDER_CHECKS_OK count="+checks.Count);
        }
        finally
        {
            RenderTexture.active=previous;camera.targetTexture=null;target.Release();
            UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(texture);
            UnityEngine.Object.DestroyImmediate(camera.gameObject);UnityEngine.Object.DestroyImmediate(wall);UnityEngine.Object.DestroyImmediate(marker);
        }
    }
}
