using System;
using System.Collections.Generic;
using IGVC;
using UnityEngine;

public static class CasterTerrainChecks
{
    public static void Run()
    {
        int count=0; var owned=new List<GameObject>();
        void Check(bool value,string name){if(!value)throw new Exception("Caster terrain check failed: "+name);count++;}
        Collider Box(Vector3 center,Vector3 size)
        {
            var go=new GameObject("Disposable caster terrain fixture");owned.Add(go);
            go.hideFlags=HideFlags.HideAndDontSave;go.transform.position=center;
            var box=go.AddComponent<BoxCollider>();box.size=size;return box;
        }
        var settings=new CasterSettings {effective_rear_mass_kg=30,spring_n_per_m_each=12000,
            damper_ns_per_m_each=700,vertical_travel_m=.04,joint_limit_m=.045,
            front_half_track_m=.405255f,rear_half_track_m=.24612f,rear_distance_m=.85f};
        try
        {
            var floor=Box(new Vector3(0,-.1f,0),new Vector3(10,.2f,10));
            var bump=Box(new Vector3(-.24612f,.0125f,1),new Vector3(.16f,.025f,.8f));
            Physics.SyncTransforms();
            var support=new CasterTerrainSupport(settings,new[]{floor,bump});
            Check(support.TryPreview(Vector3.zero,0,0,true,out var initial),"flat initialization");
            support.Commit(initial);
            Check(Vector3.Distance(initial.Position,new Vector3(0,.30385548f,-.25591f))<1e-5f
                && Math.Abs(initial.Left)+Math.Abs(initial.Right)<1e-6,"flat body and caster rest");
            Check(support.TryPreview(new Vector3(0,0,1.85f),0,.01,false,out var overBump),"one caster bump accepted");
            Check(overBump.Left>.005 && overBump.Right<0 && Math.Abs(overBump.Left-overBump.Right-.025)<1e-5,
                "left compression and opposite extension on unilateral terrain");
            Check(ReferenceEquals(support.Current,initial),"candidate does not mutate committed state");
            support.Commit(overBump);
            Check(Math.Abs(overBump.LeftJoint*(overBump.Rotation*Vector3.up).y-overBump.Left)<1e-8,
                "slider vertical projection equals compression");
            for(int i=0;i<300;i++)
            {
                if(!support.TryPreview(new Vector3(0,0,1.85f),0,.01,false,out var next)) throw new Exception("settling preview rejected");
                support.Commit(next);
            }
            Check(Math.Abs(support.Current.Left-.0125)<1e-5 && Math.Abs(support.Current.Right+.0125)<1e-5,
                "equal springs share unilateral bump at rest");
            Check(support.TryPreview(new Vector3(0,0,1.85f),0,0,false,out var paused)
                && paused.Height==support.Current.Height && paused.Left==support.Current.Left,"pause freezes spring state");
            bump.enabled=false;
            Check(support.TryPreview(new Vector3(0,0,1.85f),90,0,true,out var reset)
                && Math.Abs(reset.Height)+Math.Abs(reset.Left)+Math.Abs(reset.Right)<1e-6
                && Vector3.Distance(reset.Rotation*Vector3.forward,Vector3.right)<1e-5,"reset clears deflection and respects yaw");
            floor.enabled=false;
            var committed=support.Current;
            Check(!support.TryPreview(Vector3.zero,0,.01,false,out _),"missing support rejects without flat fallback");
            Check(ReferenceEquals(support.Current,committed),"failed preview preserves committed state");
            Debug.Log("IGVC_CASTER_TERRAIN_CHECKS_OK count="+count);
        }
        finally {foreach(var go in owned)UnityEngine.Object.DestroyImmediate(go);Physics.SyncTransforms();}
    }
}
