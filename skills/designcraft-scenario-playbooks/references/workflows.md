# DesignCraft 排版场景

坐标与字号为点，rect=[x0,y0,x1,y1]不是宽高。示例为独立新文档；capture/$ref须先绑定或编译。

## event-poster：A4活动海报

输入：A4单页，标题、主题、时间地点与报名提示；示例日期地点需替换。

| 顺序与目的 | 方法 | 参数与返回绑定 |
| --- | --- | --- |
| 1. 仅新图建立指定页面，不用于已有文档 | `file.new` | `{"width":595,"height":842,"pages":1,"facingPages":false,"margins":36,"bleed":0,"title":"A4活动海报"}` |
| 2. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,70,553,160],"content":"text","text":"Community Design Day"}`；返回记为`title` |
| 3. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"title.story"},"anchor":0,"focus":20}` |
| 4. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Sans 3","size":38}}` |
| 5. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,180,553,240],"content":"text","text":"Make useful things, together."}`；返回记为`subtitle` |
| 6. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"subtitle.story"},"anchor":0,"focus":29}` |
| 7. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":20}}` |
| 8. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,330,553,470],"content":"text","text":"18 October 2026\n10:00 - 17:00\nStudio Hall"}`；返回记为`details` |
| 9. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"details.story"},"anchor":0,"focus":41}` |
| 10. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":22}}` |
| 11. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,690,553,760],"content":"text","text":"Register before attending. Capacity is limited."}`；返回记为`footer` |
| 12. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"footer.story"},"anchor":0,"focus":47}` |
| 13. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":14}}` |
| 14. 检查当前文档结构与溢出 | `document.inspect` | `{}`；返回记为`final_inspect` |
| 15. 检查实际使用字体 | `font.list` | `{}`；返回记为`fonts` |
| 16. 执行输出前技术预检 | `preflight.run` | `{}`；返回记为`preflight` |

检查：标题与详情均为活文字；页面A4且无文本溢出；时间地点及报名条件与真实活动一致。

边界：屏幕审阅不等于印厂验收；不要把本例日期地点当真实活动发布。

## threaded-newsletter：双栏串接简报

输入：两列文字框宽244、高300点，示例长文由同一故事流入两框。

| 顺序与目的 | 方法 | 参数与返回绑定 |
| --- | --- | --- |
| 1. 仅新图建立指定页面，不用于已有文档 | `file.new` | `{"width":595,"height":842,"pages":1,"facingPages":false,"margins":36,"bleed":0,"title":"双栏串接简报"}` |
| 2. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,40,553,100],"content":"text","text":"Neighbourhood Notes"}`；返回记为`title` |
| 3. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"title.story"},"anchor":0,"focus":19}` |
| 4. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Sans 3","size":28}}` |
| 5. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,130,286,430],"content":"text","text":"Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step. Community teams share practical ideas for better public spaces. Each proposal starts with local needs and a clear next step."}`；返回记为`left` |
| 6. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"left.story"},"anchor":0,"focus":1749}` |
| 7. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":11}}` |
| 8. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[309,130,553,430],"content":"text","text":""}`；返回记为`right` |
| 9. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"right.story"},"anchor":0,"focus":0}` |
| 10. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":11}}` |
| 11. 将右栏接入左栏故事，不复制正文 | `text.thread` | `{"from":{"$ref":"left.id"},"to":{"$ref":"right.id"}}`；返回记为`thread` |
| 12. 检查当前文档结构与溢出 | `document.inspect` | `{}`；返回记为`final_inspect` |
| 13. 检查实际使用字体 | `font.list` | `{}`；返回记为`fonts` |
| 14. 执行输出前技术预检 | `preflight.run` | `{}`；返回记为`preflight` |

检查：两列共享同一故事且框顺序正确；正文完整保留且不溢出；不是把同样正文复制到两列。

边界：实际长文长度与字体会改变流动；重排后再查overset与阅读顺序，不把双栏外观当成已串接。

## two-page-product-sheet：双页产品说明

输入：2个非对页页面，每个spread独立坐标，示例技术参数需按实际产品核实。

