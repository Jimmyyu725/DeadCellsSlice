// Stylised cel-lit surface; lighting lives in DeadCellsLighting.hlsl / DeadCellsToonCore.hlsl.
Shader "DeadCells/CharacterLit"
{
    Properties
    {
        [Header(Surface)]
        [MainTexture] _BaseMap ("Albedo", 2D) = "white" {}
        [MainColor] _BaseColor ("Tint", Color) = (1,1,1,1)
        [Normal][NoScaleOffset] _BumpMap ("Normal Map", 2D) = "bump" {}
        _BumpScale ("Normal Strength", Range(0, 2)) = 1
        [NoScaleOffset] _ORMMap ("ORM (Occlusion, Roughness, Metallic)", 2D) = "white" {}
        _OcclusionStrength ("Occlusion Strength", Range(0, 1)) = 1
        _RoughnessScale ("Roughness Scale", Range(0, 2)) = 1
        _MetallicScale ("Metallic Scale", Range(0, 1)) = 1

        [Header(Emission)]
        [NoScaleOffset] _EmissionMap ("Emission Mask", 2D) = "black" {}
        [HDR] _EmissionColor ("Emission Colour", Color) = (0,0,0,1)
        _EmissionPulseAmp ("Pulse Amplitude", Range(0, 1)) = 0.25
        _EmissionPulseSpeed ("Pulse Speed", Float) = 6

        [Header(Toon Ramp)]
        _RampStep1 ("Shadow Edge", Range(0, 1)) = 0.42
        _RampStep2 ("Highlight Edge", Range(0, 1)) = 0.72
        _RampSmooth ("Edge Softness", Range(0.001, 0.2)) = 0.02
        _RampMid ("Mid Tone", Range(0, 1)) = 0.62
        _ShadowTint ("Shadow Tint", Color) = (0.32, 0.30, 0.52, 1)
        _AttenBands ("Light Falloff Bands (0 = smooth)", Range(0, 8)) = 4
        _AmbientStrength ("Ambient (probe) Strength", Range(0, 2)) = 0.6

        [Header(Specular Glint)]
        _GlintThreshold ("Glint Threshold", Range(0, 1)) = 0.5
        _GlintIntensity ("Glint Intensity", Range(0, 4)) = 1.2
        _GlintColor ("Glint Colour", Color) = (1, 0.95, 0.85, 1)

        [Header(Rim)]
        _RimPower ("Rim Power", Range(0.5, 8)) = 3
        _RimThreshold ("Rim Threshold", Range(0, 1)) = 0.35
        _RimUpBias ("Rim Up Bias", Range(0, 8)) = 2
        _RimStrength ("Overhead Rim Strength", Range(0, 4)) = 0.6
        [HDR] _RimColor ("Overhead Rim Colour", Color) = (0.55, 0.85, 1.0, 1)
        _RimLightStrength ("Per-Light Rim Strength", Range(0, 4)) = 1.4
        _RimLightWrap ("Per-Light Rim Wrap", Range(0, 1)) = 0.35
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2

        [Header(Outline and Feedback)]
        _OutlineColor ("Outline Colour", Color) = (0.03, 0.02, 0.06, 1)
        _OutlinePixels ("Outline Width (low-res px)", Range(0, 3)) = 1
        _HitFlash ("Hit Flash", Range(0, 1)) = 0
        [HDR] _HitFlashColor ("Hit Flash Colour", Color) = (2, 2, 2, 1)
        _TopShade ("Top Face Shade", Range(0, 1)) = 1
        _FogAmount ("Fog Amount", Range(0, 1)) = 0
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Opaque" "Queue" = "Geometry" }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Cull [_Cull]
            ZWrite On

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex ToonVert
            #pragma fragment ToonFrag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_instancing
            // character
            #include "DeadCellsToonCore.hlsl"
            ENDHLSL
        }
        Pass
        {
            Name "Outline"
            Tags { "LightMode" = "SRPDefaultUnlit" }
            Cull Front
            ZWrite On

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex OutlineVert
            #pragma fragment OutlineFrag
            #pragma multi_compile_instancing
            #include "DeadCellsToonCore.hlsl"
            ENDHLSL
        }
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            ZWrite On
            ZTest LEqual
            ColorMask 0
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex ShadowVert
            #pragma fragment ShadowFrag
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #pragma multi_compile_instancing
            // character
            #include "DeadCellsToonCore.hlsl"
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }
            ZWrite On
            ColorMask R
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex DepthVert
            #pragma fragment DepthFrag
            #pragma multi_compile_instancing
            // character
            #include "DeadCellsToonCore.hlsl"
            ENDHLSL
        }

        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode" = "DepthNormals" }
            ZWrite On
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex DepthVert
            #pragma fragment DepthNormalsFrag
            #pragma multi_compile_instancing
            // character
            #include "DeadCellsToonCore.hlsl"
            ENDHLSL
        }
    }
    FallBack "Hidden/Universal Render Pipeline/FallbackError"
}
