# 0.8.3 防御动画素材与实现

用户确认原画：`defense-right-v0.8.3-review.png`。全部新增栅格素材使用内置 image_gen，没有使用 API/CLI 回退。

| 素材 | 用途 |
| --- | --- |
| `assets/sprites/reference-guard-0-v0.8.3.png` | 原画左幅透明分离，只使用抬臂准备的衣袖和双手 |
| `assets/sprites/reference-guard-1-v0.8.3.png` | 原画中幅透明分离，只使用屈肘格挡的衣袖和双手 |
| `assets/sprites/reference-shield-v0.8.3.png` | 单独水盾和水花，展开、受力缩放、随掌移动、淡出 |

完整分离提示词：`defense-animation-v0.8.3-prompts.txt`。原始三段绘制提示词：`defense-reference-v0.8.3-prompt.txt`。

身体、脸、头发、裙摆、鲸尾、腿脚沿用 v0.8.2 的模型，避免动作切换时更换整个人物。新增手臂画面使用每张图统一缩放及肩部坐标锚定；没有分别拉伸手指、袖口或身体。`tools/reference_guard.py` 编写三个手臂视图的逆绑定、连续关节轨迹、脚底锚点和显示切换，源坐标轮廓在 `assets/animation/reference-guard-author.json`。前侧上臂/前臂使用同图的重叠 UV 表面并分别刚性绑定，手掌独立，避免跨越闭合肘部的大范围权重导致折叠。分离和补绘会改变部分细节。

主动作 1.15 秒，准备关键姿势位于 0.299 秒，格挡位于 0.529 秒，随后沿抬手准备姿势回收。五个防御路由共用这套绘制与关节设计，只调整时长和少量受力程度。游戏内由原生 Spine 4.2 根据渲染时间连续求值，不播放三帧/GIF。水盾由 C# Tween 驱动并跟随实时掌骨；软件预览采用同时间表近似，完整战斗中的触发、遮挡和 GPU/FPS 尚未验证。
