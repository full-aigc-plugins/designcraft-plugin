# 两页三栏刊物：实际方法与参数

输入包括刊物尺寸、完整稿件、标题、目标页数、可用字体和输出路径。示例采用595×842点、两页、三栏、12点栏距，正文11点；这些是可调整的起点，不是任意稿件都适用的版式。读取 [结构化步骤](craft-steps.json)，不要照抄示例正文。

## 执行顺序

1. 新文档调用 `file.new {"width":595,"height":842,"pages":2,"facingPages":false,"margins":36,"bleed":0}`。已有工程先 `document.inspect {}`，跳过新建并确认目标页存在；示例首框/续框的spread为0/1，不能直接套在未知工程中。
2. `frame.create` 创建标题及首个正文框。保存每次返回的 `id`、`story`。正文仅放入首框；第二页续框 `text:""`，否则串接时会追加文字。
3. `object.textFrameOptions` 用 `ids:[首框id]` 设置 `columns:3,gutter:12,inset:0,autoSize:"off",balanceColumns:false`。不能依赖当前选中的对象。第一页示例正文框 `[42,130,553,310]` 特意较短，使测试稿产生续文；正式版按实际信息层级调整。
4. `style.paragraph.create {"name":"Newsletter Body","chars":{"fontFamily":"Source Sans 3","size":11}}`。先用 `font.list` 核对字体；已有同名样式须检查后决定复用或改名，不覆盖用户样式。
5. `text.select {"story":正文story,"anchor":0,"focus":稿件UTF8字节数}`，接着 `style.paragraph.apply {"name":"Newsletter Body","clearOverrides":true}`。后者清除所选正文的局部覆盖；已有混合格式稿件应保留有意的强调，改用合适范围与覆盖策略。字号不是仅创建样式就生效。
6. `story.get {"frame":首框id}` 查看全文与 `overset`。正文更短时可能不用续页；正文更长时必须扩容，不强行压到不可读字号。
7. 第二页用 `frame.create {"spread":1,"rect":[42,42,553,780],"content":"text","text":""}` 创建续框，按返回ID设置三栏、12点栏距、`balanceColumns:true`。调用 `text.thread {"from":首框id,"to":续框id}`，不能按视觉坐标猜阅读顺序。
8. `story.get {"frame":首框id}` 核对故事包含两个框且顺序相同，全文逐字等于输入，末段存在，最终 `overset:null`（当前CLI以null表示无溢出，有溢出时返回起始偏移；0也应视为溢出）。再运行 `document.inspect {}`、`preflight.run {"minPpi":150}`，处理错误并说明警告。
9. 保存新路径的原生工程，输出PDF校样与IDML；重新打开原生文件检查全文和框链，解包IDML确认段落样式仍应用。逐页看标题、续页起始和末栏空白，PDF成功不代表排版美观或印刷认证。

## CLI 与 MCP

同画面编辑走已打开编辑器的同会话 MCP：等待 `editor_status` 就绪，读取当前工具schema后，以 `execute {"command":"text.thread","params":{"from":真实首框ID,"to":真实续框ID}}` 逐步执行；每步读取返回值。独立CLI进程不会自动修改Web会话。

独立安装的本技能自带 [引用编译器](../scripts/write_script.py)，只把命名引用转换为原生 `$N.field`，不执行排版。以当前技能目录为基准，使用argv运行：

```text
python3 scripts/write_script.py --recipes references/craft-steps.json --scene newsletter --output steps.json
 designcraft-cli script steps.json --save newsletter.designcraft --export newsletter.pdf --export newsletter.idml
```

Windows 的Python命令可能是 `python`。输出文件须使用新路径。`--existing` 只跳过 `newDocumentOnly` 步骤并重算引用，不负责增加页面、合并同名样式或保护重叠布局；已有工程先检查再由Agent调整步骤，执行时显式加 `--in`。

`{"$ref":"body.id"}` 是配方的命名引用，不是MCP实际参数。实时MCP用返回ID替换；CLI经编译器转换后执行。替换任何正文后，重新计算 `len(text.encode('utf-8'))`；不能用中文字符数代替UTF-8字节数。

## 来源与边界

[工作流来源](workflow-sources.json) 固定GitHub提交和内容哈希。InDesign脚本提醒：改变框链可能影响故事和注释；本场景只原创适配显式续文、全文和顺序检查，没有复制脚本、自动拆链或承诺注释迁移。图片环绕、自动页码与脚注需另行确认真实命令和结果。

[命令目录](craft-command-evidence.json) 明确区分稳定版背景和main目录观察；方法可发现不等于本场景已运行通过。当前场景的真实回归状态以实际CI报告为准。
