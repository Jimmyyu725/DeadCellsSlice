// Fake volumetric god ray: additive quad, bright at the grate (uv.y = 1),
// fading downward, soft side edges, slowly drifting dust streaks.
Shader "DeadCells/LightShaft"
{
    Properties
    {
        [HDR] _Color ("Colour", Color) = (0.6, 1.1, 1.2, 1)
        _Intensity ("Intensity", Range(0, 4)) = 0.6
        _EdgeSoftness ("Edge Softness", Range(0.01, 0.5)) = 0.3
        _FalloffPower ("Falloff Power", Range(0.2, 4)) = 1.4
        _StreakScale ("Streak Scale", Float) = 6
        _StreakSpeed ("Streak Speed", Float) = 0.15
        _Flicker ("Flicker", Range(0, 1)) = 0.15
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "Queue" = "Transparent-20" }

        Pass
        {
            Name "Shaft"
            Tags { "LightMode" = "UniversalForward" }
            Blend One One
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "DeadCellsNoise.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _Color;
                half _Intensity;
                half _EdgeSoftness;
                half _FalloffPower;
                float _StreakScale;
                float _StreakSpeed;
                half _Flicker;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float3 positionWS : TEXCOORD1; };

            Varyings Vert(Attributes v)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(v.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.uv = v.uv;
                return o;
            }

            half4 Frag(Varyings i) : SV_Target
            {
                half edge = smoothstep(0.0h, _EdgeSoftness, i.uv.x) * smoothstep(0.0h, _EdgeSoftness, 1.0h - i.uv.x);
                half fall = pow(saturate(i.uv.y), _FalloffPower);
                half streak = DCValueNoise2(float2(i.uv.x * _StreakScale + _Time.y * _StreakSpeed, i.uv.y * 1.5));
                streak = lerp(0.55h, 1.25h, streak);
                half flicker = 1.0h - _Flicker * (0.5h + 0.5h * sin(_Time.y * 1.7 + i.positionWS.x));
                return half4(_Color.rgb * (_Intensity * edge * fall * streak * flicker), 1.0h);
            }
            ENDHLSL
        }
    }
}
