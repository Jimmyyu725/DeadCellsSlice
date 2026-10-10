# Dead Cells Slice — 搅沸永劫（The Churning）

用 Blender（Python 程序化建模、绑定、动画、烘焙）+ Unity 6 URP（自定义卡通 shader、像素化 Render Feature、手感系统）做的《Dead Cells》风格横版 Roguelite。剧情取自《The Churning》设定：余烬血块附身无头囚犯，从地牢底层一路向上，穿过四个区域，直到钟匠之肺的时间守护者。

所有美术资产、音效和配乐都由脚本生成，关卡在运行时由房间模板拼出，整个项目可一键重建。

![主菜单](Docs/shot_menu.jpg)

| | |
|---|---|
| ![遗忘回声骨堂](Docs/shot_ossuary.jpg) | ![溺钟高脚村](Docs/shot_stilt.jpg) |
| ![钟匠之肺](Docs/shot_lung.jpg) | ![皇家守卫](Docs/shot_boss.jpg) |
| ![传送地图](Docs/shot_map.jpg) | ![收藏家](Docs/shot_collector.jpg) |

## 直接玩

```bash
open "Builds/DeadCellsSlice.app"
```

（`Builds/` 不进 git；没有时先按下面「重建」生成。）

| 操作 | 键盘 / 鼠标 | 手柄 |
|---|---|---|
| 移动 | A / D 或 ← → | 左摇杆 / 十字键 |
| 跳跃（按住更高；空中再按一次二段跳；撞墙时自动攀上边缘） | Space | A |
| 主武器 / 副武器（按住连续攻击） | J 或左键 / K 或右键 | X / Y |
| 技能 1 / 技能 2 | Q / E | LT / RT |
| 翻滚（无敌帧） | Shift 或 L | B |
| 交互（拾取、购买、开箱、传送、阅读） | F | LB |
| 血瓶 | R | RB |
| 地图 | Tab 或 M | View |
| 暂停 | Esc | Menu |
| 下砸 / 穿过木平台 | 空中 S + Space / 站在平台上 S + Space | 下 + A |
| 背包换武器（收藏家处解锁） | C | 右摇杆按下 |

盾牌按住格挡，举起后 0.2 秒内被击中为完美格挡（眩晕敌人、反弹投射物）。

## 游戏内容

