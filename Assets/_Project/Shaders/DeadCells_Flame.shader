// Flame-cluster head. Vertex colours from Blender: R = heat (core 1 -> tips 0),
// G = wobble weight (base 0 -> tips 1), B = per-tendril phase.
Shader "DeadCells/Flame"
{
    Properties
    {
        [HDR] _CoreColor ("Core Colour", Color) = (4, 3.6, 4.4, 1)
        [HDR] _FlameColor ("Flame Colour", Color) = (2.4, 1.1, 4.2, 1)
        [HDR] _TipColor ("Tip Colour", Color) = (0.55, 0.12, 1.1, 1)
        _Intensity ("Intensity", Range(0, 8)) = 1.6
        _Bands ("Heat Bands", Range(2, 8)) = 4
        _Cutoff ("Tip Cutoff", Range(0, 0.6)) = 0.16
        _NoiseScale ("Noise Scale", Float) = 7
        _NoiseSpeed ("Noise Rise Speed", Float) = 1.8
        _NoiseStrength ("Noise Strength", Range(0, 1.5)) = 0.7
        _WobbleAmp ("Wobble Amplitude (m)", Range(0, 0.1)) = 0.035
        _WobbleFreq ("Wobble Frequency", Float) = 9
        _WobbleSpeed ("Wobble Speed", Float) = 7
        _Lean ("Lean (world offset at tips)", Vector) = (0, 0, 0, 0)
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "TransparentCutout" "Queue" = "AlphaTest" }

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "DeadCellsNoise.hlsl"

        CBUFFER_START(UnityPerMaterial)
            half4 _CoreColor;
            half4 _FlameColor;
            half4 _TipColor;
            half _Intensity;
            half _Bands;
            half _Cutoff;
            float _NoiseScale;
            float _NoiseSpeed;
            half _NoiseStrength;
            float _WobbleAmp;
            float _WobbleFreq;
            float _WobbleSpeed;
            float4 _Lean;
        CBUFFER_END

        struct Attributes
        {
            float4 positionOS : POSITION;
            half4 color : COLOR;
            UNITY_VERTEX_INPUT_INSTANCE_ID
        };

        struct Varyings
        {
            float4 positionCS : SV_POSITION;
            float3 positionWS : TEXCOORD0;
            half4 color : COLOR;
            UNITY_VERTEX_OUTPUT_STEREO
        };

        Varyings FlameVert(Attributes input)
        {
            Varyings o = (Varyings)0;
            UNITY_SETUP_INSTANCE_ID(input);
            UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
            float3 p = TransformObjectToWorld(input.positionOS.xyz);
            float w = input.color.g;
            float phase = input.color.b * 6.2831853;
            float t = _Time.y * _WobbleSpeed;
            float3 offset;
            offset.x = sin(t + p.y * _WobbleFreq + phase) * _WobbleAmp * w;
            offset.z = cos(t * 1.31 + p.y * _WobbleFreq * 0.8 + phase) * _WobbleAmp * w * 0.6;
            offset.y = (sin(t * 2.07 + phase) * 0.5 + 0.5) * _WobbleAmp * 1.6 * w;
            p += offset + _Lean.xyz * (w * w);
            o.positionWS = p;
            o.positionCS = TransformWorldToHClip(p);
            o.color = input.color;
            return o;
        }

        half FlameHeat(Varyings i)
        {
            float3 q = i.positionWS * _NoiseScale + float3(0, -_Time.y * _NoiseSpeed * _NoiseScale * 0.25, i.color.b * 17.0);
            half n = DCFbm3(q);
            return saturate(i.color.r + (n - 0.5h) * _NoiseStrength);
        }
        ENDHLSL

        Pass
        {
            Name "Flame"
            Tags { "LightMode" = "UniversalForward" }
            Cull Off
            ZWrite On

            HLSLPROGRAM
            #pragma vertex FlameVert
            #pragma fragment Frag
            #pragma multi_compile_instancing

            half4 Frag(Varyings i) : SV_Target
            {
                half heat = FlameHeat(i);
                clip(heat - _Cutoff);
                half q = floor(heat * _Bands + 0.5h) / _Bands;
                half3 col = lerp(_TipColor.rgb, _FlameColor.rgb, smoothstep(0.15h, 0.5h, q));
                col = lerp(col, _CoreColor.rgb, smoothstep(0.62h, 0.9h, q));
                half pulse = 1.0h + 0.12h * sin(_Time.y * 11.0 + i.color.b * 40.0);
                return half4(col * _Intensity * pulse, 1.0h);
            }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }
            Cull Off
            ZWrite On
            ColorMask R

            HLSLPROGRAM
            #pragma vertex FlameVert
            #pragma fragment Frag
            #pragma multi_compile_instancing

            half Frag(Varyings i) : SV_Target
            {
                clip(FlameHeat(i) - _Cutoff);
                return i.positionCS.z;
            }
            ENDHLSL
        }
    }
}
