# AV-03 逐页审阅记录

审阅记录采用 `designcraft-page-review/v1` 和 `designcraft-layout-rubric/v1`，并绑定 AV-02 清单的 `runId`、工程 SHA-256、AV-02 清单摘要及每页预览文件摘要。每页编号必须与已重开工程页数一致，每张预览必须存在于交付根目录且摘要匹配。

每页六项检查全部显式记录状态和说明：

- `hierarchy`：标题、正文、辅助信息的视觉层级。
- `whitespace`：页边距、段间距及内容留白。
- `alignment`：网格、基线和组件对齐。
- `readability`：字号、对比度和阅读顺序。
- `cropping`：文本/图片是否被意外裁切。
- `crossPageConsistency`：字体、间距、颜色和页眉页脚跨页一致性。

文档结论必须分开写 `structure`、`visual`、`output`、`editability`，每项记录 `PASS`、`FAIL` 或 `NOT_RUN` 与说明。审阅来源必须标为 `human` 或 `automated`；自动审阅还要记录模型名称。没有参考图时，`basis.type` 使用 `task-spec` 并绑定任务规范文件摘要，不要求用户额外提供参考图。

```bash
python3 -I -B "$SKILL_DIR/scripts/page_review.py" \
  --root "/absolute/path/to/deliverables" \
  --artifact-manifest "/absolute/path/to/artifact-manifest.json" \
  --review "/absolute/path/to/page-review.json"
```

该命令验证记录格式、当前工程和预览摘要、页数、固定 rubric、每项状态、依据文件及审阅来源。`PASS` 只表明记录完整且绑定当前文件；它不能证明人或模型的视觉判断属实，也不能代替 AV-01 业务问题、AV-02 重开、AV-04 修订/导出检查。任何一项 `FAIL` 时输出 `FAIL`；出现 `NOT_RUN` 时输出 `NOT_RUN`，不能据此完成任务。
