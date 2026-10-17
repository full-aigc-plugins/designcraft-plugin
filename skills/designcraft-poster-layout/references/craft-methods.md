# A3活动海报：三层信息、比例置图、真实QR和点击入口

## 输入及尺寸

收集确认的活动名称、主题、日期时间、地点、报名URL、主题图、投放方式和最终尺寸。缺少报名入口就保留待确认文字，不编码猜测地址。结构化示例使用虚构活动及`https://example.org/workshop`，这是可扫描的测试数据，不是真实报名页，不可直接发布。

[craft-steps.json](craft-steps.json) 给出297×420mm A3竖幅样本；精确换算`pt = mm × 72 / 25.4`，得到841.8897638×1190.5511811pt。矩形使用`[x0,y0,x1,y1]`，不是宽高；单位、`spread:0`和页内坐标不能套用到任意已有图稿。改变成品尺寸要重新排信息和净空，不直接把整页等比拉伸。

先查看当前后端的工具schema与命令目录，尤其是`object.qrCode`、`hyperlink.create`和图片置入。已核实的0.8.0原生参数见[观察目录](craft-command-evidence.json)。若当前Web/MCP后端没有QR命令，只能使用用户提供且已实际解码的QR素材置图，保留方形和白边；不能画方块冒充二维码，也不能把原生CLI新会话当作当前Web画面。

## 具体步骤与参数

| 步骤 | 实际command | 参数与必要检查 |
| --- | --- | --- |
| 建立新A3文档 | `file.new` | `{"width":841.8897637795277,"height":1190.5511811023623,"pages":1,"facingPages":false,"margins":60,"bleed":0}`；此样例为阅读校样，既有稿件先inspect，不能清空。 |
| 建立五种信息样式 | `style.paragraph.create` | `{"name":"Poster Heading","chars":{"fontFamily":"Source Sans 3","size":54},"para":{"hyphenate":false}}`；主题26pt、详情18pt、入口16pt、样稿说明11pt。尺寸按实际阅读距离调整。 |
| 标题、主题、时间地点、入口和说明分别建框 | `frame.create` | 标题例`{"spread":0,"rect":[60,60,782,150],"content":"text","text":"已确认活动名"}`。每框保存返回`id`和`story`。 |
| 对当前故事应用正确层级 | `text.select` → `style.paragraph.apply` | `{"story":实际故事ID,"anchor":0,"focus":实际全文UTF8字节数}`，再`{"name":"Poster Heading","clearOverrides":true}`。改稿后重算字节数，不能依赖上一个框的选择。 |
| 读取每框全文及溢出 | `story.get` | `{"frame":本框实际ID}`；`overset`必须为null，偏移0也算溢出。正文、日期地点及URL逐字核对。 |
| 置入真实主题图 | `frame.create` → `file.place` | 先建`{"spread":0,"rect":[60,315,782,705],"content":"graphic"}`，再`{"path":"poster-input/hero.png","frame":实际框ID,"link":true}`。 |
| 图片不拉伸 | `object.fit` | `{"ids":[主题图框ID],"mode":"fitProportionally"}`；本方案保留全部画面并允许留白，若要裁切必须单独确认主体边界。 |
| 为入口文字框添加点击目标 | `hyperlink.create` | `{"url":"确认的URL","ids":[入口框ID],"name":"Approved registration destination"}`；调用时文字选择仍应是入口故事，避免将其他故事作为来源。 |
| 编码相同URL | `object.qrCode` | `{"type":"url","content":"确认的URL","color":"[Black]","rect":[637,949,781,1093],"spread":0}`。保留周边白底净空，路径边界只含黑色图形，不能用它替换预留白边矩形。 |
| 链接与校样预检 | `links.list`、`hyperlink.list`、`preflight.run` | 图片status为ok、uses.id为主题框，有效PPI达到约定阈值；入口URL与可见文字/QR相同；`{"minPpi":150}`只是本阅读样本门槛。 |
| 保存重开及导出 | 原生`script --save --export`或当前宿主保存／导出工具 | 新路径保存.designcraft并导出PDF、IDML、PNG。新进程重开核对内容；独立PDF解析器核对297×420mm和真实点击链接。 |
| 实际扫码后单独打包 | `file.package` | `{"dir":"poster-package","idml":true,"pdf":true}`；只在全文、预检和导出图解码通过后执行。 |

## CLI与MCP执行

[write_script.py](../scripts/write_script.py) 只将命名`$ref`转换成原生`$N.field`引用，不执行排版业务。先替换结构化输入；URL必须在`approvedDestination`、入口文字、`hyperlink.create.url`和`object.qrCode.content`中一致。用argv跨平台运行：

```text
python <本技能目录>/scripts/write_script.py --recipes <已替换输入的craft-steps.json> --scene poster-layout --output layout.json
designcraft-cli script layout.json --save review.designcraft --export review.pdf --export review.idml
designcraft-cli run --in review.designcraft --export review.png
```

读取排版返回结果并检查图稿，不能只看命令零退出。`deliverySteps`不在默认批次内；只有检查和扫码通过后才将其中的命令写入独立`delivery.json`，执行`designcraft-cli script delivery.json --in review.designcraft`。该步骤不是PDF/X认证或印厂拼版。

同画面MCP操作时等待`editor_status`就绪，读取实际schema，再逐步调用如`execute {"command":"object.qrCode","params":{"type":"url","content":"已确认URL","rect":[637,949,781,1093],"spread":0}}`，记录真实返回ID。保持同一个编辑器会话，不能用独立CLI成功代替Web画面同步验收。

## 导出后的扫码与阅读检查

必须对实际导出PNG和PDF渲染图进行解码，比较完整payload与已确认URL；仅检查返回`content`不算扫码。一个解码器未识别时，先检查净空、对比度、最终物理尺寸和渲染分辨率，再用第二个真实解码器交叉检查并记录结果，未获得真实解码成功不得交付。URL长短会改变码密度，不承诺144pt对所有URL都可扫。测试URL的解码不等于真实报名页可用，真实任务还要核对目标网页。

缩小整页查看标题与时间地点是否仍可读，再以成品比例检查小字、图片裁切及二维码四周。源图保持不变，包内Links副本摘要相同；新进程打开原生文件和包内文件，五个故事和段落样式仍可编辑。样本色块只验证比例置图，不代表商业海报设计完成。

GitHub经验来源及固定提交见[workflow-sources.json](workflow-sources.json)。只借鉴尺寸、安全区域和QR交付的工作流事实，参数及版式原创适配；没有移植InDesign脚本。本技能与A4纯文字活动海报配方区分为含真实图片、原生QR、点击链接及毫米成品规格的投放流程。
