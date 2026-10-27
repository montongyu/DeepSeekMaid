# 0.8.4 施法和聚能素材

两张新增栅格素材使用内置 image_gen，未使用 API/CLI 回退。完整提示词为 `cast-channel-v0.8.4-prompts.txt`，均以 `assets/sprites/reference-palm-0-v0.8.2.png` 为人物参考。

| 素材 | 用途 |
| --- | --- |
| `assets/sprites/reference-spell-0-v0.8.4.png` | 双手捧能姿势；运行时仅取衣袖和手掌 |
| `assets/sprites/reference-spell-1-v0.8.4.png` | 掌心向上引导释放姿势；运行时仅取衣袖和手掌 |

身体、脸、头发、裙摆和腿脚继续使用当前备战人物。手臂在统一画布中以肩部锚定，不分别拉伸手指或身体；袖口和两段衣袖有 UV 重叠。几何裁切和关节逆变换由 `tools/reference_spell.py` 编写，源坐标轮廓见 `assets/animation/reference-spell-author.json`。原生 Spine 连续计算关节路径，绘制角度单独切换，手部视图不作整个人物透明交叉淡化。

11 个动作路由共用两套手臂绘制角度，通过前手抬高、双手释放、环绕、脉冲、过载和节奏调整形成变体，不是 11 套独立新绘动画。光纹和光点为 Godot Line2D/Tween 原生几何特效，没有使用脚本重画位图。GIF/APNG 的人物姿态是原生采样，光纹为同数学公式的软件近似；C# 实际战斗触发、遮挡与 GPU/FPS 尚未验收。
