using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using UnityEngine;
using UnityEngine.Rendering;

namespace IGVC
{
    // Startup-only environment loading. No geometry is published to perception.
    public static class CourseVariant
    {
        [Serializable] public class Point { public double x, y, half_width; public bool painted; }
        [Serializable] public class Obstacle
        { public string id, kind; public double x, y, yaw, length, width, height, depth; }
        [Serializable] public class Manifest
        {
            public int schema_version, seed;
            public string difficulty, frame, units;
            public string runtime_hash;
            public double lane_width_m, camera_pitch_rad;
            public Point[] centerline;
            public Obstacle[] obstacles;
            public CourseRamp.Definition[] ramps;
            [NonSerialized] public Collider[] support_surfaces;
        }
        private static Vector3 World(double x, double y, double z=0) => new Vector3((float)-y,(float)z,(float)x);
        private static Material Paint(Color color)
        {
            var template=Resources.Load<Material>("IGVCVariantPalette");
            if (template==null) throw new InvalidOperationException("Variant palette missing; rebuild course");
            var material=new Material(template); material.color=color;return material;
        }
        public static Manifest Load(string path, LaneBoundaryGuard guard)
        {
            if (new FileInfo(path).Length>4000000) throw new InvalidDataException("Course manifest too large");
            var m=JsonUtility.FromJson<Manifest>(File.ReadAllText(path));
            if (m==null || m.schema_version!=1 || m.frame!="odom" || m.units!="m"
                || m.centerline==null || m.centerline.Length<20 || m.centerline.Length>5000
                || m.obstacles==null || m.obstacles.Length>200 || m.lane_width_m<4 || m.lane_width_m>8
                || !double.IsFinite(m.camera_pitch_rad) || Math.Abs(m.camera_pitch_rad)>Math.PI/6)
                throw new InvalidDataException("Unsupported course manifest");
            using (var hash=SHA256.Create()) m.runtime_hash=BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();
            foreach(var p in m.centerline)
                if (!double.IsFinite(p.x)||!double.IsFinite(p.y)||Math.Abs(p.x)>100||Math.Abs(p.y)>100
                    || !double.IsFinite(p.half_width) || p.half_width<0 || p.half_width>4 || (p.half_width>0 && p.half_width<1))
                    throw new InvalidDataException("Invalid centerline coordinate");
            foreach(var o in m.obstacles)
                if (!double.IsFinite(o.x)||!double.IsFinite(o.y)||!double.IsFinite(o.yaw)
                    || !double.IsFinite(o.length)||!double.IsFinite(o.width)||!double.IsFinite(o.height)||!double.IsFinite(o.depth)
                    || Math.Abs(o.x)>100||Math.Abs(o.y)>100||o.length<=0||o.length>4||o.width<=0||o.width>4
                    || o.height<0||o.height>3||o.depth<0||o.depth>1
                    || (o.kind!="barrel"&&o.kind!="barricade"&&o.kind!="pothole"))
                    throw new InvalidDataException("Invalid obstacle");
            if(m.ramps != null && m.ramps.Length>1) throw new InvalidDataException("At most one course ramp is supported");
            if(m.ramps != null) foreach(var ramp in m.ramps) CourseRamp.Validate(ramp);
            var original=GameObject.Find("Course frame (source spawn to odom origin)");
            if (original==null) throw new InvalidOperationException("Expected reference course root missing");
            original.SetActive(false);
            var root=new GameObject("Procedural IGVC seed "+m.seed).transform;
            var gray=Paint(new Color(.40f,.42f,.43f));
            var white=Paint(Color.white);var orange=Paint(new Color(1,.36f,.025f));
            var dark=Paint(new Color(.045f,.045f,.045f));
            var ground=Ground(root,m,gray);
            if(m.ramps != null && m.ramps.Length>0)
            {
                var supports=new List<Collider>{ground};
                var rampMaterial=Paint(new Color(.24f,.32f,.29f));
                foreach(var ramp in m.ramps) supports.AddRange(CourseRamp.Create(root,ramp,rampMaterial));
                m.support_surfaces=supports.ToArray();
            }
            Lanes(root,m,white,guard);
            foreach(var o in m.obstacles)
            {
                var item=new GameObject(o.kind+" "+o.id).transform;
                item.SetParent(root,false);item.position=World(o.x,o.y);
                item.rotation=Quaternion.Euler(0,(float)(-o.yaw*Mathf.Rad2Deg),0);
                if(o.kind=="barrel")
                {
                    Primitive(item,PrimitiveType.Cylinder,new Vector3(0,(float)o.height/2,0),new Vector3((float)o.width,(float)o.height/2,(float)o.length),orange);
                    // Ring geometry gives RGB barrel context while retaining a solid scan obstacle.
                    foreach(float h in new[]{.34f,.68f})
                        Primitive(item,PrimitiveType.Cylinder,new Vector3(0,(float)o.height*h,0),new Vector3((float)o.width+.004f,.045f,(float)o.length+.004f),white);
                }
                else if(o.kind=="barricade")
                {
                    Primitive(item,PrimitiveType.Cube,new Vector3(0,(float)o.height*.62f,0),new Vector3((float)o.width,(float)o.height*.65f,(float)o.length),orange);
                    for(int i=0;i<6;i+=2)
                        Primitive(item,PrimitiveType.Cube,new Vector3(0,(float)o.height*.62f,(float)o.length*((i+.5f)/6-.5f)),new Vector3((float)o.width+.006f,(float)o.height*.65f+.006f,(float)o.length/6),white);
                    foreach(float side in new[]{-.35f,.35f})
                        Primitive(item,PrimitiveType.Cube,new Vector3(0,(float)o.height*.18f,(float)o.length*side),new Vector3((float)o.width,(float)o.height*.36f,.07f),orange);
                }
                else Bowl(item,o,gray,dark);
            }
            Physics.SyncTransforms();
            if(!guard.CanOccupy(0,0,0)) throw new InvalidDataException("Variant spawn overlaps paint");
            Debug.Log("IGVC_COURSE_VARIANT_READY seed="+m.seed+" objects="+m.obstacles.Length+" pitch="+m.camera_pitch_rad);
            return m;
        }
        private static void Primitive(Transform root,PrimitiveType kind,Vector3 position,Vector3 scale,Material material)
        {
            var item=GameObject.CreatePrimitive(kind);item.transform.SetParent(root,false);
            item.transform.localPosition=position;item.transform.localScale=scale;
            item.GetComponent<Renderer>().sharedMaterial=material;
        }
        private static Collider MeshObject(Transform root,string name,List<Vector3> vertices,List<int> triangles,Material material)
        {
            var go=new GameObject(name);go.transform.SetParent(root,false);
            var mesh=new Mesh { name=name,indexFormat=IndexFormat.UInt32 };
            mesh.SetVertices(vertices);mesh.SetTriangles(triangles,0);mesh.RecalculateNormals();mesh.RecalculateBounds();
            go.AddComponent<MeshFilter>().sharedMesh=mesh;go.AddComponent<MeshRenderer>().sharedMaterial=material;
            var collider=go.AddComponent<MeshCollider>();collider.sharedMesh=mesh;
            return collider;
        }
        private static void Quad(List<Vector3> v,List<int> t,Vector3 a,Vector3 b,Vector3 c,Vector3 d)
        {
            int n=v.Count;v.AddRange(new[]{a,b,c,d});
            // Both windings avoid orientation assumptions in imported ROS polylines.
            t.AddRange(new[]{n,n+1,n+2,n,n+2,n+3,n+2,n+1,n,n+3,n+2,n});
        }
        private static Collider Ground(Transform root,Manifest m,Material gray)
        {
            double minX=0,maxX=0,minY=0,maxY=0;
            foreach(var p in m.centerline){minX=Math.Min(minX,p.x);maxX=Math.Max(maxX,p.x);minY=Math.Min(minY,p.y);maxY=Math.Max(maxY,p.y);}
            var v=new List<Vector3>();var t=new List<int>();const double cell=.5;
            for(double x=Math.Floor(minX)-10;x<Math.Ceiling(maxX)+10;x+=cell)
                for(double y=Math.Floor(minY)-10;y<Math.Ceiling(maxY)+10;y+=cell)
                {
                    bool hole=false;
                    foreach(var o in m.obstacles)if(o.kind=="pothole" && Math.Pow(x+.25-o.x,2)+Math.Pow(y+.25-o.y,2)<Math.Pow(Math.Max(o.length,o.width)/2+.36,2)){hole=true;break;}
                    if(!hole)Quad(v,t,World(x,y),World(x+cell,y),World(x+cell,y+cell),World(x,y+cell));
                }
            return MeshObject(root,"Flat ground with cutouts",v,t,gray);
        }
        private static void Bowl(Transform root,Obstacle o,Material gray,Material dark)
        {
            double radius=Math.Max(o.length,o.width)/2;
            var v=new List<Vector3>();var t=new List<int>();
            var inside=new List<Vector3>();var it=new List<int>();
            for(int i=0;i<64;i++)
            {
                double a=i*Math.PI/32,b=(i+1)*Math.PI/32;
                Func<double,double,double,Vector3> ring=(angle,r,z)=>new Vector3((float)(r*Math.Cos(angle)),(float)z,(float)(r*Math.Sin(angle)));
                Quad(v,t,ring(a,radius+.85,0),ring(b,radius+.85,0),ring(b,radius,0),ring(a,radius,0));
                Quad(inside,it,ring(a,radius,-.002),ring(b,radius,-.002),ring(b,radius*.4,-o.depth),ring(a,radius*.4,-o.depth));
                Quad(inside,it,ring(a,radius*.4,-o.depth),ring(b,radius*.4,-o.depth),new Vector3(0,(float)-o.depth,0),new Vector3(0,(float)-o.depth,0));
            }
            MeshObject(root,"Pothole rim",v,t,gray);MeshObject(root,"Dark depression",inside,it,dark);
        }
        private static void Lanes(Transform root,Manifest m,Material white,LaneBoundaryGuard guard)
        {
            var v=new List<Vector3>();var t=new List<int>();var lines=new List<LaneBoundaryGuard.Segment>();
            // Shared miter vertices keep thin paint continuous around bends.
            // Offsetting every segment independently leaves gaps proportional to
            // lane width, which can erase the entire distant stripe in RGB.
            var offsets=new Vector2[m.centerline.Length];
            for(int i=0;i<m.centerline.Length;i++)
            {
                int current=i==m.centerline.Length-1?0:i;
                int previous=current==0?m.centerline.Length-2:current-1;
                int next=current+1;
                var a=m.centerline[previous];var b=m.centerline[current];var c=m.centerline[next];
                var incoming=new Vector2((float)(b.x-a.x),(float)(b.y-a.y)).normalized;
                var outgoing=new Vector2((float)(c.x-b.x),(float)(c.y-b.y)).normalized;
                var n0=new Vector2(-incoming.y,incoming.x);var n1=new Vector2(-outgoing.y,outgoing.x);
                var bisector=(n0+n1).normalized;
                float denominator=Vector2.Dot(bisector,n1);
                if(denominator<.5f)throw new InvalidDataException("Course paint has an excessive corner angle");
                offsets[i]=bisector/denominator;
            }
            for(int i=0;i<m.centerline.Length-1;i++)
            {
                var a=m.centerline[i];var b=m.centerline[i+1];if(!a.painted||!b.painted)continue;
                double dx=b.x-a.x,dy=b.y-a.y,len=Math.Sqrt(dx*dx+dy*dy);if(len<1e-6)continue;
                foreach(int side in new[]{-1,1})
                {
                    var p=new Vector2((float)a.x,(float)a.y);var q=new Vector2((float)b.x,(float)b.y);
                    float pWidth=(float)(a.half_width>0?a.half_width:m.lane_width_m/2);
                    float qWidth=(float)(b.half_width>0?b.half_width:m.lane_width_m/2);
                    var p0=p+offsets[i]*(side*(pWidth-.06f));var p1=p+offsets[i]*(side*(pWidth+.06f));
                    var q0=q+offsets[i+1]*(side*(qWidth-.06f));var q1=q+offsets[i+1]*(side*(qWidth+.06f));
                    Quad(v,t,PaintPosition(p0,m),PaintPosition(q0,m),PaintPosition(q1,m),PaintPosition(p1,m));
                    lines.Add(new LaneBoundaryGuard.Segment{a=p0,b=q0});
                    lines.Add(new LaneBoundaryGuard.Segment{a=p1,b=q1});
                }
            }
            MeshObject(root,"Procedural painted boundaries",v,t,white);guard.Configure(lines.ToArray());guard.Clear();
        }
        private static Vector3 PaintPosition(Vector2 point,Manifest manifest)
        {
            double height=0;
            if(manifest.ramps!=null) foreach(var ramp in manifest.ramps)
                height=Math.Max(height,CourseRamp.HeightAt(ramp,point.x,point.y));
            return World(point.x,point.y,height+.008);
        }
    }
}
