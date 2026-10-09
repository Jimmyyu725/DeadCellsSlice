// Ambient smoke cards above the flame head. The cards come from Blender as
// quads in the model's X/Y plane; the vertex shader re-centres each quad and
// billboards it towards the camera. Rendered after the pixelation pass, so it
// stays soft and high resolution.
Shader "DeadCells/Smoke"
{
    Properties
    {
        [HDR] _SmokeColor ("Smoke Colour", Color) = (0.22, 0.14, 0.32, 1)
        [HDR] _GlowColor ("Glow Colour (bottom)", Color) = (1.2, 0.5, 2.0, 1)
        _Opacity ("Opacity", Range(0, 1)) = 0.45
        _NoiseScale ("Noise Scale", Float) = 3.5
        _RiseSpeed ("Rise Speed", Float) = 0.6
        _Size ("Card Size (m)", Float) = 0.32
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "Queue" = "Transparent" }

        Pass
        {
            Name "Smoke"
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "DeadCellsNoise.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _SmokeColor;
                half4 _GlowColor;
                half _Opacity;
                float _NoiseScale;
                float _RiseSpeed;
                float _Size;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv : TEXCOORD0;
                half4 color : COLOR;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 seed : TEXCOORD1;
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings Vert(Attributes v)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float size = _Size * lerp(1.0, 0.75, v.color.b);
                float3 objRight = normalize(TransformObjectToWorldDir(float3(1, 0, 0)));
                float3 objUp = normalize(TransformObjectToWorldDir(float3(0, 1, 0)));
                float3 corner = float3(v.uv - 0.5, 0) * size;
                float3 centre = TransformObjectToWorld(v.positionOS.xyz) - objRight * corner.x - objUp * corner.y;
                float3 camRight = UNITY_MATRIX_V[0].xyz;
                float3 camUp = UNITY_MATRIX_V[1].xyz;
                float3 p = centre + camRight * corner.x + camUp * corner.y;
                o.positionCS = TransformWorldToHClip(p);
                o.uv = v.uv;
                o.seed = centre + v.color.b * 13.0;
                return o;
            }

            half4 Frag(Varyings i) : SV_Target
            {
                float2 c = i.uv - 0.5;
                half radial = saturate(1.0 - length(c) * 2.0);
                float3 q = float3(i.uv * _NoiseScale, 0) + float3(i.seed.x, i.seed.y - _Time.y * _RiseSpeed * _NoiseScale, _Time.y * 0.2);
                half n = DCFbm3(q);
                half a = saturate(radial * radial * (n * 1.6 - 0.25)) * _Opacity;
                half3 col = lerp(_GlowColor.rgb, _SmokeColor.rgb, saturate(i.uv.y * 1.4));
                return half4(col, a);
            }
            ENDHLSL
        }
    }
}
