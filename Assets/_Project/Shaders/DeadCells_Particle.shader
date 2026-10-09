// Particles: sparks, embers, dust motes, blood/ichor, cells.
// _Shape: 0 = hard square (pixel spark), 1 = soft disc, 2 = hard disc.
// Blend is configurable so the same shader serves additive glow and
// alpha-blended debris.
Shader "DeadCells/Particle"
{
    Properties
    {
        [HDR] _Color ("Colour", Color) = (1, 1, 1, 1)
        _Intensity ("Intensity", Range(0, 16)) = 1
        [Enum(Square,0,Soft Disc,1,Hard Disc,2)] _Shape ("Shape", Float) = 1
        _Softness ("Disc Softness", Range(0.01, 1)) = 0.6
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src Blend", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst Blend", Float) = 1
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "Queue" = "Transparent" "IgnoreProjector" = "True" }

        Pass
        {
            Name "Particle"
            Tags { "LightMode" = "UniversalForward" }
            Blend [_SrcBlend] [_DstBlend]
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _Color;
                half _Intensity;
                half _Shape;
                half _Softness;
                half _SrcBlend;
                half _DstBlend;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; half4 color : COLOR; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; half4 color : COLOR; };

            Varyings Vert(Attributes v)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                o.uv = v.uv;
                o.color = v.color;
                return o;
            }

            half4 Frag(Varyings i) : SV_Target
            {
                half d = length(i.uv - 0.5h) * 2.0h;
                half mask = 1.0h;
                if (_Shape > 1.5h)
                    mask = step(d, 1.0h);
                else if (_Shape > 0.5h)
                    mask = saturate((1.0h - d) / _Softness);
                half4 c = i.color * _Color;
                c.rgb *= _Intensity;
                c.a *= mask;
                // Additive (One One) wants premultiplied colour.
                if (_DstBlend == 1.0h)
                    c.rgb *= c.a;
                return c;
            }
            ENDHLSL
        }
    }
}
