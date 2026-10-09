#ifndef DEADCELLS_TOON_CORE_INCLUDED
#define DEADCELLS_TOON_CORE_INCLUDED

// Pass implementations shared by DeadCells/CharacterLit and
// DeadCells/EnvironmentLit. Define DC_ENVIRONMENT before including to get
// depth fog instead of the character-only hit flash.

#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
#include "DeadCellsLighting.hlsl"

TEXTURE2D(_BaseMap);      SAMPLER(sampler_BaseMap);
TEXTURE2D(_BumpMap);      SAMPLER(sampler_BumpMap);
TEXTURE2D(_ORMMap);       SAMPLER(sampler_ORMMap);
TEXTURE2D(_EmissionMap);  SAMPLER(sampler_EmissionMap);

CBUFFER_START(UnityPerMaterial)
    float4 _BaseMap_ST;
    half4  _BaseColor;
    half   _BumpScale;
    half   _OcclusionStrength;
    half   _RoughnessScale;
    half   _MetallicScale;
    half4  _EmissionColor;
    half   _EmissionPulseAmp;
    half   _EmissionPulseSpeed;
    half   _RampStep1;
    half   _RampStep2;
    half   _RampSmooth;
    half   _RampMid;
    half4  _ShadowTint;
    half   _GlintThreshold;
    half   _GlintIntensity;
    half4  _GlintColor;
    half   _RimPower;
    half   _RimThreshold;
    half   _RimUpBias;
    half   _RimStrength;
    half4  _RimColor;
    half   _RimLightStrength;
    half   _RimLightWrap;
    half   _AttenBands;
    half   _AmbientStrength;
    half4  _OutlineColor;
    half   _OutlinePixels;
    half   _HitFlash;
    half4  _HitFlashColor;
    half   _FogAmount;
    half   _TopShade;
    half   _LightGlow;
CBUFFER_END

struct Attributes
{
    float4 positionOS : POSITION;
    float3 normalOS   : NORMAL;
    float4 tangentOS  : TANGENT;
    float2 uv         : TEXCOORD0;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct Varyings
{
    float4 positionCS : SV_POSITION;
    float2 uv         : TEXCOORD0;
    float3 positionWS : TEXCOORD1;
    half3  normalWS   : TEXCOORD2;
    half4  tangentWS  : TEXCOORD3;
    UNITY_VERTEX_INPUT_INSTANCE_ID
    UNITY_VERTEX_OUTPUT_STEREO
};

DCToonInputs DCGetToonInputs()
{
    DCToonInputs t;
    t.ramp = half4(_RampStep1, _RampStep2, _RampSmooth, _RampMid);
    t.shadowTint = _ShadowTint.rgb;
    t.specThreshold = _GlintThreshold;
    t.specIntensity = _GlintIntensity;
    t.specColor = _GlintColor.rgb;
    t.rimPower = _RimPower;
    t.rimThreshold = _RimThreshold;
    t.rimUpBias = _RimUpBias;
    t.rimStrength = _RimStrength;
    t.rimColor = _RimColor.rgb;
    t.rimLightStrength = _RimLightStrength;
    t.rimLightWrap = _RimLightWrap;
    t.attenBands = _AttenBands;
    t.lightGlow = _LightGlow;
    return t;
}

// ---------------------------------------------------------------- ForwardLit

Varyings ToonVert(Attributes input)
{
    Varyings output = (Varyings)0;
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_TRANSFER_INSTANCE_ID(input, output);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);

    VertexPositionInputs pos = GetVertexPositionInputs(input.positionOS.xyz);
    VertexNormalInputs nrm = GetVertexNormalInputs(input.normalOS, input.tangentOS);
    output.positionCS = pos.positionCS;
    output.positionWS = pos.positionWS;
    output.normalWS = nrm.normalWS;
    output.tangentWS = half4(nrm.tangentWS, input.tangentOS.w * GetOddNegativeScale());
    output.uv = TRANSFORM_TEX(input.uv, _BaseMap);
    return output;
}