- **主菜单**：继续、新游戏、成就、更新日志、设置、作弊（解锁后）、退出。新游戏可选模式：**标准、每日挑战、自定义、首领车轮战**。设置里可切换 **中文 / English**、屏幕震动、火焰颜色、全屏、显示坐标、**辅助模式**（受到伤害比例、每区一次复活）。
- **流程**：地牢底层 → 悬月长廊（或分支：毒水下水道）→ 遗忘回声骨堂（Boss：皇家守卫）→ 溺钟高脚村（或分支：落日城墙）→ 钟匠之肺（Boss：时间守护者）→（2 个以上 Boss 细胞）观星台（真结局 Boss：收藏家）。区域之间是水闸通道，有泉水、收藏家、变异者和铁匠；分支路线的门在通道高处，需要对应符文。
- **关卡**：每次进入区域时，用 47 个手写房间模板（含镜像）随机拼出约 16–22 个房间。主路线左右延伸、高低起伏，侧室（商店、宝藏、石板、精英）通过竖井挂在上下方。
- **难度**：开局选简单 / 普通 / 困难。在最高已解锁的 Boss 细胞等级通关后解锁下一级，最多 5 级。等级越高，敌人越强、精英越多、诅咒宝箱越多，泉水回复越少；2 级起时间守护者之后会打开观星台；4 级起出现**疫病**（停留越久受伤越重，喝血瓶缓解）。
- **成长（同 Dead Cells）**：三色卷轴（暴虐 / 战术 / 生存二选一）、装备品质（+ / ++ / 传说）和 21 种随机词缀、护符栏、背包、可回复生命（橙色血条）、16 种变异（每个通道选一次，最多 3 个）、铁匠强化与重铸。
- **探索**：限时门、诅咒宝箱、三枚永久符文（藤蔓 / 撞击 / 蛛行，由符文守卫携带）、裂墙和公羊地板后的隐藏房间、藤蔓攀爬、墙跳。
- **模式**：每日挑战（按日期生成同一套关卡和武器，打到皇家守卫为止，记录当天最佳时间）、自定义（起点、敌人血量、初始金币、全装备掉落）、首领车轮战（强力开局，连战各 Boss）。自定义局和辅助模式不解锁成就。
- **裁缝**：起点房间的裁缝卖 10 套服装，改变身体和火焰颜色；部分服装由高 Boss 细胞、每日挑战、车轮战和真结局解锁。
- **存档**：每次进入区域时自动存档，主菜单「继续」从当前区域入口开始。死亡后本局结束，未花掉的细胞和金币清零。收藏家处的解锁、成就和统计永久保留。
- **商店与收藏家**：商人用金币卖装备。精英、Boss、宝箱会掉落图纸，在通道里交给收藏家并花细胞解锁，之后才会出现在掉落和商店里；收藏家也卖血瓶容量、永久生命、锻造等级、背包、金币保留和变异解锁。
- **传送点（同 Dead Cells）**：靠近石像就会点亮，同时标进地图。在石像旁按交互打开地图，选另一座已点亮的石像就能传送。地图有战争迷雾，标出你、传送点、出口、商店、宝藏和石板。
- **剧情**：序章（大蒸馏、时序之神的断齿、余烬血块的诞生）、苏醒字幕、区域标题与引言、13 块碎裂石板、NPC 与 Boss 台词、死亡画面「无药可救的轮回」，以及击败时间守护者后的结局。
- **声音**：80 种音效（挥砍、命中、暴击、敌人预警、拾取、界面等）、8 首可循环配乐（主菜单、五个区域、水闸通道、Boss 战）和 6 段环境声，全部由 `Tools/Audio/` 用 numpy 合成。设置里可分别调节音乐和音效音量。
- **成就**：32 个，覆盖探索、Boss、Boss 细胞、困难通关、无伤区域、速通、收集、石板、传送、死亡次数、限时门、诅咒宝箱、变异、传说装备、隐藏房间、符文、分支路线、真结局、每日挑战和车轮战。用过作弊、自定义或辅助模式的那一局不能解锁成就。
- **作弊**：在主菜单直接键入 `CHURN` 解锁作弊菜单，可开无敌、一击必杀、无冷却，加金币和细胞，回满，显示全地图，跳关，解锁全部图纸或全部 Boss 细胞。

### 装备

共 76 件武器和 4 个护符：最初的 10 件、0.3 版的 6 件，0.5 版新增的 60 件，以及 0.6 版的护符。每件都有独立的 Blender 模型；新增装备的图标由模型直接渲染。每件武器带一种或两种颜色（暴虐 / 战术 / 生存），掉落时随机品质和词缀。

| 类型 | 物品 |
|---|---|
| 近战（30） | 锈蚀的刽子手砍刀（初始）、生锈的剑、阔剑、潮卫长矛、双子蜱刺、碎钟锤、钟摆细剑、潮汐镰刀、锁链流星、掘墓铲；余烬断齿（燃烧暴击）、月镰双刃、鲸肋大剑（终结冲击波）、钟摆战斧、薰衣草酒瓶棍（中毒）、溺亡之锚（终结拉拽）、蛛丝长鞭（超长距离）、齿轮链锯、烛台三叉戟、时针长枪、雷鳗鞭、骷髅权杖（吸血）、熔炉火钳、牧月钩杖、星砂太刀（空中暴击）、鲨齿锯刃、狱卒巨钥（克制精英与 Boss）、渡魂船桨、指挥家之棒（连击叠伤）、余烬拳套 |
| 远程（22） | 尖刺弓、鱼骨十字弩；月牙长弓（贯穿）、三连弩（连射）、霰弹火铳（散射）、蜱刺吹箭（中毒）、冰霜投石索、回旋月轮（回旋）、飞刀扇、雷弦琴弓（闪电连锁）、钟声号角（声波击退）、墨鱼喷枪（减速）、骨笛（追踪）、星屑魔杖（反弹）、鱼叉枪（拉拽）、蒸汽钉枪（速射）、余烬臼炮、泡泡枪、时钟弩（冻结）、碎石弹弓、提灯光矛、六分仪狙击枪（远距离三倍暴击） |
| 盾（7） | 前线盾牌；铜钟盾（范围眩晕）、镜月盾（三倍反弹）、尖刺壳盾（反伤）、钟面盾（宽判定冻结）、余烬圆盾（点燃）、鲸鳞塔盾（95% 减伤） |
| 技能（17） | 硫磺手雷、水银冰霜手雷、结晶闪电鱼叉；星落、雷击图腾、齿轮哨兵、捕兽夹、瘴气罐（毒雾）、集束钟弹、磁石雷、冰霜新星、余烬冲刺、时停怀表（全屏减速）、狂怒之血、疗愈提灯、弹跳锯轮、深渊墨瓶（黑洞） |
| 护符（4） | 余烬护符、潮汐护符、骨环护符、星芒护符（只带词缀：最大生命、全伤害、金币、可回复生命、移速、血瓶回复） |
| 消耗 | 生命血瓶、力量卷轴（三色二选一） |

