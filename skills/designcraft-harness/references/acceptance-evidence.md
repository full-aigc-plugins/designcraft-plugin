# 交付证据接入

本参考说明 Harness 如何消费技能源 AV-01 至 AV-04 契约。校验器只证明输入记录与摘要绑定，不代替原生打开或视觉判断。

## AV-02 产物和重开

任务进入 `VERIFYING` 或 `REVIEW_REQUIRED` 后运行：

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" verify-artifacts \
  "$TASK_ID" --expected-revision "$REVISION" \
  --root "$DELIVERABLE_DIR" \
  --manifest "$DELIVERABLE_DIR/artifact-manifest.json"
```

清单须绑定当前候选 SHA、固定契约版本、预期路径/格式/字节数/摘要以及 `reopenEvidence: PASS`。只有文件身份一致、重开为 `NOT_RUN` 时拒绝登记。不能通过手工创建 `status: PASS` 文件代替校验。

## AV-01 原始业务回执

先登记当前 AV-02，再运行：

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" verify-business \
  "$TASK_ID" --expected-revision "$REVISION" \
  --root "$DELIVERABLE_DIR" \
  --artifact-manifest "$DELIVERABLE_DIR/artifact-manifest.json" \
  --receipt "$REOPEN_RECEIPT"
```

Harness 调用源端公开 `designcraft-business-evidence/v1`，重算原始 stdout，核对预检/PDF、工程身份、重开 runId、运行时锁和当前 AV-02。手写 PASS、警告/错误/未知字段、旧分类或候选错绑均不能登记。每次完成门禁重新验证回执、清单、工程和校验资源；其中任何变化都会使 AV-01 失效。此合同不验证回执签名、原生执行真实性或视觉质量，PDF 字节数/页数也不能独立证明原生输出内容身份。

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

## AV-04 局部修订

AV-04 使用技能源 `designcraft-revision/v1` 校验规范化修订证据。修订后的当前候选必须先有 Harness 已验证的 AV-02 和 AV-03；证据记录还需包含修订前后的清单、完整页审阅、对象快照、明确授权范围、影响页和所有旧导出对应的新产物重验摘要：

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" verify-revision \
  "$TASK_ID" --expected-revision "$REVISION" \
  --root "$REVISION_EVIDENCE_DIR" \
  --revision "$REVISION_EVIDENCE_DIR/revision.json"
```

Harness 会绑定修订回执与当前任务的候选摘要；证据文件或其中引用的任何材料变化都会使 AV-04 失效。校验器拒绝越权变化、Story 影响页遗漏、摘要漂移和未重验的导出。PASS 仅表示证据结构与身份互相匹配，不代表原生编辑、用户授权、人工审阅或创作质量已经获得独立证明。

## 完成边界

完成状态还要求无未解决阻塞项、候选身份当前且必要 AV-01 至 AV-04 证据通过。缺少任一层都保留实际状态和下一步，不把计划或文件存在写成验收通过。

## 执行回执与保全失败

源网关 schema 2 的 `INPUT_CHANGED_REVIEW_REQUIRED`、`SKILL_CHANGED_REVIEW_REQUIRED` 和 `INPUT_OR_SKILL_CHANGED_REVIEW_REQUIRED` 分别记录输入变化、资源变化及保全核对不完整。原生 exitCode 可能为 0，而网关进程因保全失败返回非零；Harness 保留这两层退出码、原始回执和 runId，添加对应阻塞项，下一步只读核对，不再次调用或标记完成。缺少保全证据或退出关系矛盾按 UNKNOWN 处理。

源检查点路径经系统目录别名解析后必须与调用者给出的保存工程是同一文件；之后以源回执路径身份核对重开计划、输入摘要和 inspection。另一份同内容文件或直接符号链接工程不能代替原检查点。