| 顺序与目的 | 方法 | 参数与返回绑定 |
| --- | --- | --- |
| 1. 仅新图建立指定页面，不用于已有文档 | `file.new` | `{"width":595,"height":842,"pages":2,"facingPages":false,"margins":36,"bleed":0,"title":"双页产品说明"}` |
| 2. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,48,553,110],"content":"text","text":"Craft Desk Lamp"}`；返回记为`title1` |
| 3. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"title1.story"},"anchor":0,"focus":15}` |
| 4. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Sans 3","size":28}}` |
| 5. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,150,553,390],"content":"text","text":"Focused light for reading and making.\nMaterials: aluminium and recycled polymer.\nPower: 8 W. Colour temperature: 4000 K."}`；返回记为`intro` |
| 6. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"intro.story"},"anchor":0,"focus":120}` |
| 7. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":16}}` |
| 8. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":1,"rect":[42,48,553,110],"content":"text","text":"Setup and care"}`；返回记为`title2` |
| 9. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"title2.story"},"anchor":0,"focus":14}` |
| 10. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Sans 3","size":28}}` |
| 11. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":1,"rect":[42,150,553,420],"content":"text","text":"1. Place on a stable surface.\n2. Connect the approved power adapter.\n3. Keep the light source clear.\nDisconnect power before cleaning."}`；返回记为`care` |
| 12. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"care.story"},"anchor":0,"focus":134}` |
| 13. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":16}}` |
| 14. 检查当前文档结构与溢出 | `document.inspect` | `{}`；返回记为`final_inspect` |
| 15. 检查实际使用字体 | `font.list` | `{}`；返回记为`fonts` |
| 16. 执行输出前技术预检 | `preflight.run` | `{}`；返回记为`preflight` |

检查：两页标题分属不同spread；规格与维护说明不丢失；导出含2页。

边界：样例参数不是认证结果；正式说明须按产品实际安全资料审核。

## plan-comparison-table：套餐对比活表格

输入：3行3列，首行为表头；价格单位和周期在真实任务中明确。

| 顺序与目的 | 方法 | 参数与返回绑定 |
| --- | --- | --- |
| 1. 仅新图建立指定页面，不用于已有文档 | `file.new` | `{"width":595,"height":842,"pages":1,"facingPages":false,"margins":36,"bleed":0,"title":"套餐对比活表格"}` |
| 2. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,48,553,110],"content":"text","text":"Plan comparison"}`；返回记为`title` |
| 3. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"title.story"},"anchor":0,"focus":15}` |
| 4. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Sans 3","size":28}}` |
| 5. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,160,553,430],"content":"text","text":"Plan\tSeats\tUSD/month\nStarter\t5\t19\nTeam\t20\t59"}`；返回记为`grid` |
| 6. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"grid.story"},"anchor":0,"focus":44}` |
| 7. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":14}}` |
| 8. 按制表符把所选文字转为表格 | `table.convertFromText` | `{"columnSeparator":"tab"}`；返回记为`table` |
| 9. 明确选择本次转换的整表 | `table.select` | `{"story":{"$ref":"grid.story"},"table":{"$ref":"table.table"},"what":"table"}` |
| 10. 设置一行重复表头 | `table.options` | `{"headerRows":1}` |
| 11. 检查实际单元格 | `table.get` | `{"story":{"$ref":"grid.story"},"table":{"$ref":"table.table"}}`；返回记为`table_info` |
| 12. 检查当前文档结构与溢出 | `document.inspect` | `{}`；返回记为`final_inspect` |
| 13. 检查实际使用字体 | `font.list` | `{}`；返回记为`fonts` |
| 14. 执行输出前技术预检 | `preflight.run` | `{}`；返回记为`preflight` |

检查：真实表格单元格而非空格对齐文字；行列及表头保留；源工程和IDML均可编辑。

边界：表格不自动计费，也不自动核实价格；转换后检查列宽、换行及文字是否溢出。

## brand-copy-revision：品牌文案替换并保留段落样式