状态效果：燃烧、冰冻、感电、中毒（可叠加）、减速、流血（可叠加）、浇油（遇火爆燃）、定身。

### 敌人

溺亡囚徒、钟针哨兵、兰灯僧侣（倒唱经文，把你的投射物反弹回来）、鳗舌渔民（闪电鱼叉、扑跳）、腐蚀害虫（自爆）、薄翼蜱虫（俯冲）、苔藓贫民、歌唱方尖碑（音波炮台），还有精英变体。三个 Boss：

- **皇家守卫**：重劈，带向两侧扩散的冲击波；横扫；半血以下连招。
- **时间守护者**：三个阶段，包括铲击、星光抛射、地面星光柱、召唤蜱虫，以及「倒流六十秒」。倒流会给自己回血、把你拉回 3 秒前的位置，读条时打出足够伤害就能打断。
- **收藏家**（真结局，观星台）：悬浮作战，细胞弹幕、突进、星光雨；第二阶段召唤小怪；第三阶段把你吸过去吸取生命，读条时打出足够伤害可以打断。

每个区域还有一个带符文的**符文守卫**（精英，生命更高、带符文颜色光环），击败后掉落符文石。

### 预计时长

一次成功通关约 1.5–2 小时：5 个区域、约 100 个房间、2 个 Boss，按每个房间 1 分钟左右估算。普通难度下，第一次通关通常要先失败几局，靠收藏家的永久成长和图纸解锁变强，所以首次通关总时长约 4–6 小时，设计目标是 5 小时。这是按关卡规模和战斗数值推算的，没有经过真人试玩校准。参考数据：不会闪避的测试机器人在普通难度下通过了第一个区域，在第二个区域中途死亡。

## 目录

| 路径 | 内容 |
|---|---|
| `Tools/Blender/` | 资产生成脚本：角色 `build_beheaded.py`、`build_zombie.py`、`build_enemies.py`（哨兵、僧侣、渔民、两个 Boss、生物），武器 `build_weapons.py`、`build_arsenal.py`、`build_armory.py`、`armory_melee.py` / `armory_ranged.py` / `armory_other.py`（60 件扩展，公共部分在 `armory_kit.py`，可在打开的 Blender 里 `preview()` 实时预览），图标 `render_icons.py`，道具 `build_props.py`，0.6 的 NPC / 护符 / 符文 / 方块 / 藤蔓 `sanctum_props.py`（两个套件 Sanctum、Relics，同样可 `preview()`），环境 `build_environment.py`、`build_biome.py`（四个区域套件） |
| `Tools/PIPELINE.md`、`Tools/BIOMES.md` | Blender → Unity 资产约定、区域套件约定 |
| `Tools/Audio/` | 音频合成：`dsp.py` 信号处理，`sfx.py` 音效配方，`music.py` 作曲与环境声，`make_audio.py` 生成 WAV 和清单（用 Blender 自带的 Python 运行，它带 numpy） |
| `Tools/Rooms/` | 房间模板（`make_rooms.py` 按坐标定义）和两个校验器：单房间（含镜像）可达性 `validate_rooms.py`，整关可达性 `validate_levels.py` |
| `Assets/_Project/Art/` | 导出的 FBX 与烘焙贴图 |
| `Assets/_Project/Resources/` | 房间模板、中英文字符串表、物品库、世界预制体表 |
| `Assets/_Project/Scripts/Runtime/` | `Player/` 移动与战斗、`Enemies/` 敌人与 Boss、`Items/` 物品与投射物、`Run/` 关卡生成与流程、`Meta/` 存档 / 成就 / 难度 / 作弊 / 本地化、`UI/` 菜单与 HUD |
| `Assets/_Project/Scripts/Editor/` | 一键配置项目，生成材质 / 预制体 / 物品 / 区域 / 场景，打包 |

## 重建

