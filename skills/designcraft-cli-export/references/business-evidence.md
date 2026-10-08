# AV-01 业务证据校验

公开契约 `designcraft-business-evidence/v1` 通过本技能内的校验器读取原始回执，并重算 `designcraft-business-assessment/v1`。无需安装或调用原生 CLI，不写入工程。

```bash
python3 -I -B "$SKILL_DIR/scripts/business_evidence.py" \
  --root "$DELIVERABLE_DIR" \
  --artifact-manifest "$DELIVERABLE_DIR/artifact-manifest.json" \
  --receipt "$REOPEN_RECEIPT"
```

当前支持固定 CLI 的一次 `preflight.run` 和一次 `file.exportPdf`，可伴随 `file.open`、`document.inspect`、`story.get`、`links.list`。其他命令尚不支持此验收合同。原始警告、错误、未知字段和自报 PASS 与原始结果不一致均拒绝；并非所有零退出回执都可接受。

校验要求 AV-02 已重开通过，回执 runId 与清单重开会话一致、输入工程摘要当前、执行前后输入及资源未变化、运行时身份与本技能锁一致，并核对 PDF 字节数和页数。返回值绑定工程、清单、回执摘要及重算分类，`completeAcceptance` 始终为 false。插件登记时还必须有当前 AV-02，并重验这些输入和当前校验资源摘要。

校验只证明记录内部一致及当前候选绑定。原生回执没有 PDF 内容摘要，因此字节数/页数不能独立证明它生成了清单中的同一 PDF；清单文件摘要只证明当前文件身份。未验证回执签名、原生执行真实性、视觉质量、目标应用兼容性、格式损失或外部 PDF/X 认证。历史原生回执可以重新校验，但不能据此宣称由新版代码执行过原生操作。
