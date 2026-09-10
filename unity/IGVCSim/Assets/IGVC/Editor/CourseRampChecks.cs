using System;
using System.Collections.Generic;
using System.IO;
using IGVC;
using UnityEngine;

public static class CourseRampChecks
{
    public static void Run()
    {
        int count=0;
        void Check(bool condition,string name){if(!condition)throw new Exception("Course ramp: "+name);count++;}
        var root=new GameObject("Course ramp test fixture");
        try
        {
            var floor=GameObject.CreatePrimitive(PrimitiveType.Cube);floor.transform.SetParent(root.transform);
            floor.transform.position=new Vector3(0,-.1f,0);floor.transform.localScale=new Vector3(50,.2f,50);
            foreach(double yaw in new[]{0.0,Math.PI/2,.63})
            {
                var spec=new CourseRamp.Definition{x=2,y=-1,yaw=yaw,width=3,rise_length=3,deck_length=2,height=.4};
                var ramps=CourseRamp.Create(root.transform,spec,null);
                Physics.SyncTransforms();
                var surfaces=new List<Collider>{floor.GetComponent<Collider>()};surfaces.AddRange(ramps);
                var start=new Vector3(1,0,2);
                var rotation=Quaternion.Euler(0,(float)(-yaw*Mathf.Rad2Deg),0);
                foreach(var sample in new[]{new Vector2(0,0),new Vector2(1.5f,.2f),new Vector2(3,.4f),new Vector2(4,.4f),new Vector2(5,.4f),new Vector2(6.5f,.2f),new Vector2(8,0)})
                {
                    var position=start+rotation*new Vector3(0,0,sample.x);
                    float best=float.NegativeInfinity;
                    foreach(var collider in surfaces)
                        if(collider.Raycast(new Ray(position+Vector3.up*3,Vector3.down),out var hit,6))best=Mathf.Max(best,hit.point.y);
                    Check(Mathf.Abs(best-sample.y)<1e-4,"ray height across rotated rise/deck/descent");
                    foreach(float side in new[]{-1.44f,1.44f})
                    {
                        var edge=start+rotation*new Vector3(side,0,sample.x);
                        Check(Math.Abs(CourseRamp.HeightAt(spec,edge.z,-edge.x)-sample.y)<1e-4,"paint follows raised surface at both edges");
                    }
                }
                var settings=new CasterSettings{effective_rear_mass_kg=30,spring_n_per_m_each=12000,damper_ns_per_m_each=700,
                    vertical_travel_m=.04,joint_limit_m=.045,front_half_track_m=.405255f,rear_half_track_m=.24612f,rear_distance_m=.85f};
                var support=new CasterTerrainSupport(settings,surfaces);
                float maxHeight=0;bool moving=true;
                for(int i=0;i<=1700;i++)
                {
                    var position=start+rotation*new Vector3(0,0,-1+i*.006f);
                    if(!support.TryPreview(position,(float)(-yaw*Mathf.Rad2Deg),.01,i==0,out var candidate)){moving=false;break;}
                    support.Commit(candidate);maxHeight=Mathf.Max(maxHeight,candidate.AxleHeight);
                }
                Check(moving && maxHeight>.399f,"continuous sprung crossing without missing supports");
                Check(Math.Abs(support.Current.Left)<.001 && Math.Abs(support.Current.Right)<.001,"settled after ramp exit");
                UnityEngine.Object.DestroyImmediate(ramps[0].transform.parent.gameObject);
            }
            bool rejected=false;
            try{CourseRamp.Validate(new CourseRamp.Definition{x=2,width=3,rise_length=2,deck_length=2,height=.6});}
            catch(InvalidDataException){rejected=true;}
            Check(rejected,"reject slope above support limit");
            Debug.Log("IGVC_COURSE_RAMP_CHECKS_OK count="+count);
        }
        finally{UnityEngine.Object.DestroyImmediate(root);Physics.SyncTransforms();}
    }
}
