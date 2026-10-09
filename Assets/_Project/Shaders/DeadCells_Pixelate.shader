// Used by PixelateRenderFeature. Pass 0 point-samples the full-resolution
// camera colour into the integer-scaled low-res target; pass 1 upscales it
// back with nearest filtering, shifted by the camera's sub-pixel remainder so
// the snapped camera still scrolls smoothly.
Shader "Hidden/DeadCells/Pixelate"
{
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" }
        ZWrite Off ZTest Always Cull Off Blend Off

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.core/Runtime/Utilities/Blit.hlsl"

        float4 _DC_LowResTexel;  // xy = 1/size, zw = size
        float4 _DC_ScreenSize;   // xy = full-res size, z = integer scale
        float4 _DC_PixelOffset;  // xy = sub-pixel camera remainder in low-res pixels
        float _DC_ColorSteps;    // 0 = off, else per-channel levels
        ENDHLSL

        Pass
        {
            Name "Downsample"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag

            half4 Frag(Varyings input) : SV_Target
            {
                // Area-average this low-res texel's exact scale x scale block:
                // four bilinear taps at the quarter points cover it evenly, so
                // texture detail resolves to a stable colour instead of shimmering.
                float2 uv = input.texcoord.xy * _DC_LowResTexel.zw * _DC_ScreenSize.z / _DC_ScreenSize.xy;
                float2 quarter = (_DC_ScreenSize.z * 0.25) / _DC_ScreenSize.xy;
                half4 c = SAMPLE_TEXTURE2D_X_LOD(_BlitTexture, sampler_LinearClamp, uv + float2(-quarter.x, -quarter.y), 0);
                c += SAMPLE_TEXTURE2D_X_LOD(_BlitTexture, sampler_LinearClamp, uv + float2(quarter.x, -quarter.y), 0);
                c += SAMPLE_TEXTURE2D_X_LOD(_BlitTexture, sampler_LinearClamp, uv + float2(-quarter.x, quarter.y), 0);
                c += SAMPLE_TEXTURE2D_X_LOD(_BlitTexture, sampler_LinearClamp, uv + float2(quarter.x, quarter.y), 0);
                c *= 0.25h;
                // Keep the brightest tap's hue on thin emissive details (sparks of
                // light would otherwise average away).
                half4 centre = SAMPLE_TEXTURE2D_X_LOD(_BlitTexture, sampler_PointClamp, uv, 0);
                c = max(c, centre * 0.85h);
                if (_DC_ColorSteps > 0.5)
                {
                    // Quantise in a perceptual space so dark tones keep detail.
                    half3 g = sqrt(max(c.rgb, 0.0h));
                    g = floor(g * _DC_ColorSteps + 0.5h) / _DC_ColorSteps;
                    c.rgb = g * g;
                }
                return c;
            }
            ENDHLSL
        }

        Pass
        {
            Name "Upscale"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag

            half4 Frag(Varyings input) : SV_Target
            {
                // Exact integer blocks: screen pixel -> low-res texel, shifted by
                // the camera's sub-pixel remainder.
                float2 px = input.texcoord.xy * _DC_ScreenSize.xy;
                float2 texel = floor(px / _DC_ScreenSize.z + _DC_PixelOffset.xy);
                float2 uv = (texel + 0.5) * _DC_LowResTexel.xy;
                return SAMPLE_TEXTURE2D_X_LOD(_BlitTexture, sampler_PointClamp, uv, 0);
            }
            ENDHLSL
        }
    }
}
