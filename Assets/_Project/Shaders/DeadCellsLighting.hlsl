#ifndef DEADCELLS_LIGHTING_INCLUDED
#define DEADCELLS_LIGHTING_INCLUDED

// Shared stylised lighting for the Dead Cells slice.
// Cel ramp (2-3 hard tonal steps), hard-stepped specular glint, Fresnel rim
// biased towards world-up, per-light coloured rim and banded light falloff.
// Requires Core.hlsl + Lighting.hlsl to be included first.

// Global art-direction values, pushed by DCAtmosphere.cs.
float4 _DC_FogColor;    // rgb = fog colour, a = max fog amount
float4 _DC_FogParams;   // x = fog start (world z), y = density per metre, z = floor glow height, w = floor glow amount
float4 _DC_AmbientColor; // rgb = flat ambient fill, a = unused
float4 _DC_PixelParams; // x = low-res width, y = low-res height, z = integer pixel scale, w = 1 if pixelation active

struct DCToonInputs
{
    half4 ramp;          // x = step1, y = step2, z = softness, w = mid band value
    half3 shadowTint;    // colour the unlit side of the key light falls to
    half  specThreshold;
    half  specIntensity;
    half3 specColor;
    half  rimPower;
    half  rimThreshold;
    half  rimUpBias;
    half  rimStrength;
    half3 rimColor;
    half  rimLightStrength;
    half  rimLightWrap;
    half  attenBands;
    half  lightGlow;     // albedo-independent scatter around punctual lights (haze halo)
};

struct DCSurface
{
    half3 albedo;
    half3 normalWS;
    half  occlusion;
    half  roughness;
    half  metallic;
};

half DCToonRamp(half x, half4 ramp)
{
    half t1 = smoothstep(ramp.x - ramp.z, ramp.x + ramp.z, x);
    half t2 = smoothstep(ramp.y - ramp.z, ramp.y + ramp.z, x);
    return t1 * lerp(ramp.w, 1.0h, t2);
}

// Quantise the smooth URP falloff into soft bands (stylised light pools).
half DCBandAtten(half atten, half bands)
{
    if (bands < 1.0h)
        return atten;
    half scaled = atten * bands;
    half stepped = floor(scaled) + smoothstep(0.35h, 0.65h, frac(scaled));
    return saturate(stepped / bands);
}

half DCRimMask(half3 N, half3 V, DCToonInputs t)
{
    half fresnel = pow(1.0h - saturate(dot(N, V)), t.rimPower);
    return smoothstep(t.rimThreshold - 0.06h, t.rimThreshold + 0.06h, fresnel);
}

half3 DCSpecular(half3 N, half3 V, half3 L, half rampTerm, DCSurface s, DCToonInputs t)
{
    half3 H = SafeNormalize(L + V);
    half shininess = exp2(10.0h * (1.0h - s.roughness) + 1.0h);
    half spec = pow(saturate(dot(N, H)), shininess) * rampTerm;
    half glint = smoothstep(t.specThreshold - 0.015h, t.specThreshold + 0.015h, spec);
    half3 tint = lerp(t.specColor, s.albedo * 1.5h + 0.35h, s.metallic);
    return glint * tint * t.specIntensity * lerp(0.25h, 1.0h, s.metallic);
}

// Key light: unlit side falls to the shadow tint instead of black.
half3 DCMainLight(Light light, DCSurface s, half3 V, DCToonInputs t)
{
    half3 L = light.direction;
    half ndl = dot(s.normalWS, L);
    half halfLambert = ndl * 0.5h + 0.5h;
    half ramp = DCToonRamp(halfLambert * lerp(0.35h, 1.0h, light.shadowAttenuation), t.ramp);
    half3 diffuseCol = s.albedo * (1.0h - s.metallic * 0.6h);
    half3 col = diffuseCol * light.color * lerp(t.shadowTint, half3(1.0h, 1.0h, 1.0h), ramp);
    col += DCSpecular(s.normalWS, V, L, ramp, s, t) * light.color;
    col += DCRimMask(s.normalWS, V, t) * saturate(ndl + t.rimLightWrap) * light.color * t.rimLightStrength * light.shadowAttenuation;
    return col;
}

