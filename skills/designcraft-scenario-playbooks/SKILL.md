---
name: designcraft-scenario-playbooks
description: 用 DesignCraft 排版活动海报、串接简报、双页说明、活表格、品牌文案修订、溢出修复、出血审阅稿和交互阅读链接时使用，提供逐步 CLI/MCP 方法、参数及实际输出检查。
license: Apache-2.0
---

# DesignCraft 排版场景

从[8条具体流程](references/workflows.md)选任务，[recipes.json](references/recipes.json)提供有序参数，[命令证据](references/command-evidence.json)与[GitHub来源](references/sources.json)分别记录实际方法和工作流参考。文案、页面及示例数据是原创演示，不执行InDesign JSX。

## 先确认单位和范围

先运行`designcraft-cli --version`及`commands`；CLI不随本技能安装，缺失时按[官方发行说明](https://github.com/storytold/designcraft/releases)选择系统版本并遵守安装授权。本文原生0.8命令与插件Web桥可能不同，实际宿主先读schema。用font.list检查本次使用字体；本例采用运行时自带的Source Serif 4 / Source Sans 3，不默认要求系统安装商业字体。

坐标、字号、出血均为点，1毫米=72/25.4点。rect=[左,上,右,下]，不是[x,y,宽,高]。frame.create.spread从0，图中位置是跨页坐标；file.exportPdf.pages按1开始的页面位置，不能混用。text.select.anchor/focus是UTF-8字节，不能把中文字符数直接当偏移。

## 同会话MCP与独立CLI

编辑器就绪后用同一个MCP服务的execute逐步调用，具体封装以tools/list为准。先创建文本框，保存真实返回的id/story，再传给后续方法；inspect_document、get_story和render_page核对结构与页面。独立CLI文件操作不能证明内嵌编辑器同步。

手册capture为返回值命名，`{"$ref":"title.story"}`必须绑定实际值，不能原样发给CLI/MCP。CLI原生支持`$N.story`等引用，可用[编译脚本](scripts/write_script.py)生成：`python write_script.py --recipes recipes.json --scene event-poster --output steps.json`，两个输入路径换成本技能实际路径。随后`designcraft-cli script steps.json --save new.designcraft --export review.pdf --export exchange.idml`。编译脚本只重排引用，不执行排版；所有业务仍由原生CLI完成。

已有文档编译加`--existing`再用`script steps.json --in input.designcraft --save new.designcraft`。该模式跳过newDocumentOnly并重排引用，仍须先调整本次位置、页数、故事和样式冲突；不能把完整新文档示例原样塞入已有版面。不要手工只删file.new而保留旧$N编号。MCP直接使用实际返回值；只有CLI脚本的引用解析器会解释$N。

## 结果与交付

每次输出采用未占用的新路径；原生CLI不会替你防止覆盖。保留可编辑.designcraft和需要的IDML、PDF。重开查询document.inspect、story.get、table.get；检查预检issues，不靠退出码或文件头宣称完整交付。溢出修复先证明确有overset，再检查修复后消失且内容未删；字体、行距、图片和分页变化后重新检查。

模板中的assertions只适用于示例输入。逐页查看实际PDF，核对阅读顺序、数据、换行和对象覆盖。出血与PDF导出成功不代表CMYK、PDF/X、印厂或无障碍验收。交互PDF含注释也不代表目标网站可用，示例URL必须替换。

## 技能商店场景经验

遇到先规划阅读顺序再排页、长文按故事流排版、把印前发现转成待处理项时，读取[商店工作流适配](references/market-workflows.md)，使用对应的Craft方法和实际结果检查。上游技能不作为运行依赖。
