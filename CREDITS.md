# v0.8.6 待机发丝细化

沿用 v0.8.5 主图及所有原始 PNG，未新增或修改栅格美术。上层长发、下层卷发、发梢与头顶呆毛通过本工程编写的原生 Spine 分区权重、连续位移/旋转曲线及错相跟随细化；没有引入序列帧、光流图或第三方素材。源图和历次 image_gen 提示词记录仍见 assets/concept/common-state-v0.8.5-art.md。

# v0.8.5 同一默认原型与整套动作

用户指定的掌心向上原图原样保存在 offer-master-v0.8.5.png。遮挡补齐、眨眼、恼火与同人物趴地姿势使用内置 image_gen，未使用 API/CLI 回退。原可见脸、头发、衣裙与肢体尽量使用主图直接几何裁切；详细用途、提示词与实现见 `assets/concept/common-state-v0.8.5-art.md`。旧站姿整套纹理不再进入当前运行图集；未复制其他模组的图像、骨骼或运行库。

# v0.8.4 施法与聚能新增素材

两张新增手臂源姿势使用内置 image_gen，参考当前备战人物；未使用 API/CLI 回退。身体与脸继续使用 v0.8.2 模型。素材、提示词与连续关节实现见 `assets/concept/cast-channel-v0.8.4-art.md`。光纹为自制 Godot Line2D/Tween 几何特效，没有复制其他模组的图像、骨骼或运行库。

# v0.8.3 防御动画新增素材

防御动作原画与三张透明分离素材使用内置 image_gen；未使用 API/CLI 回退。身体沿用 v0.8.2 模型，只新增抬臂衣袖、手掌与水盾。素材、完整提示词和连续骨骼实现见 `assets/concept/defense-v0.8.3-art.md`。没有导入猎手模组的图片、骨骼或运行库。

# 素材与工具记录
- 0.8.2 指定攻击：内置 image_gen 从三阶段原画分离三个视图、补全无肢体身体层、制作水环和闭眼层；完整资产清单与提示词见 `assets/concept/attack-v0.8.2-art.md`。`tools/reference_palm.py` 自行编写连续关节、手掌分层、三视图绑定、裙摆遮挡与回弹；运行时不使用旧八姿势节奏稿或光流像素。透明分离和补绘会改变局部细节，不能宣称逐像素还原原画。

- 0.8.1 参考图推掌：根据用户指定的三阶段攻击图重做站距、屈膝、腰部移动、水平送掌与收手曲线。保留原立绘的可见双腿、袜带与鞋像素，只从内置 image_gen 生成的腿部补图取裙下遮挡处的上段；新增完整无腿裙身供分层遮挡使用。图片为 `assets/sprites/right-body-nolegs-v0.8.1.png`、`right-legs-v0.8.1.png`，准确提示词为 `assets/attack-legs-prompts-v0.8.1.txt`。未使用 CLI/API 回退。
- 0.8.1 绑定由 `tools/unified_rig.py` 自行编写：髋膝踝 IK、密集采样的 C1 曲线、前裙/后衬裙/双腿分层、蓄力专用衣袖权重。当前 25 骨骼、12 层、19 附件、50 动作/变体。水环由本工程 Line2D/Tween 绘制三条起伏轮廓和九个水滴；GIF 为原生混合姿态的软件渲染，水环为近似示意，非游戏截图。

- 0.8.0 用户确认的朝右人物、攻击关键姿势、同坐标透明完整立绘/无手臂底层、眨眼/恼火表情与趴地终态均使用内置 **image_gen** 工具绘制，未使用 CLI/API 回退。当前运行纹理为 `assets/sprites/right-*-v0.8.png`；完整原图与攻击设计稿在 `assets/concept/`，准确提示词在该目录的 `*v0.8-prompt.txt` 以及 `assets/right-animation-prompts-v0.8.txt`、`assets/right-face-prompts-v0.8.txt`。底层补画和抠图由 image_gen 完成；几何裁取手臂保持原图 UV，不擦改生成像素。
- 0.8.0 绑定由本工程 `tools/unified_rig.py` 编写：25 根骨骼、7 层、13 个附件、50 段曲线及变体；所有直立部件共用原图坐标和同一缩放。手部保持原图张掌；早期不协调的独立头身/拳头素材未用于当前运行包。水纹、怒筋与蒸汽由 Godot Line2D/Tween 绘制。动作 GIF 为原生姿态采样的软件渲染，非游戏截图。
- 0.8.0 其余 96 项卡面重新配色，使用内置 image_gen 绘制 `assets/cards/cards-00-v0.8.png` 至 `cards-04-v0.8.png`，准确提示词见 `assets/prompts-v0.8.txt`，颜色计划为 `assets/cards/palette-v0.8.json`。两张基础卡面保留 0.5 的暖色打击与绿色防御。