输入：首段为标题、次段为正文，替换2次品牌名。

| 顺序与目的 | 方法 | 参数与返回绑定 |
| --- | --- | --- |
| 1. 仅新图建立指定页面，不用于已有文档 | `file.new` | `{"width":595,"height":842,"pages":1,"facingPages":false,"margins":36,"bleed":0,"title":"品牌文案替换并保留段落样式"}` |
| 2. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,70,553,430],"content":"text","text":"ACME annual review\nACME supports teams with practical tools."}`；返回记为`copy` |
| 3. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"copy.story"},"anchor":0,"focus":60}` |
| 4. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":16}}` |
| 5. 创建本次标题段落样式 | `style.paragraph.create` | `{"name":"Review Title","chars":{"fontFamily":"Source Sans 3","size":28}}` |
| 6. 只选首段文字的UTF-8字节范围 | `text.select` | `{"story":{"$ref":"copy.story"},"anchor":0,"focus":18}` |
| 7. 应用标题样式 | `style.paragraph.apply` | `{"name":"Review Title","clearOverrides":true}` |
| 8. 只替换本次故事内的品牌名 | `find.change` | `{"find":"ACME","change":"Craft Studio","scope":"story","story":{"$ref":"copy.story"},"caseSensitive":true}`；返回记为`replacement` |
| 9. 检查当前文档结构与溢出 | `document.inspect` | `{}`；返回记为`final_inspect` |
| 10. 检查实际使用字体 | `font.list` | `{}`；返回记为`fonts` |
| 11. 执行输出前技术预检 | `preflight.run` | `{}`；返回记为`preflight` |

检查：两次替换且旧词消失；标题仍绑定Review Title样式；其他故事不执行文档级替换。

边界：已有项目先确认替换范围和名称冲突；本例样式创建仅新文档示例，不能覆盖既有同名样式。

## overset-repair：文本溢出诊断与扩框修复

输入：初始36点高文本框故意溢出，扩至420点高；原字号不缩小。

| 顺序与目的 | 方法 | 参数与返回绑定 |
| --- | --- | --- |
| 1. 仅新图建立指定页面，不用于已有文档 | `file.new` | `{"width":595,"height":842,"pages":1,"facingPages":false,"margins":36,"bleed":0,"title":"文本溢出诊断与扩框修复"}` |
| 2. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,100,553,136],"content":"text","text":"Keep the full message visible before delivery. Keep the full message visible before delivery. Keep the full message visible before delivery. Keep the full message visible before delivery. Keep the full message visible before delivery. Keep the full message visible before delivery. Keep the full message visible before delivery. Keep the full message visible before delivery. Keep the full message visible before delivery. Keep the full message visible before delivery. Keep the full message visible before delivery. Keep the full message visible before delivery. Keep the full message visible before delivery. Keep the full message visible before delivery."}`；返回记为`copy` |
| 3. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"copy.story"},"anchor":0,"focus":657}` |
| 4. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":14}}` |
| 5. 记录修复前的实际溢出 | `document.inspect` | `{}`；返回记为`before_repair` |
| 6. 仅扩展本次文本框高度，不缩放文字 | `transform.resize` | `{"ids":[{"$ref":"copy.id"}],"to":[42,100,553,520],"content":false,"from":[42,100,553,136]}` |
| 7. 检查当前文档结构与溢出 | `document.inspect` | `{}`；返回记为`final_inspect` |
| 8. 检查实际使用字体 | `font.list` | `{}`；返回记为`fonts` |
| 9. 执行输出前技术预检 | `preflight.run` | `{}`；返回记为`preflight` |

检查：修复前确有overset，修复后消失；文字内容与字号保持；不是隐藏或删除溢出内容。

边界：真实版面不能无条件向下扩框，先检查与其他对象、页脚及安全边界是否冲突。

## bleed-review-pdf：带出血的审阅PDF

输入：A4页面、四边9点出血；约3.175mm，真实印厂若要求3mm应换算8.504点。

