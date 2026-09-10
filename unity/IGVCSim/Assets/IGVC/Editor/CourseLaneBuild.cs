using System;
using System.Collections.Generic;
using System.IO;
using IGVC;
using UnityEngine;

public static class CourseLaneBuild
{
    public static LaneBoundaryGuard Add(MeshFilter road)
    {
        var mesh=road.sharedMesh; var vertices=mesh.vertices; var uv=mesh.uv;
        var segments=new List<LaneBoundaryGuard.Segment>();
        // Pinned texture: opaque columns0..35 and477..511 of512. Preserve open course gaps.
        for(int i=0;i<vertices.Length;i+=4)
        {
            if(uv[i].x!=0 || uv[i+1].x!=1 || uv[i+2].x!=0 || uv[i+3].x!=1)
                throw new Exception("Course lane mesh UV ordering changed");
            var a=road.transform.TransformPoint(vertices[i]); var b=road.transform.TransformPoint(vertices[i+1]);
            var c=road.transform.TransformPoint(vertices[i+2]); var d=road.transform.TransformPoint(vertices[i+3]);
            Quad(segments,a,Vector3.Lerp(a,b,36f/512),Vector3.Lerp(c,d,36f/512),c);
            Quad(segments,Vector3.Lerp(a,b,477f/512),b,d,Vector3.Lerp(c,d,477f/512));
        }
        var guard=new GameObject("Painted boundary constraint (simulator truth)").AddComponent<LaneBoundaryGuard>();
        guard.Configure(segments.ToArray());
        if(!guard.CanOccupy(0,0,0))throw new Exception("R3-a spawn intersects a painted boundary");
        // Reproducible independent checks: translation, reverse and rotation corner sweeps.
        var test=new GameObject("Temporary boundary check").AddComponent<LaneBoundaryGuard>();
        test.Configure(new[]{new LaneBoundaryGuard.Segment{a=new Vector2(-10,.75f),b=new Vector2(10,.75f)}});
        if(!test.CanOccupy(0,0,0) || test.CanOccupy(0,.6,0)
            || test.AllowsMotion(0,0,Math.PI/2,1,0,2)
            || !test.AllowsMotion(0,0,Math.PI/2,-1,0,.1)
            || test.AllowsMotion(0,0,0,0,1,Math.PI/2))throw new Exception("Painted boundary sweep checks failed");
        UnityEngine.Object.DestroyImmediate(test.gameObject);
        string report=Path.GetFullPath(Path.Combine(Application.dataPath,"../../../artifacts/checks/lane-guard-build.json"));
        File.WriteAllText(report,"{\"status\":\"passed\",\"segments\":"+segments.Count+",\"footprint\":[-1.1,0.6,-0.5,0.5],\"skin_m\":0.03,\"sweep_checks\":5}");
        return guard;
    }
    private static void Quad(List<LaneBoundaryGuard.Segment> result,params Vector3[] points)
    {
        for(int i=0;i<4;i++) {var a=points[i];var b=points[(i+1)%4];result.Add(new LaneBoundaryGuard.Segment{a=new Vector2(a.z,-a.x),b=new Vector2(b.z,-b.x)});}
    }
}
