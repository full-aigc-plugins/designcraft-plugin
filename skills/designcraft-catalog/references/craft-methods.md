# 商品目录：图片、SKU与交付关联

先读取商品对应表：每条记录必须有SKU、确认过的名称、规格、价格/币种和图片路径。缺失数据明确标记待确认，不凭图片猜型号、尺寸或售价。示例只有两条测试商品，用于展示一页两列的完整流程；没有自动CSV合并或真实商品信息保证。

## 按记录执行

1. 新任务 `file.new {"width":595,"height":842,"pages":1,"facingPages":false,"margins":36,"bleed":0}`。已有工程先 `document.inspect`，确认页面、坐标、已有对象和样式，跳过新建；不清空用户内容。页面扩展/类别分组由真实商品数量决定，不能把一页示例当成任意数量模板。
2. 创建标题；用 `font.list` 核对字体。`style.paragraph.create {"name":"Catalog Product","chars":{"fontFamily":"Source Sans 3","size":11}}` 建立正文样式。已有同名样式先检查再复用或改名，不覆盖它。
3. 对SKU-101调用 `frame.create {"spread":0,"rect":[42,140,286,340],"content":"graphic"}`，记下返回框ID。`file.place {"path":"catalog-input/sku-101.png","frame":真实图片框ID,"link":true}` 只置入该商品图片。路径根据当前素材替换，不能依赖当前选择来判断图片归属。
4. `object.fit {"ids":[真实图片框ID],"mode":"fitProportionally"}` 保持比例完整展示。它允许留白；若用户要求铺满，用 `fillProportionally` 后逐图确认被裁掉的部分，不能拉伸商品外形。
5. `frame.create` 在 `[42,360,286,620]` 创建该SKU的名称、价格与规格文字，记下返回 `id`、`story`。`text.select {"story":真实文字故事ID,"anchor":0,"focus":UTF8字节数}` 后调用 `style.paragraph.apply {"name":"Catalog Product","clearOverrides":true}`。只对本次新建商品文字清除局部覆盖，已有精排文字须保留有意格式。
6. 对SKU-205以自己的图片文件、图片框和文字框重复步骤，示例右列x=309..553。不能沿用前一商品的框ID或相同图片占位。正文变更后重算UTF-8字节数，不能用字符个数代替。
7. `story.get {"frame":实际文字框ID}` 逐条比对输入全文；`overset` 为null才没有溢出，数值0也表示溢出。`links.list {}` 返回每个asset的路径、状态及uses中的框ID，按SKU检查文件确实被目标框使用；同一图片用于多商品时也要核对所有实例。状态missing/modified需处理，embedded不等于具备可搬运的外部链接。
8. `preflight.run {"minPpi":150}` 检查有效分辨率、字体与溢出。150是校样示例阈值，正式印刷依印厂要求调整；不能用原图像素数替代置入尺寸对应的PPI。预检通过仍要看图片内容、裁切及文字价格对应关系。
9. 保存新路径的原生工程，导出PDF校样和IDML。`file.package {"dir":"catalog-package","idml":true,"pdf":true}` 收集链接与允许分发的字体，读取返回report与files。字体可能因许可受限而不复制，应说明缺口，不能把打包目录存在当成完整交付。
10. 在隔离验收副本中，让原素材路径不可用后重新打开打包的原生工程；检查链接状态、文件摘要和SKU文字，实际再导出PDF。对用户原始素材只读，不移动或删除它们做测试。

## 命令入口

[结构化步骤](craft-steps.json) 的products保存示例对应表，steps是展开后的实际命令。`{"$ref":"sku101_image.id"}` 表示之前返回的框ID。实时MCP先等待 `editor_status`，按实际schema通过 `execute` 调用同会话命令，并以真实返回值替换命名引用；独立CLI不会自动同步到Web编辑器。

独立安装包含 [引用编译器](../scripts/write_script.py)，只转换引用，不导入或编排业务。以本技能目录为基准，确认图片文件已存在后，使用argv运行：

```text
python3 scripts/write_script.py --recipes references/craft-steps.json --scene catalog --output steps.json
designcraft-cli script steps.json --save catalog.designcraft --export catalog.pdf --export catalog.idml
```

Windows的Python入口可能为 `python`。CLI工作目录须能解析素材相对路径；可改成当前工作区实际文件路径，不能使用开发者机器固定路径。所有输出使用新目录；已有工程须先调整页码、布局和样式，再编译并显式传 `--in`，`--existing` 本身只跳过新建并重算引用。

## 来源和验收限制

[GitHub来源](workflow-sources.json) 固定le-tex/InDesignScripts提交及已读文件摘要；只借鉴链接图像实例和输出的经验，Craft步骤与商品样例原创。旧的空网格配方已替换；本场景没有自动母版、自动目录页码或任意CSV数据合并的保证。[命令目录](craft-command-evidence.json) 的main观察不能单独证明业务通过；真实结果看原生回归报告，最终版式与图片真实性单独验收。
