---
name: designcraft-data-merge-badges
description: 当用户需要用DesignCraft从CSV批量生成可编辑胸牌、会议姓名卡或同版式单记录卡片时使用；逐条预览、修复长姓名溢出、验证缺字及保存重开后的完整字段，不把数据表截图当成排版。
license: Apache-2.0
---

# CSV批量胸牌

适合一个模板、每条记录一页的90×54毫米胸牌。原生坐标用点，毫米乘72/25.4。输入CSV要求唯一且区分大小写的Name、Role列，UTF-8或UTF-8 BOM；保留引号内逗号和完整文字，不覆盖CSV。其他列不进入胸牌。当前执行器支持1至200条单行字段，既有工程另用副本操作，不运行新图示例覆盖用户文档。

先读[实际方法](references/craft-methods.md)、[原始模板配方](references/craft-steps.json)、[当前命令证据](references/craft-command-evidence.json)和[GitHub来源](references/workflow-sources.json)。配方含固定合成数据，实际执行须换成用户授权数据。

1. 先审查字段、记录数、输出位置和印刷尺寸。复制字体进任务工程旁Document Fonts时保留许可证；本技能不安装系统字体。
2. 中文任务先用[字体来源](references/font-source.json)提供的固定摘要获取Noto字体。保存空白模板，再重开加载Document Fonts；之后创建字段。file.new会重置字体环境，不能加载字体后又新建文档。
3. data.source.select真正选择数据源；data.fields只列字段。Name/Role分别在空故事中插入data.placeholder.add，不能把NAME/ROLE示例文字留在字段后。
4. text.select使用UTF-8字节位置，不用字符数。data.preview的record从1开始；逐条story.get比对完整字段，document.inspect查溢出，preflight.run查缺字。
5. 姓名22pt溢出时重新预览18pt、14pt；不能再小，不能截断或自动改名。仍溢出、缺字或其他错误时停止，保留草稿让用户确认重新排版。
6. data.preview.stop恢复原字段，核对故事仍为占位符，再保存可编辑模板。data.merge生成新文档，核对实际records/pages、缺图及溢出；不能以模板预览当作完整合并结果。
7. 保存合并工程及PDF；新进程重开，逐页核对标题、姓名、角色全文和预检，生成每页PNG查看。默认不生成多合一拼版或裁切标记，正式印刷另核对交付规范。

## 可执行入口

英文且内置字体覆盖输入时：`python3 <本技能目录>/scripts/build_badges.py --cli <designcraft-cli> --csv <输入.csv> --output-dir <不存在的输出目录>`。

中文：先`python3 <本技能目录>/scripts/fetch_font.py --directory <任务字体目录>`，按返回的fontFile调用上述入口并加`--font-file <字体路径>`。获取失败则停止，不把缺字输出记为成功。也可传入有使用权的字体和`--font-family`，但仍须真实预检。字体与许可证仅放任务目录，不依赖技能兄弟目录或全局安装。

输出包括可编辑模板、合并工程、PDF、逐页PNG及检查结果；失败时可能留下草稿和诊断文件，不应交付为通过。命令用argv，stdout为ASCII转义JSON以保留Windows中文路径。

## 同画面MCP

交给 **designcraft-editor** 技能，独立安装：`npx skills add full-aigc-skills/designcraft-skills --skill designcraft-editor`。在同一会话读取execute/inspect_document/get_story等实际schema，逐步绑定真实返回值，再preview、stop、merge与保存；原生$N或手册$ref不能直接传给MCP。另开CLI修改文件不证明当前编辑器同步。原生字体加载也不自动证明Web运行时支持相同字体路径。当前内置Web运行时可用`LXGW WenKai`，经font.list和预检确认后，可在退出预览后用font.replace将示例字体替换为它，再逐条预览与合并；品牌指定字体不得静默替换。保存的Web工程若需CLI重开，按[Web字体记录](references/web-font-source.json)获取相同字体及许可证放入Document Fonts，不能以缺字或字体替代结果冒充一致。

本技能属于开发预发布场景；CLI、Windows和目标宿主的当前验证状态以配套记录为准。胸牌是版式内容，不是门禁认证或身份凭证。
