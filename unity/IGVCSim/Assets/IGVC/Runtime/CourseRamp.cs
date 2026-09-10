using System;
using System.IO;
using UnityEngine;

namespace IGVC
{
    // Static surveyed environment geometry; never published as perception input.
    public static class CourseRamp
    {
        [Serializable] public class Definition
        {
            public string id;
            public double x, y, yaw, width, rise_length, deck_length, height;
        }

        public static void Validate(Definition ramp)
        {
            if (ramp == null || !double.IsFinite(ramp.x) || !double.IsFinite(ramp.y)
                || !double.IsFinite(ramp.yaw) || !double.IsFinite(ramp.width)
                || !double.IsFinite(ramp.rise_length) || !double.IsFinite(ramp.deck_length)
                || !double.IsFinite(ramp.height) || Math.Abs(ramp.x)>100 || Math.Abs(ramp.y)>100
                || ramp.width<2 || ramp.width>6 || ramp.rise_length<2 || ramp.rise_length>8
                || ramp.deck_length<1 || ramp.deck_length>4 || ramp.height<.05 || ramp.height>.6
                || Math.Atan2(ramp.height,ramp.rise_length)>15*Math.PI/180)
                throw new InvalidDataException("Unsupported course ramp dimensions");
        }

        public static Collider[] Create(Transform parent, Definition ramp, Material material)
        {
            Validate(ramp);
            var root = new GameObject("Course ramp " + ramp.id).transform;
            root.SetParent(parent, false);
            root.localPosition = new Vector3((float)-ramp.y, 0, (float)ramp.x);
            root.localRotation = Quaternion.Euler(0, (float)(-ramp.yaw*Mathf.Rad2Deg), 0);
            float rise=(float)ramp.rise_length, deck=(float)ramp.deck_length, height=(float)ramp.height;
            float angle=Mathf.Atan2(height,rise)*Mathf.Rad2Deg;
            return new[] {
                Surface(root,"Rise",new Vector3(0,height/2,rise/2),-angle,Mathf.Sqrt(rise*rise+height*height),(float)ramp.width,material),
                Surface(root,"Deck",new Vector3(0,height,rise+deck/2),0,deck,(float)ramp.width,material),
                Surface(root,"Descent",new Vector3(0,height/2,rise+deck+rise/2),angle,Mathf.Sqrt(rise*rise+height*height),(float)ramp.width,material)
            };
        }

        public static double HeightAt(Definition ramp,double x,double y)
        {
            double dx=x-ramp.x,dy=y-ramp.y,c=Math.Cos(ramp.yaw),s=Math.Sin(ramp.yaw);
            double along=c*dx+s*dy,across=-s*dx+c*dy;
            double total=2*ramp.rise_length+ramp.deck_length;
            if(along<0 || along>total || Math.Abs(across)>ramp.width/2+1e-5)return 0;
            return ramp.height*Math.Min(1,Math.Min(along,total-along)/ramp.rise_length);
        }

        private static Collider Surface(Transform parent,string name,Vector3 top,float angle,float length,float width,Material material)
        {
            var item=GameObject.CreatePrimitive(PrimitiveType.Cube);
            item.name=name;item.transform.SetParent(parent,false);
            item.transform.localRotation=Quaternion.Euler(angle,0,0);
            item.transform.localPosition=top-item.transform.localRotation*Vector3.up*.05f;
            item.transform.localScale=new Vector3(width,.1f,length);
            item.GetComponent<Renderer>().sharedMaterial=material;
            return item.GetComponent<Collider>();
        }
    }
}