half4 ToonFrag(Varyings input) : SV_Target
{
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);

    half4 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv) * _BaseColor;
    half4 orm = SAMPLE_TEXTURE2D(_ORMMap, sampler_ORMMap, input.uv);
    half3 normalTS = UnpackNormalScale(SAMPLE_TEXTURE2D(_BumpMap, sampler_BumpMap, input.uv), _BumpScale);

    half3 bitangent = input.tangentWS.w * cross(input.normalWS, input.tangentWS.xyz);
    half3 normalWS = NormalizeNormalPerPixel(TransformTangentToWorld(normalTS,
        half3x3(input.tangentWS.xyz, bitangent, input.normalWS)));

    #if defined(DC_ENVIRONMENT)
    // Upward faces are seen at grazing angles in a side view: keep them
    // darker than the fronts so floors read as ledges, not glowing strips.
    albedo.rgb *= lerp(1.0h, _TopShade, smoothstep(0.55h, 0.9h, input.normalWS.y));
    #endif

    DCSurface s;
    s.albedo = albedo.rgb;
    s.normalWS = normalWS;
    s.occlusion = lerp(1.0h, orm.r, _OcclusionStrength);
    s.roughness = saturate(orm.g * _RoughnessScale);
    s.metallic = saturate(orm.b * _MetallicScale);

    InputData inputData = (InputData)0;
    inputData.positionWS = input.positionWS;
    inputData.normalWS = normalWS;
    inputData.viewDirectionWS = GetWorldSpaceNormalizeViewDir(input.positionWS);
    inputData.shadowCoord = TransformWorldToShadowCoord(input.positionWS);
    inputData.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(input.positionCS);

    half3 color = DCShade(inputData, s, DCGetToonInputs(), _AmbientStrength);

    // HDR emission with a time-driven pulse (flame glow, rune channels).
    half pulse = 1.0h + _EmissionPulseAmp * sin(_Time.y * _EmissionPulseSpeed + input.positionWS.y * 3.0);
    color += SAMPLE_TEXTURE2D(_EmissionMap, sampler_EmissionMap, input.uv).rgb * _EmissionColor.rgb * pulse;

    #if defined(DC_ENVIRONMENT)
    color = lerp(color, DCApplyFog(color, input.positionWS), _FogAmount);
    #else
    color = lerp(color, _HitFlashColor.rgb, _HitFlash);
    #endif
    return half4(color, 1.0h);
}

// ---------------------------------------------------------------- Outline (inverted hull, ~1 low-res pixel)

struct OutlineVaryings
{
    float4 positionCS : SV_POSITION;
    UNITY_VERTEX_OUTPUT_STEREO
};

OutlineVaryings OutlineVert(Attributes input)
{
    OutlineVaryings output = (OutlineVaryings)0;
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
    float4 positionCS = TransformObjectToHClip(input.positionOS.xyz);
    float3 normalWS = TransformObjectToWorldNormal(input.normalOS);
    float2 normalCS = mul((float3x3)GetWorldToHClipMatrix(), normalWS).xy;
    float2 res = _DC_PixelParams.w > 0.5 ? _DC_PixelParams.xy : _ScreenParams.xy;
    float len = max(length(normalCS), 1e-4);
    positionCS.xy += (normalCS / len) * (_OutlinePixels * 2.0 / res) * positionCS.w;
    output.positionCS = positionCS;
    return output;
}

half4 OutlineFrag(OutlineVaryings input) : SV_Target
{
    return half4(lerp(_OutlineColor.rgb, _HitFlashColor.rgb, _HitFlash * 0.5h), 1.0h);
}

// ---------------------------------------------------------------- ShadowCaster

float3 _LightDirection;
float3 _LightPosition;

struct ShadowVaryings
{
    float4 positionCS : SV_POSITION;
};

ShadowVaryings ShadowVert(Attributes input)
{
    ShadowVaryings output;
    UNITY_SETUP_INSTANCE_ID(input);
    float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
    float3 normalWS = TransformObjectToWorldNormal(input.normalOS);
    #if _CASTING_PUNCTUAL_LIGHT_SHADOW
    float3 lightDirectionWS = normalize(_LightPosition - positionWS);
    #else
    float3 lightDirectionWS = _LightDirection;
    #endif
    float4 positionCS = TransformWorldToHClip(ApplyShadowBias(positionWS, normalWS, lightDirectionWS));
    output.positionCS = ApplyShadowClamping(positionCS);
    return output;
}

half4 ShadowFrag(ShadowVaryings input) : SV_Target
{
    return 0;
}

// ---------------------------------------------------------------- DepthOnly / DepthNormals

struct DepthVaryings
{
    float4 positionCS : SV_POSITION;
    half3 normalWS : TEXCOORD0;
    UNITY_VERTEX_OUTPUT_STEREO
};

DepthVaryings DepthVert(Attributes input)
{
    DepthVaryings output = (DepthVaryings)0;
    UNITY_SETUP_INSTANCE_ID(input);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
    output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
    output.normalWS = TransformObjectToWorldNormal(input.normalOS);
    return output;
}

half DepthFrag(DepthVaryings input) : SV_Target
{
    return input.positionCS.z;
}

half4 DepthNormalsFrag(DepthVaryings input) : SV_Target
{
    return half4(NormalizeNormalPerPixel(input.normalWS), 0.0h);
}

#endif