- 造型方向由用户选定：蓝发鲸鱼女仆版 DeepSeek 娘。
- 公开造型参考：[梗鲸 DeepSeek 娘图集](https://aigengtu.com/en/tag/deepseek-chan)，参考图为该图集的 `079.webp`。原始参考图片不随成品或源码压缩包分发。
- 角色设定、八姿态图集、五张卡面图集：本次使用内置 **image_gen** 生图工具制作；未使用 API/CLI 回退。生成提示词见 `assets/prompts.txt`。卡面图集前 98 格用于映射，最后两格不使用。
- 0.2.0 新版卡通元素球图集与独立选人立绘：内置 **image_gen** 工具生成，实际 PNG 保存在 `assets/effects/elemental-orbs.png` 和 `assets/ui/character-select.png`；完整提示词见 `assets/prompts-v0.2.txt`。
- 0.3.0 精修战斗姿态、八帧待机图集与深海观测馆背景：内置 **image_gen** 工具生成，保存在 `assets/sprites/deepseek-poses-v0.3.png`、`assets/sprites/deepseek-idle-v0.3.png` 与 `assets/ui/selection-background.png`；完整提示词见 `assets/prompts-v0.3.txt`。未使用 API/CLI 回退。
- 0.4.0 连续动画：本工程自行编写 14 根骨骼、加权网格与八段动画曲线，见 `tools/make_rig.py`、`assets/animation/maid.spine-json`；纹理使用已生成精修人物图集的第一格。旧待机轮换不再用于运行时。
- 0.5.0 动作扩充：本工程自行增加 14 段曲线及变体选择逻辑，仍使用同一人物纹理与自制网格。基础打击、基础防御两张独立卡面使用内置 image_gen 制作，保存于 `assets/cards/strike-defect-v0.5.png`、`assets/cards/defend-defect-v0.5.png`，完整提示词见 `assets/prompts-v0.5.txt`。未使用 API/CLI 回退。
- 0.6.0 手部动作：自行增加双侧肘部、手腕、指尖六根骨骼，重做局部权重与出手曲线，共 20 根骨骼、22 段动画。仅复用本工程人物纹理，没有新增生成式美术。软件动作检查图由自制网格和原生引擎姿态采样渲染，不是游戏截图。
- 0.7.0 分层重制：使用内置 **image_gen** 制作人物部件图集、独立裙摆、鲸尾、恼火表情和趴地终态五份透明 PNG，保存在 `assets/sprites/puppet-*-v0.7.png`。完整提示词见 `assets/prompts-v0.7.txt`，未使用 CLI/API 回退。图集使用矩形区域作为骨骼附件，不重绘或擦改生成像素。
- 0.7.0 原创绑定与动作：`tools/puppet_rig.py` 编写 21 根骨骼、14 个显示层、19 个附件和 50 段动画。手臂从图集中的独立衣袖区域设置上臂、前臂接缝，拳头/张掌及头部表情使用不同附件；长发、裙摆、鲸尾另有加权形变。怒筋和蒸汽由本工程 Godot Line2D/Tween 绘制。
- 技术对照：只读检查本机已安装的 LieRenTVmod（创意工坊 3787753911），确认其使用 Spine 4.2.43。该模组的图片、骨骼和关键帧未复制到本工程或压缩包。
- 本次额外在隔离工程中只读采样猎手动画，记录攻击约 0.567 秒、施法约 1.3 秒及手臂前段快速发力等节奏特征，作为原创动画的技术参考；检查脚本为 `tools/hunter_check.gd`。猎手为多层绑定，不能直接把它的骨骼幅度套到本工程的单图网格上。
- 原生加载与动画接口参考：[Spine Godot 官方文档](https://esotericsoftware.com/spine-godot)、[Spine 4.2 运行库源码](https://github.com/EsotericSoftware/spine-runtimes/tree/4.2/spine-godot)。模组调用游戏已安装的运行库，不分发 Spine 运行库代码、二进制或其示例素材。
- 光环、元素线条和数据流：本工程的 Godot 节点代码绘制；星光粒子使用新版透明图集。
- 游戏与游戏原素材属于 Mega Crit。压缩包不分发游戏 DLL、PCK、原插画或反编译代码。
- 编译器：[Microsoft.Net.Compilers.Toolset 4.14.0](https://www.nuget.org/packages/Microsoft.Net.Compilers.Toolset/4.14.0)，仅用于本地构建，不随成品分发。
- 接口检查工具：[ICSharpCode.Decompiler 9.1.0.7988](https://www.nuget.org/packages/ICSharpCode.Decompiler/9.1.0.7988)，仅用于本地检查，不随成品分发。
- 开发格式参考：[Slay the Spire 2 Modding Tutorial](https://github.com/fresh-milkshake/Modding-Tutorial)。具体补丁目标已针对本机 `v0.111.0` 程序集重新核对。

这些来源记录不表示参考图作者、DeepSeek 或 Mega Crit 对本模组作出官方背书。
