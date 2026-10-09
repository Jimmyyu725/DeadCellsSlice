# 资产管线约定（Blender → Unity）

本文件是所有生成脚本共同遵守的「合同」。改约定先改这里。

## 坐标与单位

- 1 Blender 单位 = 1 米，Z 轴向上。
- 统一导出轴向：`axis_forward="Z"`, `axis_up="Y"`（即 Z-Forward / Y-Up）。
  效果：Blender 坐标 `(x, y, z)` 在 Unity 中就是 `(x, z, y)`，**没有镜像**。
- 游戏摄像机在 Unity 里从 `-Z` 看向 `+Z`，等价于 Blender 的 Front 视图（从 `-Y` 看向 `+Y`）。
  - 环境件：玩家看得到的面朝 Blender `-Y`；越往后（背景）Blender `y` 越大。
  - 游戏平面：Blender `y = 0`（= Unity `z = 0`），角色就站在这一层。
- 角色面朝 Blender `-Y`（= Unity `-Z`，朝向镜头），脚底在原点。游戏里由代码把模型转到 ±X 方向并带一点 3/4 侧角。
- 静态网格导出用 `export_fbx(..., static=True)`（轴向转换烘进顶点，Unity 里物体变换为单位矩阵）；带骨骼的用 `static=False`。

## 目录

| 内容 | 路径 |
|---|---|
| Blender 脚本 | `Tools/Blender/*.py`（共用库 `dc_common.py`） |
| 角色 FBX / 贴图 | `Assets/_Project/Art/Characters/<Name>/` |
| 武器 FBX / 贴图 | `Assets/_Project/Art/Weapons/` |
| 环境 FBX | `Assets/_Project/Art/Environment/Meshes/` |
| 环境贴图 | `Assets/_Project/Art/Environment/Textures/` |
| 预览图、临时文件 | `Tools/_out/`（不进 git） |

运行方式（headless，不碰正在打开的 Blender）：

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P Tools/Blender/<script>.py
```

## 贴图约定

每套贴图四张 PNG：

- `<Prefix>_Albedo.png`（sRGB）
- `<Prefix>_Normal.png`（切线空间，OpenGL 约定 +Y，Non-Color）
- `<Prefix>_ORM.png`（R = Occlusion，G = Roughness，B = Metallic，Non-Color）
- `<Prefix>_Emission.png`（sRGB，LDR 颜色遮罩；亮度在 Unity 材质里用 HDR 强度控制）

预算：角色 2048²；武器共用 1024²；环境前景共用一张 2048² 图集 `ENV_Kit_*`；远景剪影共用 1024² `BG_Kit_*`。

## 角色骨骼命名（The Beheaded / Zombie 共用）

```
root
└─ hips
   ├─ spine ─ chest ─ neck ─ head ─ head_socket
   │          ├─ shoulder.L ─ upper_arm.L ─ forearm.L ─ hand.L
   │          │                                └─ shield_socket   (forearm.L 子骨骼)
   │          ├─ shoulder.R ─ upper_arm.R ─ forearm.R ─ hand.R ─ weapon_socket
   │          └─ scarf_01 ─ scarf_02 ─ scarf_03 ─ scarf_04       (仅 Beheaded)
   ├─ thigh.L ─ shin.L ─ foot.L
   ├─ thigh.R ─ shin.R ─ foot.R
   ├─ coat_L_01 ─ coat_L_02 ─ coat_L_03
   └─ coat_R_01 ─ coat_R_02 ─ coat_R_03
```

所有肢体骨骼的局部 X 轴 = 世界 +X，所以「矢状面」（侧视游戏里最重要的摆动）都是绕局部 X 旋转。

## 动画（60 fps，原地动画，无根运动）

| Clip | 帧数 | 循环 |
|---|---|---|
| `Idle` | 60 | 是 |
| `Run` | 24 | 是 |
| `Slash_Combo_1` / `Slash_Combo_2` / `Slash_Combo_3` | 18 / 18 / 24 | 否 |
| `Dodge_Roll` | 20 | 否 |
| `Jump_Rise` / `Jump_Fall` | 12 / 12 | 是（保持姿势） |
| `Ground_Pound_Slam` | 24 | 否 |
| `Shield_Block` | 12 | 否（最后一帧保持） |
| `Hurt` | 14 | 否 |

攻击节奏：2 帧预备 → 1 帧挥砍（拖影姿势）→ 4 帧定格 → 回位。

## 环境模块（网格单元 1 m）

- 地块类：枢轴在格子左下角（游戏平面上），占 `x∈[0,1]`、`z∈[0,1]`，前表面在 `y≈-0.9`，向后延伸到 `y≈1.6`。
- 背景件放在 Unity `z = 1.5～3`；远景剪影放在 Unity `z = 5` 和 `z = 10`。
- `env_manifest.json` 记录每个模块的 FBX、尺寸（Unity 坐标）和挂点（例如火把的 `FlameSocket`）。
