Shader "IGVC/MetricDepth"
{
    SubShader
    {
        Pass
        {
            ZWrite On ZTest LEqual Cull Back
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            struct v2f { float4 position : SV_POSITION; float depth : TEXCOORD0; };
            v2f vert(appdata_base v)
            {
                v2f o;
                o.position = UnityObjectToClipPos(v.vertex);
                o.depth = -UnityObjectToViewPos(v.vertex).z;
                return o;
            }
            float frag(v2f i) : SV_Target { return i.depth; }
            ENDCG
        }
    }
}
