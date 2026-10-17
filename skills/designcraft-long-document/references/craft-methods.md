# 长文档：章节、续文、目录与脚注

输入包括章节全文及顺序、标题层级、注释、目标页面尺寸、字体和交付格式。先检查现有工程的章节样式、页面与故事；不要用新文档步骤清空已有排版。示例是单文档两章，先四页，插入附录后五页，不是INDB多文件书籍转换器。

## 真实操作链

1. 仅新任务调用 `file.new {"width":595,"height":842,"pages":4,"facingPages":false,"margins":36}`。所有坐标单位为点，示例spread从0开始，`toc.generate.page`从1开始。已有工程先查询 `document.inspect`，重新绑定实际页面，跳过新建。
2. 用 `font.list` 确认可用字体，建立 `Book Body`、`Chapter Heading`、`Contents Title`、`Contents Entry` 和 `Book Note` 样式。`style.paragraph.create` 的 `chars` 示例为 `{"fontFamily":"Source Sans 3","size":11}`，章节标题20点、脚注10点。已存在同名样式须先检查再复用或改名，不覆盖用户样式。
3. `frame.create` 把第一章全文放入第二页（spread=1）首框，记录返回 `id`、`story`。先用 `text.select {"story":实际story,"anchor":0,"focus":全文UTF8字节数}` 选全文，`style.paragraph.apply {"name":"Book Body","clearOverrides":true}` 应用正文样式；再只选择首段标题的字节范围，应用 `Chapter Heading`。标题样式不能误施到全章，否则正文也会进入目录。
4. `story.get {"frame":首框ID}` 查询溢出。示例首框特意较短，第三页建立空白文字框并用 `text.thread {"from":首框ID,"to":续框ID}` 串接。正文仅输入一次。稿件增长时按实际页数和框链继续排版，不能删正文或盲目缩小字号消除溢出。
5. 第二章放在第四页，独立故事采用相同“先正文、再首段标题”的样式步骤；章节之间不误串同一故事。输入正文变更后重新计算UTF-8字节偏移，不用字符数代替。
6. 为示例来源注释调用 `footnote.options {"paraStyle":"Book Note"}`。在第二章结尾以 `text.select` 设置相同anchor/focus形成插入点，然后 `footnote.insert {"text":"实际来源注释"}`，记录返回story/id；用 `footnote.goToReference {}` 返回正文。已有工程的脚注选项是文档设置，先读原选项再决定是否调整，不全局替换已有注释规则。
7. `toc.generate {"entries":[{"style":"Chapter Heading","level":1,"entryStyle":"Contents Entry","pageNumber":"after","separator":"\t"}],"title":"Contents","titleStyle":"Contents Title","page":1,"rect":[42,42,553,600]}` 从真实标题生成目录。用 `toc.entries` 查询同一entries，示例应为第一章页2、第二章页4。目录条目样式明确设置 `para:{"tabs":[{"position":480,"align":"right","leader":"."}]}`，在当前511点宽框中将页码右对齐并显示点引导线；框宽变化后重新计算制表位，防止标题与数字挤在一起。目录文字仍可编辑，但页码不得靠猜测或手写长期维护。
8. 需要加入附录时，示例 `layout.pages.insert {"count":1,"after":2}` 在第三页后插一页（after为0基索引）；在新spread=3填入实际附录。第二章移到第五页，调用 `toc.update {}` 更新原目录，避免重复生成目录；再次 `toc.entries` 应为2/5。实际工程必须检查插入结果与返回文档，不照抄页码假设。
9. 保存新原生工程后重新打开，用明确框ID查询两章全文和框链，核对第一章没有断文/重复、第二章正文及脚注引用保持。当前 `story.get.overset` 无溢出为null，0也是溢出。原生脚注引用在故事字符串中为U+E00A占位，必须结合 `footnote.list {"story":实际第二章story}` 检查数量、文本和anchor，不能把占位符误删成普通文字。
10. `document.inspect` 和 `preflight.run {"minPpi":150}` 检查全部正文、目录及注释。保存原生工程，导出IDML/PDF；`file.package {"dir":"book-package","idml":true,"pdf":true}` 后读取report，字体可能自带或因许可不复制。解包IDML检查标题/正文/脚注样式及内容，逐页查看PDF中的续文、目录页码和脚注实际位置，导出成功不代替排版验收。

## CLI / MCP

[结构化配方](craft-steps.json) 含完整示例章节和参数。实时操作宿主编辑器时等待 `editor_status`，读取实际MCP schema，以 `execute` 顺序调用同会话命令，命名引用必须换成实际返回ID。独立CLI处理文件，不自动修改Web编辑器。

独立安装包含 [引用编译器](../scripts/write_script.py)，只转换引用，不执行排版。以技能目录为基准，使用argv运行：

```text
python3 scripts/write_script.py --recipes references/craft-steps.json --scene long-document --output steps.json
designcraft-cli script steps.json --save book.designcraft --export book.pdf --export book.idml
```

Windows的Python命令可能为 `python`。输出用新路径。已有工程先调整章节范围、页面、样式与插页位置，再以 `--existing` 编译、加 `--in` 执行；`--existing` 只跳过新建并重算引用，不自动合并已有内容。

## 来源和能力边界

[GitHub来源记录](workflow-sources.json) 固定提交、文件和哈希。参考InDesign的样式驱动目录、改版刷新及章节交付经验，步骤原创；不复制其正文或脚本。reason-machines仓库LICENSE仅写MIT标签，作为工作流事实参考，不复制许可条款不完整的素材。

本场景覆盖原生目录的实际页码、跨页正文与一条原生脚注；未承诺自动页脚页码、索引、任意外部脚注导入或INDB转换。复杂表格、图文混排与生产长文仍需专门检查。[命令目录](craft-command-evidence.json) 只是可发现方法证据，业务与视觉结果以实际回归、逐页检查为准。
