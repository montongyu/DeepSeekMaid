# 指定原画的攻击动作工作区

当前已完成并接入的版本是 **0.8.2**，预览位于上级目录的 `reference_attack-v0.8.2.gif`（50fps）和同名 `.png`（60fps APNG）。本目录以下内容是早期原画对照和八姿势节奏稿的历史记录，不是当前运行动画。

用户最新要求：攻击动作与提供的三幅原画一致。0.8.1 的站立原画骨骼变形方案未达到这个要求，不能将它视为已经还原。

本目录与 `dist/DeepSeekMaid` 分开，尚未替换游戏运行素材。原图为 `assets/concept/attack-right-v0.8-review.png`，与用户本次附件的 RGB 像素完全一致。

原画分隔线不等距，正确裁切范围为 x=[0,722)、[727,1523)、[1528,2172)，高度均为 724。`key-1.png`、`key-2.png`、`key-3.png` 保留原画人物像素，只在画布外侧补足宽度便于动画对齐。

自动几何变形和光流试验在手臂、裙摆、鞋部出现重影或变形，已拒绝作为成品。这些结果只是诊断图。

补绘中间帧使用内置 image_gen，提示词保存在 `assets/concept/attack-exact-inbetweens-prompt.txt`。补绘会产生新的图像细节，不能宣称与原图逐像素一致；三张原画始终作为姿势对照。

没有修改安装目录，也没有将预览写入发布包。

当前可看的文件为 `attack-painted-animatic.gif`，以及无 GIF 调色板量化的 APNG `attack-painted-animatic.png`。这是 8 幅姿势的节奏稿（原图 3 幅、补绘 5 幅），不是 50/60 张独立绘制的流畅成品。原图关键姿势 PNG 的逐像素误差为 0；补绘细节、站位与原图存在差异，不能宣称整段已经一模一样。生成的九格原稿位于 `assets/concept/attack-painted-inbetweens-v0.8.2.png`。
