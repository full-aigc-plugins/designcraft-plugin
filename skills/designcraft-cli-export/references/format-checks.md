# 导出格式检查边界

本参考定义不同输出格式需要独立记录的检查项，不声称某格式已由当前固定 CLI 支持或实测。离线运行 `python3 -I -B "$SKILL_DIR/scripts/format_probe.py" --file /absolute/path/export.pdf` 可生成绑定文件名、字节数和 SHA-256 的结构检查 JSON；也可使用 `--format` 显式指定格式。`PASS` 仅表示探针覆盖的结构子集通过，PDF 压缩对象/继承页面框会给出 `PARTIAL`。格式探针不解码完整视觉内容，不判断创作正确性、转换损失或应用兼容性，也不完成 AV-01/02/03/04。

| 格式 | 基本身份检查 | 内容/可编辑性检查 | 未验证时的说明 |
|---|---|---|---|
| PDF | 文件签名、字节数、页数、尺寸 | 页面文本、链接/字体、视觉审阅；适用时记录内部 PDF/X 检查 | 内部检查不是第三方认证；字体替换或交互语义可能改变 |
| 图片 | 文件签名、像素宽高、页/帧数量 | 对照源工程页面预览颜色、裁切和清晰度 | 图片不是可编辑工程，逐页输出数量需单独核对 |
| IDML | ZIP/包结构、成员清单与摘要 | 在新会话或目标应用重开并检查关键样式、文本与链接 | 可编辑性依赖目标应用；未重开时不得声称互操作通过 |
| EPUB | 容器和包文档结构、资源清单 | 新会话验证导航、文本、图片及阅读顺序 | 流式重排可能改变分页；没有目标阅读器证据则标为未验收 |

图片探针支持 PNG/JPEG/WebP 及经典 TIFF 的尺寸头部读取；完整像素解码、动画/多帧数量及 BigTIFF 当前不覆盖。IDML 探针校验 ZIP 成员路径、CRC、designmap 与可发现的 Stories XML；EPUB 探针校验 ZIP 成员、mimetype、container、package manifest 和 spine 资源引用。结构通过仍需目标应用或阅读器重开与人工视觉审阅。`pdfxExternalCertification` 固定为 `NOT_RUN`；离线检查绝不声称取得外部 PDF/X 认证。

输出清单绑定当前源工程和导出文件摘要。某一类型通过，不推出其他类型通过；损失项应按当前原生结果记录，不能仅凭格式名称推测。

## 标准参考

- EPUB 容器、Package Document、导航和阅读系统要求以 [W3C EPUB 3.3](https://www.w3.org/TR/epub-33/) 为准。
- IDML 包成员与文档结构检查参照 [Adobe InDesign Markup Language File Format Specification](https://community.adobe.com/havfw69955/attachments/havfw69955/indesign/632652/1/idml-specification.pdf)；通过包结构检查仍不等于目标应用重开或可编辑性通过。
