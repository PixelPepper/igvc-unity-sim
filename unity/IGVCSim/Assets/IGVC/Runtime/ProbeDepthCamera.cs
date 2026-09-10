using System;
using RosMessageTypes.Sensor;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;
using UnityEngine.Rendering;

namespace IGVC
{
    // Ideal co-located depth at half RGB resolution, not simulated stereo matching.
    public sealed class ProbeDepthCamera : MonoBehaviour
    {
        private const int Width=320, Height=240;
        private ROSConnection ros;
        private TransportProbe probe;
        private Camera depthCamera;
        private RenderTexture target;
        private Shader shader;
        private bool alive, pending;
        private double nextCapture;
        private int completed, errors;
        public string Diagnostics => $"depth completed={completed} errors={errors}";

        public void Initialize(ROSConnection connection,TransportProbe owner,Camera source)
        {
            ros=connection;probe=owner;
            shader=Resources.Load<Shader>("IGVCMetricDepth");
            if(shader==null||!shader.isSupported||!SystemInfo.SupportsRenderTextureFormat(RenderTextureFormat.RFloat))
                throw new InvalidOperationException("Metric depth requires the included shader and RFloat render support");
            var go=new GameObject("Ideal registered depth camera");
            go.transform.SetParent(source.transform,false);
            depthCamera=go.AddComponent<Camera>();depthCamera.CopyFrom(source);
            depthCamera.enabled=false;depthCamera.aspect=(float)Width/Height;
            depthCamera.clearFlags=CameraClearFlags.SolidColor;depthCamera.backgroundColor=Color.clear;
            depthCamera.allowMSAA=false;depthCamera.allowHDR=false;
            depthCamera.nearClipPlane=.05f;depthCamera.farClipPlane=10.01f;
            target=new RenderTexture(Width,Height,24,RenderTextureFormat.RFloat,RenderTextureReadWrite.Linear);
            target.Create();depthCamera.targetTexture=target;
            ros.RegisterPublisher<ImageMsg>("/camera/depth/image_raw",1);
            ros.RegisterPublisher<CameraInfoMsg>("/camera/depth/camera_info",1);
            alive=true;
        }
        private void LateUpdate()
        {
            if(!alive||pending||ros.HasConnectionError||probe.IsPaused||probe.SimTime<nextCapture)return;
            nextCapture=probe.SimTime+.1;
            var header=probe.Header("camera_color_optical_frame");
            int captureRun=probe.RunId;
            double focal=Height/(2*Math.Tan(depthCamera.fieldOfView*Math.PI/360));
            depthCamera.RenderWithShader(shader,"");pending=true;
            AsyncGPUReadback.Request(target,0,request=>
            {
                pending=false;
                if(request.hasError)errors++;
                if(!alive||request.hasError||ros.HasConnectionError||probe.RunId!=captureRun)return;
                var source=request.GetData<float>();var values=new float[Width*Height];
                for(int row=0;row<Height;row++)for(int col=0;col<Width;col++)
                {
                    float z=source[row*Width+col];
                    values[(Height-1-row)*Width+col]=float.IsFinite(z)&&z>=.2f&&z<=10f?z:float.NaN;
                }
                var bytes=new byte[values.Length*4];Buffer.BlockCopy(values,0,bytes,0,bytes.Length);
                ros.Publish("/camera/depth/image_raw",new ImageMsg(header,Height,Width,"32FC1",(byte)(BitConverter.IsLittleEndian?0:1),Width*4,bytes));
                ros.Publish("/camera/depth/camera_info",new CameraInfoMsg {header=header,width=Width,height=Height,distortion_model="plumb_bob",
                    D=new double[5],K=new[]{focal,0,159.5,0,focal,119.5,0,0,1.0},
                    R=new[]{1.0,0,0,0,1,0,0,0,1},P=new[]{focal,0,159.5,0,0,focal,119.5,0,0,0,1,0}});
                completed++;
            });
        }
        private void OnDestroy()
        {
            alive=false;
            if(pending)AsyncGPUReadback.WaitAllRequests();
            if(depthCamera!=null){depthCamera.targetTexture=null;Destroy(depthCamera.gameObject);}
            if(target!=null){target.Release();Destroy(target);}
        }
    }
}
