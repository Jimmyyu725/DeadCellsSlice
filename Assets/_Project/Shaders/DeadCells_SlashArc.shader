// Weapon slash ribbon. Mesh is rebuilt every frame by SlashArc.cs:
// uv.x = age along the trail (0 = at the blade now, 1 = oldest sample),
// uv.y = position along the blade (0 = hilt, 1 = tip), vertex alpha = fade.
Shader "DeadCells/SlashArc"
{
    Properties
    {
        [HDR] _CoreColor ("Core Colour", Color) = (6, 6, 6, 1)
        [HDR] _ArcColor ("Arc Colour", Color) = (1.2, 2.6, 3.2, 1)
        [HDR] _EdgeColor ("Trailing Edge Colour", Color) = (0.6, 0.2, 1.6, 1)
        _Bands ("Bands", Range(2, 8)) = 4
        _NoiseScale ("Noise Scale", Float) = 5
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "Queue" = "Transparent+10" }

        Pass
        {
            Name "Slash"
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
                half4 _CoreColor;
                half4 _ArcColor;
                half4 _EdgeColor;
                half _Bands;
                float _NoiseScale;
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
                half age = i.uv.x;
                half span = i.uv.y;
                half lead = 1.0h - age;
                // Crescent: thick near the tip, thinning towards the hilt and the tail.
                half width = lerp(0.15h, 1.0h, smoothstep(0.1h, 0.95h, span)) * lead;
                half body = smoothstep(1.0h - width, 1.0h - width * 0.6h, 1.0h - span * 0.98h) * (1.0h - smoothstep(0.97h, 1.0h, span));
                half n = DCValueNoise2(float2(age * _NoiseScale * 2.0 - _Time.y * 4.0, span * _NoiseScale));
                half intensity = saturate(body * (lead * 1.3h) * (0.75h + 0.5h * n)) * i.color.a;
                half q = floor(intensity * _Bands + 0.35h) / _Bands;
                clip(q - 0.01h);
                half3 col = lerp(_EdgeColor.rgb, _ArcColor.rgb, smoothstep(0.2h, 0.5h, q));
                col = lerp(col, _CoreColor.rgb, smoothstep(0.7h, 0.95h, q) * smoothstep(0.55h, 0.9h, span));
                return half4(col * q * i.color.rgb, 1.0h);
            }
            ENDHLSL
        }
    }
}
