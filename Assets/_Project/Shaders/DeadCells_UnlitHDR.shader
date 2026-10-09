// Flat HDR emitter (flame eye, glowing pickups, torch coals). Optional pulse.
Shader "DeadCells/UnlitHDR"
{
    Properties
    {
        [HDR] _Color ("Colour", Color) = (6, 5.4, 4, 1)
        _PulseAmp ("Pulse Amplitude", Range(0, 1)) = 0.15
        _PulseSpeed ("Pulse Speed", Float) = 8
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Opaque" "Queue" = "Geometry" }

        Pass
        {
            Name "Unlit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _Color;
                half _PulseAmp;
                half _PulseSpeed;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; UNITY_VERTEX_OUTPUT_STEREO };

            Varyings Vert(Attributes v)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                return o;
            }

            half4 Frag(Varyings i) : SV_Target
            {
                return half4(_Color.rgb * (1.0h + _PulseAmp * sin(_Time.y * _PulseSpeed)), 1.0h);
            }
            ENDHLSL
        }
    }
}
