using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using UnityEngine;

namespace IGVC
{
    [Serializable] public sealed class SandboxSettings
    {
        public string controller="rpp", execution="checked-path", escape="legacy";
        public double speed_mps=.6, inflation_m=.3, clearance_weight=3, planning_budget_s=.5, lookahead_m=.65;
        // Learned scorers (0 = off, the accepted baseline); the supervisor passes the promoted models.
        public double route_weight, corridor_weight;
    }
    [Serializable] public sealed class SandboxPreset
    {
        public int schema_version=1;
        public CourseVariant.Manifest course;
        public SandboxSettings settings=new SandboxSettings();
    }
    [Serializable] public sealed class SandboxCommand
    {
        public string id, action;
        public SandboxSettings settings;
    }
    [Serializable] public sealed class SandboxStatus
    {
        public string id, state, message;
        public bool editable;
        public int completed_destinations,total_destinations=6;
    }
    public static class SandboxDocument
    {
        public static T Clone<T>(T value) => JsonUtility.FromJson<T>(JsonUtility.ToJson(value));
        public static string PresetPath(string directory,string name)
        {
            if(!Regex.IsMatch(name??"",@"^[A-Za-z0-9][A-Za-z0-9 _-]{0,47}$"))
                throw new InvalidDataException("Use 1-48 letters, numbers, spaces, hyphens or underscores for a preset name.");
            return Path.Combine(directory,"presets",name+".json");
        }
        public static void AtomicWrite(string path,string json)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            string temporary=path+".tmp";
            File.WriteAllText(temporary,json);
            if(File.Exists(path)) File.Replace(temporary,path,null); else File.Move(temporary,path);
        }
        public static void ValidateSettings(SandboxSettings s)
        {
            if(s==null || (s.controller!="rpp"&&s.controller!="mppi") || (s.execution!="checked-path"&&s.execution!="nav2-goal"))
                throw new InvalidDataException("Unknown controller or planning mode.");
            if(s.escape!="legacy"&&s.escape!="retrace") throw new InvalidDataException("Unknown escape mode.");
            Range(s.speed_mps,.1,2.2,"Speed");Range(s.inflation_m,.1,1.5,"Inflation");
            Range(s.clearance_weight,0,10,"Clearance preference");Range(s.planning_budget_s,.1,5,"Planning budget");
            Range(s.lookahead_m,.2,2,"Lookahead");
            Range(s.route_weight,0,10,"Learned route weight");Range(s.corridor_weight,0,10,"Learned corridor weight");
        }
        private static void Range(double v,double min,double max,string label)
        { if(!double.IsFinite(v)||v<min||v>max) throw new InvalidDataException(label+" must be between "+min+" and "+max+"."); }
        public static void ValidateEdit(CourseVariant.Manifest m)
        {
            if(m?.obstacles==null || m.centerline==null) throw new InvalidDataException("Missing course geometry.");
            var ids=new HashSet<string>();
            double minX=100,maxX=-100,minY=100,maxY=-100;
            foreach(var p in m.centerline){minX=Math.Min(minX,p.x);maxX=Math.Max(maxX,p.x);minY=Math.Min(minY,p.y);maxY=Math.Max(maxY,p.y);}
            foreach(var o in m.obstacles)
            {
                if(o==null || string.IsNullOrWhiteSpace(o.id)||!ids.Add(o.id)) throw new InvalidDataException("Obstacle IDs must be unique.");
                Range(o.length,.1,4,"Length");Range(o.width,.1,4,"Width");
                if(o.kind=="pothole")Range(o.depth,.02,1,"Depth");else Range(o.height,.1,3,"Height");
                double radius=Math.Sqrt(o.length*o.length+o.width*o.width)/2;
                if(!double.IsFinite(o.x)||!double.IsFinite(o.y)||o.x-radius<minX-8||o.x+radius>maxX+8||o.y-radius<minY-8||o.y+radius>maxY+8)
                    throw new InvalidDataException("Keep obstacles on the course ground.");
                if(Math.Sqrt(o.x*o.x+o.y*o.y)<radius+1.6)
                    throw new InvalidDataException("Keep the starting area clear (1.6 m plus obstacle radius).");
                if(o.kind=="pothole"&&m.ramps!=null)foreach(var ramp in m.ramps)
                {
                    double dx=o.x-ramp.x,dy=o.y-ramp.y,c=Math.Cos(ramp.yaw),s=Math.Sin(ramp.yaw);
                    double along=c*dx+s*dy,across=-s*dx+c*dy,pad=radius+CourseVariant.PotholeRimWidth;
                    if(along>-pad&&along<2*ramp.rise_length+ramp.deck_length+pad&&Math.Abs(across)<ramp.width/2+pad)
                        throw new InvalidDataException("Potholes must stay clear of the ramp structure.");
                }
            }
        }
    }
}