| 顺序与目的 | 方法 | 参数与返回绑定 |
| --- | --- | --- |
| 1. 仅新图建立指定页面，不用于已有文档 | `file.new` | `{"width":595,"height":842,"pages":1,"facingPages":false,"margins":36,"bleed":9,"title":"带出血的审阅PDF"}` |
| 2. 创建延伸到出血区的背景条 | `frame.create` | `{"rect":[-9,-9,604,150],"content":"unassigned"}`；返回记为`bar` |
| 3. 为本次背景设置颜色 | `object.color` | `{"ids":[{"$ref":"bar.id"}],"color":"#1d4ed8","target":"fill"}` |
| 4. 背景条不保留默认黑色轮廓 | `object.stroke` | `{"ids":[{"$ref":"bar.id"}],"swatch":"[None]","weight":0}` |
| 5. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,220,553,390],"content":"text","text":"A print-ready conversation starts here"}`；返回记为`title` |
| 6. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"title.story"},"anchor":0,"focus":38}` |
| 7. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Sans 3","size":30}}` |
| 8. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,450,553,570],"content":"text","text":"Confirm paper, colour profile, bleed and finishing with the printer."}`；返回记为`note` |
| 9. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"note.story"},"anchor":0,"focus":68}` |
| 10. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":18}}` |
| 11. 输出包含出血和裁切标记的审阅PDF | `file.exportPdf` | `{"path":"bleed-review.pdf","bleed":true,"marks":{"crop":true,"bleed":true,"pageInfo":false},"standard":"none"}`；返回记为`bleed_pdf` |
| 12. 检查当前文档结构与溢出 | `document.inspect` | `{}`；返回记为`final_inspect` |
| 13. 检查实际使用字体 | `font.list` | `{}`；返回记为`fonts` |
| 14. 执行输出前技术预检 | `preflight.run` | `{}`；返回记为`preflight` |

检查：背景越过裁切边缘；PDF包含出血审阅区域；没有把RGB审阅稿说成已通过印厂色彩验收。

边界：这是技术审阅输出，不宣称PDF/X、CMYK、软打样或印厂已验收。固定输出名只用于新的空工作目录。

## interactive-guide-link：交互PDF阅读链接

输入：一页阅读指南，URL是不可用占位值，正式交付前替换为已确认地址。

| 顺序与目的 | 方法 | 参数与返回绑定 |
| --- | --- | --- |
| 1. 仅新图建立指定页面，不用于已有文档 | `file.new` | `{"width":595,"height":842,"pages":1,"facingPages":false,"margins":36,"bleed":0,"title":"交互PDF阅读链接"}` |
| 2. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,70,553,140],"content":"text","text":"Reader guide"}`；返回记为`title` |
| 3. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"title.story"},"anchor":0,"focus":12}` |
| 4. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Sans 3","size":30}}` |
| 5. 创建独立可编辑文本框并记录返回值 | `frame.create` | `{"spread":0,"rect":[42,210,553,280],"content":"text","text":"Open the online guide"}`；返回记为`link` |
| 6. 用UTF-8字节范围选择本次故事 | `text.select` | `{"story":{"$ref":"link.story"},"anchor":0,"focus":21}` |
| 7. 设置已核实的字体和字号 | `type.char` | `{"attrs":{"fontFamily":"Source Serif 4","size":20}}` |
| 8. 为选中活文字建立链接 | `hyperlink.create` | `{"url":"https://example.invalid/guide","name":"Online guide"}`；返回记为`link_result` |
| 9. 核对实际链接目的地 | `hyperlink.list` | `{}`；返回记为`hyperlinks` |
| 10. 检查当前文档结构与溢出 | `document.inspect` | `{}`；返回记为`final_inspect` |
| 11. 检查实际使用字体 | `font.list` | `{}`；返回记为`fonts` |
| 12. 执行输出前技术预检 | `preflight.run` | `{}`；返回记为`preflight` |

检查：链接记录绑定当前文字；PDF实际含链接注释；占位URL已按任务替换。

边界：只生成链接注释，不访问外部地址；文件内有链接不代表网页可用或权限已验证。

