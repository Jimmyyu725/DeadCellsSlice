#ifndef DEADCELLS_NOISE_INCLUDED
#define DEADCELLS_NOISE_INCLUDED

// Small hash-based value noise used by the flame, smoke, slash and shaft
// shaders (no texture fetches, stable across platforms).

float DCHash31(float3 p)
{
    p = frac(p * 0.1031);
    p += dot(p, p.zyx + 31.32);
    return frac((p.x + p.y) * p.z);
}

float DCValueNoise3(float3 p)
{
    float3 i = floor(p);
    float3 f = frac(p);
    float3 u = f * f * (3.0 - 2.0 * f);
    float n000 = DCHash31(i);
    float n100 = DCHash31(i + float3(1, 0, 0));
    float n010 = DCHash31(i + float3(0, 1, 0));
    float n110 = DCHash31(i + float3(1, 1, 0));
    float n001 = DCHash31(i + float3(0, 0, 1));
    float n101 = DCHash31(i + float3(1, 0, 1));
    float n011 = DCHash31(i + float3(0, 1, 1));
    float n111 = DCHash31(i + float3(1, 1, 1));
    float nx00 = lerp(n000, n100, u.x);
    float nx10 = lerp(n010, n110, u.x);
    float nx01 = lerp(n001, n101, u.x);
    float nx11 = lerp(n011, n111, u.x);
    return lerp(lerp(nx00, nx10, u.y), lerp(nx01, nx11, u.y), u.z);
}

float DCFbm3(float3 p)
{
    float v = 0.0;
    float a = 0.5;
    [unroll] for (int k = 0; k < 3; k++)
    {
        v += DCValueNoise3(p) * a;
        p = p * 2.03 + 11.7;
        a *= 0.5;
    }
    return v / 0.875;
}

float DCValueNoise2(float2 p)
{
    return DCValueNoise3(float3(p, 0.0));
}

#endif
