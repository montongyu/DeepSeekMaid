# 0.8.5 默认待机与整套动作统一

用户指定的原图原样复制到 `assets/sprites/offer-master-v0.8.5.png`。其余新增栅格素材使用内置 image_gen，未使用 API/CLI 回退；完整提示词见 `common-state-v0.8.5-prompts.txt`。

| 素材 | 实际用途 |
| --- | --- |
| `offer-master-v0.8.5.png` | 直接保留可见的脸、头发、衣裙、腿、尾巴和默认双手，作为统一原型 |
| `offer-body-v0.8.5.png` | 仅在原手臂、腿部几何遮挡区域下方补齐衣服，不替换可见整张脸/头发 |
| `offer-blink-v0.8.5.png` | 只取配准的脸部区域，用于眨眼和闭眼休息 |
| `offer-angry-v0.8.5.png` | 只取配准的脸部区域，用于受击后的坚定恼火表情 |
| `offer-prone-v0.8.5.png` | 同人物的趴地终态，头朝右、双手垫头、脚朝左 |

表内 PNG 位于 `assets/sprites/`。旧攻击、护盾和施法绘制角度仍作为局部手臂 UV 来源，身体、脸和腿不再切换为旧站姿人物。不是 50 套独立新绘，而是同一原型、连续关节路径及七个局部手臂绘制角度组成的 50 个动作和变体。

`tools/common_state.py` 统一所有动作，`assets/animation/common-state.json` 保存原型坐标、源绘制几何、关键姿势检查点和全部动作起止状态。上臂与前臂、腿与脚使用父子关节及 noScale 继承；本地旋转根据父级非均匀缩放求逆，使实际混合过程也保持关节连接。参数的官方格式参考 [Spine 4.2 JSON 读取实现](https://github.com/EsotericSoftware/spine-runtimes/blob/4.2/spine-csharp/src/SkeletonJson.cs)，没有复制或打包该运行库。

各绘制角度的手掌朝向单独标定并在关键姿势之间连续转腕，减少附件切换时的翻掌突变。每个身体部位在单个显示槽中选择附件，避免两张半透明人物或手臂重影。开局直接进入 `idle_loop`。普通动作首尾回到同一默认姿势；死亡以趴地结束，复起以趴地开始并回到默认待机。恼火待机播放一次之后自动恢复。GIF/APNG 为真实原生姿态的软件渲染，C# 特效触发、完整战斗遮挡和 GPU/FPS 尚未验证。
