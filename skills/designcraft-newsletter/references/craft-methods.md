# 本场景的 Craft 方法与参数

先读取输入与当前选择。数值、路径、名称和对象编号仅为格式示例；用当前输入、实际返回ID和目标尺寸替换后执行。

| 顺序与目的 | 实际方法 | 参数例子 |
| --- | --- | --- |
| 1. 新建多栏文字框 | `frame.create` | `{"rect":[36,36,559,780],"content":"text","text":"本期简报正文"}` |
| 2. 设定三栏与栏间距 | `object.textFrameOptions` | `{"columns":3,"gutter":12,"balanceColumns":true}` |
| 3. 查看当前故事溢出 | `story.get` | `{}` |
| 4. 检查交付问题 | `preflight.run` | `{"minPpi":150}` |

## 如何调用

宿主内已打开编辑器时使用该同会话MCP；先等待editor_status就绪，读取实际工具schema和当前命令参数。独立CLI可用于文件任务，但新进程与已打开Web编辑器不是同一状态。

本插件MCP包装：`execute`，参数 `{"command": "frame.create", "params": {"rect": [36, 36, 559, 780], "content": "text", "text": "本期简报正文"}}`。后续行保持同一会话和对象选择，逐条检查实际结果。

CLI 语法（下面是展示用写法，实际跨平台执行用argv避免shell引号差异）：

designcraft-cli script steps.txt --in input.designcraft --save output.designcraft；steps.txt 每行：frame.create {"rect":[36,36,300,180],"content":"text","text":"标题"}。后续对象引用使用真实返回值或当前版脚本引用语法。

## 参数核对与完成标准

先查 [当前版本观察目录](craft-command-evidence.json) 中对应方法的完整参数，再按实际运行时查询更新。结构化步骤见 [craft-steps.json](craft-steps.json)。

核对续文顺序、跨栏标题、末栏空白和文章完整性。

边界：长文通过 text.thread 串联真实框ID，不按视觉位置猜测阅读顺序。

保存可编辑工程后由新进程或重新打开的同一宿主会话核对；导出格式单独解码/查看。方法存在和零退出不代表本场景已经完成。

工作流来源与许可见 [workflow-sources.json](workflow-sources.json)。仅借鉴事实与方法，本文与参数例子原创编写。