// Punctual lights: banded falloff, toon ramp, coloured rim.
half3 DCPunctualLight(Light light, DCSurface s, half3 V, DCToonInputs t)
{
    half3 L = light.direction;
    half ndl = dot(s.normalWS, L);
    half atten = DCBandAtten(light.distanceAttenuation, t.attenBands) * light.shadowAttenuation;
    half ramp = DCToonRamp(ndl * 0.5h + 0.5h, t.ramp);
    half3 diffuseCol = s.albedo * (1.0h - s.metallic * 0.6h);
    half3 col = diffuseCol * light.color * ramp * atten;
    col += DCSpecular(s.normalWS, V, L, ramp, s, t) * light.color * atten;
    col += DCRimMask(s.normalWS, V, t) * saturate(ndl + t.rimLightWrap) * light.color * atten * t.rimLightStrength;
    // View-independent warm halo so dark surfaces still show the light pool.
    col += light.color * atten * t.lightGlow * (ndl * 0.25h + 0.75h);
    return col;
}

half3 DCShade(InputData inputData, DCSurface s, DCToonInputs t, half ambientStrength)
{
    half3 V = inputData.viewDirectionWS;
    half4 shadowMask = half4(1, 1, 1, 1);
    Light mainLight = GetMainLight(inputData.shadowCoord, inputData.positionWS, shadowMask);

    half3 color = DCMainLight(mainLight, s, V, t);

    #if defined(_ADDITIONAL_LIGHTS)
    uint pixelLightCount = GetAdditionalLightsCount();
    #if USE_CLUSTER_LIGHT_LOOP
    [loop] for (uint lightIndex = 0; lightIndex < min(URP_FP_DIRECTIONAL_LIGHTS_COUNT, MAX_VISIBLE_LIGHTS); lightIndex++)
    {
        CLUSTER_LIGHT_LOOP_SUBTRACTIVE_LIGHT_CHECK
        Light light = GetAdditionalLight(lightIndex, inputData.positionWS, shadowMask);
        color += DCPunctualLight(light, s, V, t);
    }
    #endif
    LIGHT_LOOP_BEGIN(pixelLightCount)
        Light light = GetAdditionalLight(lightIndex, inputData.positionWS, shadowMask);
        color += DCPunctualLight(light, s, V, t);
    LIGHT_LOOP_END
    #endif

    // Ambient: probe SH + flat art-directed fill, both occluded.
    half3 ambient = (SampleSH(s.normalWS) * ambientStrength + _DC_AmbientColor.rgb) * s.albedo * s.occlusion;
    color += ambient;

    // Overhead rim: Fresnel x world-up bias.
    half up = pow(saturate(s.normalWS.y * 0.5h + 0.5h), t.rimUpBias);
    color += DCRimMask(s.normalWS, V, t) * up * t.rimColor * t.rimStrength;
    return color;
}

// Depth fog towards the background layers plus a low floor glow.
half3 DCApplyFog(half3 color, float3 positionWS)
{
    // Exponential with distance behind the start plane: z=2.5 back wall
    // ~25%, z=5 ruins ~50%, z=10 towers ~75% (density 0.15).
    half depthFog = (1.0h - exp(-max(0.0, positionWS.z - _DC_FogParams.x) * _DC_FogParams.y)) * _DC_FogColor.a;
    half floorGlow = saturate((_DC_FogParams.z - positionWS.y) / 4.0h) * _DC_FogParams.w * saturate(positionWS.z / 6.0h);
    color = lerp(color, _DC_FogColor.rgb, saturate(depthFog + floorGlow * 0.5h));
    return color;
}

#endif
