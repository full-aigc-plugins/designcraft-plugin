# 从技能商店适配的场景方法

以下内容是基于已阅读技能的原创 Craft 指导。沿用现有配方的实际命令；这里补充任务判断和结果检查，不将同一配方再计为新增场景。商店提供发现入口，原技能使用的软件、服务和依赖不会随本插件安装。

示例步骤是参数模板，不能直接作为通用执行脚本。先取当前会话的文档、图层、片段或故事ID，解析所有引用，再按实际工具schema执行；尺寸、坐标、路径和文本按本次任务调整。已打开编辑器时使用同一个MCP会话；独立CLI文件编辑不能证明界面同步。

## 先规划阅读顺序再排页

参考：[suzheng/k2f/k2f-idml](https://github.com/suzheng/k2f/blob/d28f3672ccadf8b537ceca227bb503c9dd2ffba3/skills/expert/k2f-idml/SKILL.md)；[skillhub:indesign-script-for-claw](https://api.skillhub.cn/api/v1/download?slug=indesign-script-for-claw)。

先列读者、用途、必须原样保留的价格与声明，再分配两页角色：第一页重点价值，第二页规格与行动入口。标题、正文与说明各有明确层级，然后创建实际文本框。

原配方：`two-page-product-sheet`。输入与边界：2个非对页页面，每个spread独立坐标，示例技术参数需按实际产品核实。

| 顺序 | Craft 实际方法 | 参数模板 |
| --- | --- | --- |
| 1 | `file.new` | `{"width":595,"height":842,"pages":2,"facingPages":false,"margins":36,"bleed":0,"title":"双页产品说明"}` |
| 2 | `frame.create` | `{"spread":0,"rect":[42,48,553,110],"content":"text","text":"Craft Desk Lamp"}` |
| 3 | `text.select` | `{"story":{"$ref":"title1.story"},"anchor":0,"focus":15}` |
| 4 | `type.char` | `{"attrs":{"fontFamily":"Source Sans 3","size":28}}` |
| 5 | `frame.create` | `{"spread":0,"rect":[42,150,553,390],"content":"text","text":"Focused light for reading and making.\nMaterials: aluminium and recycled polymer.\nPower: 8 W. Colour temperature: 4000 K."}` |
| 6 | `text.select` | `{"story":{"$ref":"intro.story"},"anchor":0,"focus":120}` |
| 7 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":16}}` |
| 8 | `frame.create` | `{"spread":1,"rect":[42,48,553,110],"content":"text","text":"Setup and care"}` |
| 9 | `text.select` | `{"story":{"$ref":"title2.story"},"anchor":0,"focus":14}` |
| 10 | `type.char` | `{"attrs":{"fontFamily":"Source Sans 3","size":28}}` |
| 11 | `frame.create` | `{"spread":1,"rect":[42,150,553,420],"content":"text","text":"1. Place on a stable surface.\n2. Connect the approved power adapter.\n3. Keep the light source clear.\nDisconnect power before cleaning."}` |
| 12 | `text.select` | `{"story":{"$ref":"care.story"},"anchor":0,"focus":134}` |
| 13 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":16}}` |
| 14 | `document.inspect` | `{}` |
| 15 | `font.list` | `{}` |
| 16 | `preflight.run` | `{}` |

检查：两页各有清晰职责，关键事实完整，原生对象仍可编辑。

能力边界：不把K2F、InDesign JSX或漫画排版器直接装进Craft。

原配方结果检查：["两页标题分属不同spread", "规格与维护说明不丢失", "导出含2页"]

原配方限制：样例参数不是认证结果；正式说明须按产品实际安全资料审核。

## 长文按故事流排版

参考：[skillhub:adobe-indesign-2026](https://api.skillhub.cn/api/v1/download?slug=adobe-indesign-2026)；[sfkislev/flue/indesign](https://github.com/sfkislev/flue/blob/6c542fe2e490f47cd984abfc3b78e95021611fd2/skills/indesign/SKILL.md)。

先检查页、跨页、文本框与故事关系，再串接两栏；正文只写入所属故事，后续校对关注换栏位置与overset，不复制同一段到两栏凑版。

原配方：`threaded-newsletter`。输入与边界：两列文字框宽244、高300点，示例长文由同一故事流入两框。

| 顺序 | Craft 实际方法 | 参数模板 |
| --- | --- | --- |
| 1 | `file.new` | `{"width":595,"height":842,"pages":1,"facingPages":false,"margins":36,"bleed":0,"title":"双栏串接简报"}` |
| 2 | `frame.create` | `{"spread":0,"rect":[42,40,553,100],"content":"text","text":"Neighbourhood Notes"}` |
| 3 | `text.select` | `{"story":{"$ref":"title.story"},"anchor":0,"focus":19}` |
| 4 | `type.char` | `{"attrs":{"fontFamily":"Source Sans 3","size":28}}` |
| 5 | `frame.create` | `{"spread":0,"rect":[42,130,286,430],"content":"text","text":"Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step."}` |
| 6 | `text.select` | `{"story":{"$ref":"left.story"},"anchor":0,"focus":1749}` |
| 7 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":11}}` |
| 8 | `frame.create` | `{"spread":0,"rect":[309,130,553,430],"content":"text","text":""}` |
| 9 | `text.select` | `{"story":{"$ref":"right.story"},"anchor":0,"focus":0}` |
| 10 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":11}}` |
| 11 | `text.thread` | `{"from":{"$ref":"left.id"},"to":{"$ref":"right.id"}}` |
| 12 | `document.inspect` | `{}` |
| 13 | `font.list` | `{}` |
| 14 | `preflight.run` | `{}` |

检查：完整故事内容与输入一致，串接顺序正确且无溢出。

能力边界：不能把删除尾文当成修复溢出；frame与story ID以实际返回为准。

原配方结果检查：["两列共享同一故事且框顺序正确", "正文完整保留且不溢出", "不是把同样正文复制到两列"]

原配方限制：实际长文长度与字体会改变流动；重排后再查overset与阅读顺序，不把双栏外观当成已串接。

## 把印前发现转成待处理项

参考：[skillhub:adobe-indesign-2026](https://api.skillhub.cn/api/v1/download?slug=adobe-indesign-2026)；[ie3jp/illustrator-mcp-server/illustrator-preflight](https://github.com/ie3jp/illustrator-mcp-server/blob/57c5c101a5192c61535493f39b653e6f92b8eb29/plugins/ie3-design-bridge/skills/illustrator-preflight/SKILL.md)。

导出前检查文本、字体与RGB等预检问题；背景按实际出血延伸，导出后核对PDF的TrimBox与BleedBox及边缘内容。警告按用途解释，未检查项保留为未知。

原配方：`bleed-review-pdf`。输入与边界：A4页面、四边9点出血；约3.175mm，真实印厂若要求3mm应换算8.504点。

| 顺序 | Craft 实际方法 | 参数模板 |
| --- | --- | --- |
| 1 | `file.new` | `{"width":595,"height":842,"pages":1,"facingPages":false,"margins":36,"bleed":9,"title":"带出血的审阅PDF"}` |
| 2 | `frame.create` | `{"rect":[-9,-9,604,150],"content":"unassigned"}` |
| 3 | `object.color` | `{"ids":[{"$ref":"bar.id"}],"color":"#1d4ed8","target":"fill"}` |
| 4 | `object.stroke` | `{"ids":[{"$ref":"bar.id"}],"swatch":"[None]","weight":0}` |
| 5 | `frame.create` | `{"spread":0,"rect":[42,220,553,390],"content":"text","text":"A print-ready conversation starts here"}` |
| 6 | `text.select` | `{"story":{"$ref":"title.story"},"anchor":0,"focus":38}` |
| 7 | `type.char` | `{"attrs":{"fontFamily":"Source Sans 3","size":30}}` |
| 8 | `frame.create` | `{"spread":0,"rect":[42,450,553,570],"content":"text","text":"Confirm paper, colour profile, bleed and finishing with the printer."}` |
| 9 | `text.select` | `{"story":{"$ref":"note.story"},"anchor":0,"focus":68}` |
| 10 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":18}}` |
| 11 | `file.exportPdf` | `{"path":"bleed-review.pdf","bleed":true,"marks":{"crop":true,"bleed":true,"pageInfo":false},"standard":"none"}` |
| 12 | `document.inspect` | `{}` |
| 13 | `font.list` | `{}` |
| 14 | `preflight.run` | `{}` |

检查：出血量和裁切范围符合任务；缺字、RGB警告与未查项目可见。

能力边界：审阅PDF不等于CMYK或印厂认证；不能把另一工具的preflight_check当本插件接口。

原配方结果检查：["背景越过裁切边缘", "PDF包含出血审阅区域", "没有把RGB审阅稿说成已通过印厂色彩验收"]

原配方限制：这是技术审阅输出，不宣称PDF/X、CMYK、软打样或印厂已验收。固定输出名只用于新的空工作目录。

## 版本与执行

执行包装沿用本技能主文件。原生CLI脚本中的$N由原生引用解析器解释，MCP使用实际返回值。坐标和字号为点，rect为左右上下边界，story与frame编号不能混用。 保存到未占用路径并重开，按实际产物检查；本轮文档适配未新增宿主或真实媒体验收。

本技能内的[商店来源与参数记录](market-adaptations.json)记录版本、内容哈希和观察方法；没有分发第三方脚本或正文。
