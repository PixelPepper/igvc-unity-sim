using System;
using IGVC;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class TerrainBenchBuild
{
    public static void Build()
    {
        TerrainSupportChecks.Run();
        CasterSuspensionChecks.Run();
        CasterTerrainChecks.Run();
        CasterTurningChecks.Run();
        R3aDriveBuild.CreateScene();
        foreach(string name in new[]{"Calibration Wall","Left Marker","Right Marker"})
            UnityEngine.Object.DestroyImmediate(GameObject.Find(name));
        for(int i=-5;i<=5;i++) UnityEngine.Object.DestroyImmediate(GameObject.Find("Grid "+i));
        var pad=GameObject.Find("Test Pad").GetComponent<Collider>();
        pad.transform.localScale=new Vector3(14,.2f,28);
        float angle=Mathf.Atan2(.4f,3)*Mathf.Rad2Deg;
        var up=Surface("Terrain rise",new Vector3(0,.2f,3.5f),-angle,Mathf.Sqrt(9.16f));
        var deck=Surface("Terrain deck",new Vector3(0,.4f,6),0,2);
        var down=Surface("Terrain descent",new Vector3(0,.2f,8.5f),angle,Mathf.Sqrt(9.16f));
        // The front wheels miss this narrow strip; only the rear left support meets it.
        var bump=GameObject.CreatePrimitive(PrimitiveType.Cube);bump.name="Left caster travel bump";
        bump.transform.position=new Vector3(-.24612f,.0125f,1);
        bump.transform.localScale=new Vector3(.16f,.025f,.8f);
        UnityEngine.Object.FindFirstObjectByType<TransportProbe>().ConfigureTerrain(new[]{pad,up,deck,down,bump.GetComponent<Collider>()});
        var camera=GameObject.Find("Overview Camera").GetComponent<Camera>();
        camera.transform.position=new Vector3(9,7,3);camera.transform.LookAt(new Vector3(0,.3f,5));
        camera.gameObject.AddComponent<SpectatorCamera>().Configure(GameObject.Find("R3-a kinematic oracle").transform,
            camera.transform.position,new Vector3(0,.3f,5));
        const string scene="Assets/IGVC/GeneratedRobot/TerrainBench.unity";
        EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(),scene);
        AssetDatabase.SaveAssets();
        R3aDriveBuild.BuildScene(scene,"build-terrain/IGVCTerrain.exe");
    }

    private static Collider Surface(string name,Vector3 top,float angle,float length)
    {
        var obj=GameObject.CreatePrimitive(PrimitiveType.Cube);obj.name=name;
        obj.transform.rotation=Quaternion.Euler(angle,0,0);
        obj.transform.position=top-obj.transform.up*.05f;
        obj.transform.localScale=new Vector3(3,.1f,length);
        const string path="Assets/IGVC/GeneratedRobot/TerrainBench.mat";
        var material=AssetDatabase.LoadAssetAtPath<Material>(path);
        if(material==null){material=new Material(Shader.Find("Standard")){color=new Color(.35f,.4f,.45f)};AssetDatabase.CreateAsset(material,path);}
        obj.GetComponent<Renderer>().sharedMaterial=material;
        return obj.GetComponent<Collider>();
    }
}
