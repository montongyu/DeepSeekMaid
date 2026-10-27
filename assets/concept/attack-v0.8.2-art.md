# 0.8.2 攻击美术与提示词

全部新增栅格素材使用内置 **image_gen**，没有使用 API/CLI 回退。角色来自用户指定的三阶段攻击原画 `attack-right-v0.8-review.png`。透明分离、补绘肩部及被遮挡衣服会带来局部图像差异；原画逐像素一致的三幅 PNG 仍保存在 `preview/exact-reference-attack/key-1.png` 至 `key-3.png`，它们不是游戏运行纹理。

| 当前运行素材（相对项目目录） | 用途 | 完整提示词 |
|---|---|---|
| `assets/sprites/reference-palm-0-v0.8.2.png` | 蓄力视图的手臂、手、腿 | `assets/concept/attack-cutouts-v0.8.2-prompts.txt`，POSE 1 |
| `assets/sprites/reference-palm-1-v0.8.2.png` | 推掌视图的手臂、手、腿 | 同上，POSE 2 |
| `assets/sprites/reference-palm-2-v0.8.2.png` | 收势视图的手臂、手、腿 | 同上，POSE 3 |
| `assets/sprites/reference-body-0-v0.8.2.png` | 蓄力身体，补全被肢体遮挡处 | `assets/concept/attack-layers-v0.8.2-prompts.txt`，BODY LAYERS |
| `assets/sprites/reference-body-1-v0.8.2.png` | 推掌身体，补全被肢体遮挡处 | 同上，BODY LAYERS |
| `assets/sprites/reference-body-2-v0.8.2.png` | 收势身体，补全被肢体遮挡处 | 同上，BODY LAYERS |
| `assets/sprites/reference-water-v0.8.2.png` | 掌前水环 | 同上，WATER EFFECT |
| `assets/sprites/reference-blink-v0.8.2.png` | 常规待机眨眼，仅使用脸部区域 | `assets/concept/attack-blink-v0.8.2-prompt.txt` |

`tools/reference_palm.py` 编写 UV 裁切、统一画布配准、源视图的关节逆变换、连续关节曲线及三个绘制视角的切换。手掌另作刚性表面，袖口被遮挡的小区域使用同张衣袖纹理的 UV 补片；没有用脚本重画位图。前裙摆和后衬裙沿同一轮廓分层。运行时使用游戏自带的原生 Spine 4.2，不播放 GIF 或八帧节奏稿，不使用光流生成的变形像素。

`attack-painted-inbetweens-v0.8.2.png` 和它的九格提示词是早期节奏稿记录，不在当前运行图集中使用。
