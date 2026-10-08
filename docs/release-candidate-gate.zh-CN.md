# 插件发行候选门禁

`scripts/validate_release_candidate.py` 只读检查已构建的插件包、portable/Codex 清单、市场引用和验收报告，不创建包、不提交、不发布。它要求 package version 与两个清单、发行 tag 和市场记录一致；package SHA-256 与实际归档文件一致；市场记录引用同一 package SHA-256。

`--acceptance` 是逐层报告引用清单。每个报告都必须在 `--evidence-root` 下，路径不能越界或为符号链接；报告文件摘要必须匹配，报告自身必须声明正确的 `layer`、`status: PASS` 和当前 `candidatePackageSha256`。来源发行报告还必须绑定当前 `sourceLockSha256`。必要层为 source release、CI、native runtime、host discovery、model dispatch、creative acceptance 和 evidence freshness。缺少报告、非 PASS、重复引用其他层报告、报告摘要变化或候选摘要过期都会拒绝发行。

示例：

```bash
python3 -I -B scripts/validate_release_candidate.py \
  --release /path/to/release-record.json \
  --manifest /path/to/package/plugin.json \
  --host-manifest /path/to/package/.codex-plugin/plugin.json \
  --package /path/to/designcraft-1.2.3.zip \
  --marketplace /path/to/marketplace-reference.json \
  --acceptance /path/to/acceptance-references.json \
  --evidence-root /path/to/evidence
```

校验报告摘要只证明被引用文件未变化，不证明报告签名者身份或报告内容来自可信 CI/宿主。正式运行仍需由受信发布流程验证报告来源，并先完成真实技能源来源锁核验；当前本地候选缺少这些真实发行证据，不能通过正式发行门禁。
