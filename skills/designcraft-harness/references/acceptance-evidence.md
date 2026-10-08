# 交付证据接入

本参考说明 Harness 如何消费技能源 AV-02/AV-03 契约。校验器只证明输入记录与摘要绑定，不代替原生打开或视觉判断。

## AV-02 产物和重开

任务进入 `VERIFYING` 或 `REVIEW_REQUIRED` 后运行：

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" verify-artifacts \
  --root "$DELIVERABLE_DIR" \
  --manifest "$DELIVERABLE_DIR/artifact-manifest.json"
```

清单须绑定当前候选 SHA、固定契约版本、预期路径/格式/字节数/摘要以及 `reopenEvidence: PASS`。只有文件身份一致、重开为 `NOT_RUN` 时拒绝登记。不能通过手工创建 `status: PASS` 文件代替校验。

## AV-03 页级审阅

AV-03 需要当前 AV-02 PASS，并使用同一目录和产物清单：

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" verify-review \
  "$TASK_ID" --expected-revision "$REVISION" \
  --root "$DELIVERABLE_DIR" \
  --artifact-manifest "$DELIVERABLE_DIR/artifact-manifest.json" \
  --review "$DELIVERABLE_DIR/page-review.json"
```

校验内容绑定当前工程、清单摘要、rubric、逐页预览摘要、审阅来源和独立结论。预览、清单或审阅变化会使证据失效。校验器不证明人工或视觉模型的判断本身真实正确。

## 完成边界

完成状态还要求无未解决阻塞项、候选身份当前且必要 AV-01 至 AV-04 证据通过。缺少任一层都保留实际状态和下一步，不把计划或文件存在写成验收通过。
