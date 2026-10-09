# 区域（Biome）资产约定

运行时关卡生成器按下面的**模块角色名**取网格，所以每个区域的套件必须提供同一组角色。坐标、轴向、贴图规则沿用 `Tools/PIPELINE.md`（Blender (x,y,z) = Unity (x,z,y)；可见面朝 Blender -Y；游戏平面 y=0；静态网格 `export_fbx(..., static=True)`）。

## 区域列表（剧情顺序）

| Id | 中文 | English | 氛围 / 配色 |
|---|---|---|---|
| `Oubliette` | 地牢·排污闸 | The Oubliette | 现有套件（`Art/Environment`），青蓝石砖、苔藓、暖火把 |
| `Promenade` | 悬月长廊 | Promenade of the Suspended Moons | 深靛夜空、苍白月光、银色蛛丝、碎月块悬空、城墙栈道 |
| `Ossuary` | 遗忘回声骨窟 | Ossuary of the Forgotten Echoes | 漂白骨质建筑（巨兽肋骨）、地下雾、滴绿蜡的烛龛 |
| `StiltVillage` | 溺钟高脚村 | Stilt Village of the Drowned Chime | 鸟足般高脚上的木塔、沸腾的薰衣草酒海、紫色水雾 |
| `ClockLung` | 钟匠之肺 | The Clockmaker's Lung | 大教堂尺度的机械管风琴、黄铜熔炉、齿轮、星光 |

## 每个区域必须提供的模块（`<Id>_<Role>`）

| 角色 | 尺寸 / 枢轴 | 说明 |
|---|---|---|
| `Fill_A` `Fill_B` `Fill_C` | 1×1 地块，枢轴左下，前面 y≈-0.9，后延到 y≈1.6，顶面 z=1 | 实心填充（墙体/地下） |
| `Top_A` `Top_B` | 同上 | 顶面有区域特色覆盖物（苔藓/月尘/骨粉/湿木/铜锈），可向前垂挂 |
| `Edge_L` `Edge_R` | 同上 | 平台左右端的表层件 |
| `Platform` | 1 m 宽单向平台，枢轴左下，台面 z=1，厚 ≤0.2 | 区域材质（石梁/骨梁/木板/铁格栅） |
| `BackWall` | 4×4 m 背墙板，枢轴左下，前面 y=0，厚 ≤0.4，四向无缝 | |
| `Pillar` | 宽 ≤1 m，高 5 m，枢轴底部中心 | 背景立柱 |
| `Arch` | 宽 ~6 m，高 ~5.5 m，枢轴底部中心 | 背景大拱/框架 |
| `Light` | 墙挂光源，枢轴为贴墙点，带子空物体 `LightSocket` | 火把/提灯/烛龛/火盆；发光部分写入自发光遮罩 |
| `Hang` | 垂挂物，枢轴在顶部挂点，向下 2–3 m | 蛛丝/风铃/锁链/管线 |
| `Door` | 宽 ~2.4 m，高 ~3.2 m，枢轴底部中心，凹进深度 ≤0.8 m | 背景门洞 |
| `Prop_A` `Prop_B` `Prop_C` | 地面小道具，枢轴底部中心，高 ≤1.2 m | |
| `BG_Near` | ~20×10 m 剪影，枢轴底部中心 | 放在 Unity z=5 |
| `BG_Far_A` `BG_Far_B` | 高 16–25 m 剪影，枢轴底部中心 | 放在 Unity z=10 / 16 |

## 区域特色模块（额外）

| 区域 | 模块 |
|---|---|
| Promenade | `Promenade_MoonChunk`（悬空碎月块，直径 3–5 m，枢轴中心）、`Promenade_ClockTower`（远景钟塔，高 25 m） |
| Ossuary | `Ossuary_RibArch`（巨兽肋骨拱，跨度 8 m，枢轴底部中心）、`Ossuary_SkullWall`（4×4 背墙变体） |
| StiltVillage | `StiltVillage_Stilt`（高脚柱，高 6 m，枢轴顶部，向下延伸）、`StiltVillage_Pagoda`（远景塔楼屋顶） |
| ClockLung | `ClockLung_Gear`（齿轮，直径 2–4 m，枢轴中心，便于 Unity 里旋转）、`ClockLung_OrganPipes`（远景管风琴，高 20 m）、`ClockLung_Furnace`（熔炉，带 `LightSocket`） |

## 输出

- FBX：`Assets/_Project/Art/Biomes/<Id>/Meshes/<Id>_<Role>.fbx`
- 贴图：`Assets/_Project/Art/Biomes/<Id>/Textures/<Id>_Kit_{Albedo,Normal,ORM,Emission}.png`（2048）和 `<Id>_BG_*.png`（1024）
- 清单：`Assets/_Project/Art/Biomes/<Id>/biome_manifest.json`，格式同 `env_manifest.json`（Unity 坐标的 bounds、sockets、tris）

## 角色骨骼补充

Beheaded 新增 `offhand_socket`（`hand.L` 的子骨骼，指向前方），用于弓和副手匕首。敌人沿用同一套骨骼命名（见 `PIPELINE.md`），体型和比例可以不同。