1. Blender 资产（headless，每个脚本几分钟到十几分钟）：

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P Tools/Blender/build_biome.py -- --biome all
```

其它脚本同理（`build_arsenal.py`、`build_props.py` 加 `-- --res=640`；敌人见 `build_enemies.py` 里的 `build(name)`）。0.6 的套件分两次烘焙：`sanctum_props.py -- --kit=Sanctum` 和 `-- --kit=Relics`，然后 `render_icons.py -- --kits=Relics` 渲染护符和符文图标。

2. 改了房间以后，先跑两个校验：

```bash
python3 Tools/Rooms/make_rooms.py && python3 Tools/Rooms/validate_rooms.py
```

```bash
~/.unity/bin/unity run . --no-tail -l Logs/dump.log -- -executeMethod DeadCells.EditorTools.DCBatch.DumpLevels && python3 Tools/Rooms/validate_levels.py
```

3. 音频（约 30 秒）：

```bash
/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13 Tools/Audio/make_audio.py
```

4. 配置 Unity、生成内容和场景、打包 macOS 版，并跑一遍自动验证：

```bash
zsh Tools/build_and_capture.sh check --seconds 120 -- -autoplayMenu -autoplayGod -autoplaySkip 20
```

截图和日志在 `Captures/check/`。

## 报告问题的位置

在设置或暂停菜单里打开「显示坐标」。右上角会显示 X / Y 格子坐标、所在房间模板和关卡种子；打开地图后，鼠标悬停在任意位置也能读出坐标。按 F8 会复制一行位置信息，例如：

```
v0.6 | Promenade | seed 15838 | X 40 Y 20 | room cmb_hall_a~m (combat) @40,11
```

开发端用同样的种子把这一关原样重建，并在 `Tools/_out/levels/one.txt` 里用 `@` 标出该位置：

```bash
~/.unity/bin/unity run . --no-tail -l Logs/dump.log -- -executeMethod DeadCells.EditorTools.DCBatch.DumpOne -dcArea Promenade -dcSeed 15838 -dcX 40 -dcY 20
```

## 自动验证参数

`-autoplay` 会启动一个跨场景的测试机器人，按地形图寻路、战斗、喝血瓶、走出口。常用参数：

| 参数 | 作用 |
|---|---|
| `-autoplaySeconds N`、`-captureInterval N` | 运行时长、截图间隔 |
| `-autoplayMenu` | 先截主菜单各页面 |
| `-autoplayBiome N`、`-autoplayDifficulty easy\|normal\|hard` | 从第 N 个区域开始、难度 |
| `-autoplayGod`、`-autoplaySkip N` | 无敌、每 N 秒跳到下一区域（巡视全部区域与结局） |
| `-autoplayWarpBoss` | 直接传送到 Boss 场地 |
| `-autoplayUiTour`、`-autoplayDie` | 依次打开暂停、地图、收藏家、传送、商店购买、石板并截图；最后测试死亡画面 |
| `-autoplayLang en\|zh`、`-autoplayNoVsync` | 语言、关闭垂直同步（测真实帧率） |
| `-autoplayDieAfter N`、`-autoplayRetry`、`-autoplayPrologue` | 第 N 秒强制死亡、死亡画面选「重试」、允许播放序章（测试重开流程） |
| `-autoplayShaftTest` | 每个区域把角色放到竖井底部，只靠跳跃爬出，记录成败 |
| `-autoplayJumpTest`、`-autoplayArmory` | 在通道里测单跳 / 二段跳高度；逐把挥舞所有武器并拉近截图 |
| `-autoplayBreakPost` | 故意清空后处理配置，验证运行时自动重建 |
| `-autoplaySystems` | 在通道里依次验证 0.6 系统：卷轴、变异、铁匠、传说装备卡、护符、背包、可回复生命、限时门、诅咒宝箱、藤蔓、墙跳、分支路线、裂墙、公羊地板 |
| `-autoplayMode daily\|rush\|custom`、`-autoplayBossCells N`、`-autoplayAssist` | 以指定模式 / Boss 细胞等级 / 辅助模式开局 |
| `-autoplayClearRunes` | 清空符文，用来检查符文守卫是否生成 |

测试机器人使用单独的存档 `save_autoplay.json` 并静音运行，不会改动玩家自己的 `save.json`。日志 `autoplay_log.txt` 记录每个区域的房间数和敌人数、报错计数、平均帧率、最差帧、CPU/GPU 帧时间。
