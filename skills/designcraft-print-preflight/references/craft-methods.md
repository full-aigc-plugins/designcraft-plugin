# 印前检查：先盘点，按问题修复，再导出

输入包括现有原生工程、印厂确认的尺寸/出血/有效PPI/格式要求，以及获准使用的替换素材。先复制工作工程到新输出，原输入与素材只读；没有清晰原图时不能通过插值放大文件冒充真实细节。

## 盘点

在原工程上调用 `document.inspect {}`、`preflight.run {"minPpi":300}`、`links.list {}`、`font.list {}`。记录所有issue的kind、severity、item和page，将图片使用框关联到实际asset ID；不要只看错误数量，更不能忽略lowResolution警告。300是本示例阈值，依据实际交付约定确定。

当前后端能检查overset、missingLink、lowResolution以及字体/字形等问题；没有自动证明出血、专色、套印、ICC或透明度符合印厂要求。非目标对象、页数、原框边界、正文和字号先记录，供修复后比较。

## 有依据的修复

1. 低PPI：核对内容一致且具有足够真实细节的替换文件，`links.relink {"asset":实际assetID,"path":"确认后的替换文件"}`。此操作影响该asset的全部使用实例，先查uses，不只看当前页。预检阈值保持不变，不能降阈值伪造修复。
2. 缺链：用原始交付表/素材来源确认文件，按缺失asset ID显式relink，防止同名图片错配。找不到原素材时保留缺口并停止正式导出，不静默使用预览缓存。
3. 文字溢出：`story.get {"frame":实际文字框ID}` 记录全文，确认扩框不与邻近对象、页脚或安全边界冲突后，`transform.resize {"ids":[框ID],"from":[原边界],"to":[获准新边界],"content":false}`。只改变框，不缩字号、不删除文字；空间不足时另行续页。
4. 出血：印厂确认后 `layout.documentSetup {"bleed":9}`，9点只是示例；不顺带改页面大小或自动调整所有对象。设置出血不等于所有背景已延伸到出血边界，有满版对象时另查其实际范围。
5. 字体、字形与其他错误：先确认可用字体及替换授权，按真实命令处理，不能将其纳入本示例已自动修复的保证。检查所有警告并说明未解决内容。
6. 用相同 `minPpi` 再次 `preflight.run`，核对完整正文、字号、链接与非目标对象。`story.get.overset` 为null才没有溢出，0也是溢出。仍有error，或目标missingLink/lowResolution/overset尚未解决时，停止导出阶段。

## 导出与交付

检查复检报告后，单独调用 `file.exportPdf {"path":"preflight-proof.pdf","bleed":true,"marks":false,"standard":"none"}`，读取返回warnings。这里明确输出普通PDF校样，不声称PDF/X。检查真实页数、TrimBox、BleedBox、MediaBox及图文；9点四边出血示例应保留595×842点裁切尺寸，不能仅检查文件头。

`file.package {"dir":"print-package","idml":true,"pdf":false}` 保留可返工工程及素材。此处不额外生成参数不明确的包内PDF，印刷校样使用前一步显式导出的文件。阅读字体许可/打包报告，重新打开原生工程确认全文、链接及未改对象，逐页看实际内容。没有外部合规检查和印厂确认，不能将零错误预检当成印刷认证。

## CLI / MCP 分段执行

[结构化配方](craft-steps.json) 使用 `$input` 命名输入；由Agent从盘点结果和获准修复计划填写，例如 `lowResolutionAsset`、`missingAsset`、`oversetFrame`、原/新边界和出血。ID不能使用示例中的固定数字，路径不能是开发者机器地址。不适用的修复行删掉或改成对应真实问题的步骤，不能强行修复不存在的问题。

本技能自带 [引用编译器](../scripts/write_script.py)，只替换输入和返回引用，强制显式选择阶段；不执行预检业务，也不替Agent评估结果。以技能目录为基准用argv运行（Windows可能用python）：

```text
python3 scripts/write_script.py --recipes references/craft-steps.json --scene print-preflight --phase inspect --output inspect.json
designcraft-cli script inspect.json --in original.designcraft
python3 scripts/write_script.py --recipes references/craft-steps.json --scene print-preflight --phase repair --inputs approved-bindings.json --output repair.json
designcraft-cli script repair.json --in original.designcraft --save fixed.designcraft
```

**读取并确认复检报告后**，才编译 `--phase export`，对 `fixed.designcraft` 执行。编译器不会解释`stopIf`或代替人工/Agent接受警告，禁止把三段串成不检查返回结果的一键命令。所有输出用新路径。

宿主内操作走同会话MCP，等待 `editor_status` 并读取schema，再通过 `execute` 分段调用命令；实际ID由返回值填写。独立CLI不自动控制Web编辑器。

## 来源和边界

[GitHub来源](workflow-sources.json) 固定le-tex文档格式盘点脚本及哈希，只借鉴盘点和规则核对的事实，不移植脚本、条件隐藏、网络或安装行为。修复映射依据[当前命令目录](craft-command-evidence.json)和原生测试；当前示例不保证任意字体、色彩空间、专色、透明度、PDF/X或真实生产物料质量。
