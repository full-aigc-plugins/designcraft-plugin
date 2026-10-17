# 四页产品宣传册：内容计划 → 图文绑定 → 校样 → 打包

## 输入与前置检查

准备已确认的产品名称、卖点、尺寸、价格、图片和联系入口。先让用户确认四页阅读顺序：封面、产品A、产品B、下一步；本样例是420×595pt单页阅读版。不是印厂拼版或对折页顺序；实际尺寸、装订、出血、安全边距以任务要求为准。样例文字与色块仅用于技术试跑，不可当真实商品信息发布。

将图片路径和每页文案替换到 [craft-steps.json](craft-steps.json)；每个`text.select.focus`须重算为该框全文的UTF-8字节数，而不是字符数。保留货币尾零，把价格作为已确认的显示文本；不要自行推断未给出的税费、库存和产品特征。

先读取当前工具schema；[craft-command-evidence.json](craft-command-evidence.json)是固定版本观察记录，不能替代当前后端。新图才执行`file.new`；已有工程先`document.inspect`、确认页序、尺寸及目标故事，然后局部修改，不清空或把本样例的spread编号直接套入。

## 实际步骤与参数

| 步骤 | CLI命令／MCP execute中的command | 关键参数及检查 |
| --- | --- | --- |
| 建立四页阅读文档 | `file.new` | `{"width":420,"height":595,"pages":4,"facingPages":false,"margins":36,"bleed":0}`。pt单位；spread为0起始。 |
| 建立三种可编辑样式 | `style.paragraph.create` | `{"name":"Brochure Body","chars":{"fontFamily":"Source Sans 3","size":12}}`；标题24pt、页脚9pt。字体必须实际可用。 |
| 按内容计划建立每页标题、正文和页脚 | `frame.create` | 产品页正文例`{"spread":1,"rect":[42,320,378,500],"content":"text","text":"实际SKU全文"}`；记录返回的`id`与`story`。 |
| 显式应用相应样式 | `text.select` → `style.paragraph.apply` | `{"story":实际故事ID,"anchor":0,"focus":全文UTF8字节数}`，再`{"name":"Brochure Body","clearOverrides":true}`。不能只创建样式而不应用。 |
| 放置对应产品图 | `frame.create` → `file.place` | 图框`{"spread":1,"rect":[42,105,322,292],"content":"graphic"}`，置图`{"path":"brochure-input/organiser.png","frame":刚返回的框ID,"link":true}`；按SKU对应表逐项绑定。 |
| 保持图片比例 | `object.fit` | `{"ids":[实际图片框ID],"mode":"fitProportionally"}`；允许留白，不能拉伸产品。 |
| 检查故事和链接 | `story.get`、`links.list` | 前者显式传`{"frame":实际框ID}`；检查12个故事全文、页序、页码和`overset is null`。`overset=0`也表示溢出。后者检查两图片路径、status、uses.id及有效PPI。 |
| 检查校样问题 | `preflight.run` | `{"minPpi":150}`是本阅读版样本阈值，印刷按实际要求提高。缺链、溢出、低PPI先修复，同阈值复检。 |
| 保存并独立检查PDF | 原生script的`--save`、`--export`，或当前宿主保存／导出工具 | 新输出路径保存.designcraft并导出PDF/IDML；新进程重开源文件，独立解析四页PDF并逐页查看。不把零退出当作完成。 |
| 检查通过后另行打包 | `file.package` | `{"dir":"brochure-package","idml":true,"pdf":true}`。保留链接副本；字体实际可搬运性另查报告，不承诺任意字体可复制。 |

## CLI和同画面MCP

同画面操作使用已打开编辑器的同一个MCP会话；等待`editor_status`就绪，然后例如调用`execute {"command":"frame.create","params":{"spread":1,"rect":[42,105,322,292],"content":"graphic"}}`，把实际返回ID填入后续`file.place`和`object.fit`。独立CLI文件操作不会自动改变另一个已打开Web会话。

每个技能自带 [write_script.py](../scripts/write_script.py) 只转换`$ref`为原生`$N.field`，不代替排版引擎：

```text
python <本技能目录>/scripts/write_script.py --recipes <已替换输入的craft-steps.json> --scene brochure --output layout.json
designcraft-cli script layout.json --save review.designcraft --export review.pdf --export review.idml
```

使用argv运行命令，避免Windows shell转义。`layout.json`只包含排版和检查，不含打包。读取脚本返回结果的`story.get`、`links.list`、`preflight.run`；发现问题停止，修改并复检。通过且查看PDF后，才把`deliverySteps`中的命令写入独立JSON脚本：

```text
designcraft-cli script delivery.json --in review.designcraft
```

`delivery.json`是`[{"command":"file.package","params":{"dir":"brochure-package","idml":true,"pdf":true}}]`，不可将其直接拼到未经检查的排版批次。已有工程流程需要另写目标化步骤；不能以`--existing`跳过新建就假定其四页结构与样例相同。

## 完成条件与边界

四页阅读顺序和尺寸符合确认的计划；两SKU图片及文字逐项匹配；十二个故事完整、无溢出、段落样式实际应用；源图不变，打包Links内容保持；可编辑工程重开和PDF页序独立核对通过。逐页查看实际照片裁切、文字层级、断行和留白；合成色块只能证明技术链，不证明商业设计质量。

借鉴GitHub工作流事实，来源固定提交和哈希见[workflow-sources.json](workflow-sources.json)。命名框与字段匹配的经验改为Craft返回ID绑定；未移植InDesign JSX，也没有声称实现CSV模板合并。此宣传册与单页商品目录场景在页序、内容计划与阅读路径上分别执行。
