# DesignCraft main排版交付补充

固定main `fc36957fe05f38a6976df4734d52b9250cd54a2c`的原生目录观察为519条，相对稳定版CLI459条新增60条、119处契约变化，完整参数见[main目录差异](main-command-delta.json)。这是相对稳定版CLI的差异，不表示旧增强内嵌引擎缺少全部60条；执行前以当前会话`list_commands`为准。SVG→原生版式→可编辑PPTX已通过Windows main专项39008681404：几何、活文字、填色、保存重开与PDF输出检查通过；Flex流程仍待执行。不计入原有8条手册通过数。

## 品牌SVG进入版式并交付可编辑PPTX

适用：把VectorCraft、Figma等导出的图标、标志或小型插图放进报告/页面，再交付可以继续编辑的演示文稿。先确认SVG尺寸、字体与外部资源；不得把转轮廓的文字称为活文字。

1. 检查当前文档页面尺寸与坐标；下面示例从`file.new {"width":360,"height":240,"facingPages":false}`开始。已有文档不得照抄新建步骤。
2. `edit.pasteSvg {"svg":"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"120\" height=\"60\"><rect width=\"50\" height=\"60\" fill=\"#2563eb\"/><ellipse cx=\"90\" cy=\"30\" rx=\"25\" ry=\"25\" fill=\"#16a34a\"/></svg>","at":[180,100]}`。`at`是艺术品中心的跨页坐标，不是左上角；保留返回的真实`ids`及`warnings`。路径、填充、描边和分组有原生映射，SVG文字按当前契约成为轮廓。
3. 需要可编辑标题时另建文本框：`frame.create {"rect":[24,180,336,220],"content":"text","text":"MAIN EDITABLE TITLE"}`，并记录返回的frame/story标识。
4. 先用`file.saveAs {"path":"output/layout.designcraft"}`或宿主`save_document`保存源工程；重开，`story.get {"frame":实际ID}`核对标题和溢出。
5. `file.exportPptx {"path":"output/editable.pptx","rasterize":false,"embedFonts":false}`导出。页码`pages`从1开始；`lineBreaks:keep`保留当前断行，`reflow`允许PowerPoint重新排版。
6. 核对返回slides/warnings、原生PPTX图形与文本框、填充颜色和实际打开效果。简单SVG例子不应变成整页图片；字体可用性、复杂混合效果与外部PowerPoint渲染另验。

`rasterize`默认true，无法原生表达的PDF/EPS、路径文字及部分效果可以变成300ppi图片；必须保留警告，不能笼统宣称无损。嵌字体默认true也只嵌许可允许的TrueType字体。WASM当前命令若以`base64`返回字节，应交由宿主保存，不能假定浏览器有本地文件系统。导出路径遵守宿主当前工作区和新文件规则。

独立CLI使用同一组JSON步骤：`designcraft-cli script steps.json --save output/layout.designcraft`；宿主内嵌编辑用当前MCP `execute {"command":"…","params":{…}}`逐条执行。另启CLI不会自动修改当前页面。

## 卡片/图文模块的Flex自适应布局

用途：横排卡片、按钮组或需要重排的图文模块。先用`document.inspect`取得本次任务对象ID；只处理同一跨页顶层对象，不把整篇用户文档全选送进容器。

1. `flex.add {"ids":[实际卡片1ID,实际卡片2ID]}`，记录返回容器`id`；单个组或空矩形改用`flex.convert`的语义。
2. `flex.set {"ids":[实际容器ID],"direction":"row","wrap":true,"width":320,"height":"auto","padding":[12,12,12,12],"gapH":12,"gapV":8,"justify":"flexStart","align":"start"}`。padding顺序为上、左、下、右；尺寸使用文档单位的数值，不传CSS字符串。
3. `flex.reorder {"id":实际子对象ID,"to":0}`改变其在容器中的顺序；这里的id是子对象，不能用容器替代。
4. `document.inspect`检查对象归属、尺寸、排列与故事溢出，再保存重开；真实页面需要窄尺寸试排和视觉检查。
5. 取消自适应用`flex.remove {"ids":[实际容器ID]}`，其子对象保留，可能形成组；不得当作删除图文内容。

Flex流程当前只核对了固定main的真实参数契约，尚未执行本流程的版面往返，不能标为实测通过。其余如`style.load`需先`style.load.list`检查同名冲突；默认redefine会替换定义，已有品牌样式优先明确选择useExisting或autoRename。新增方法索引不代表它们均完成场景验收。
