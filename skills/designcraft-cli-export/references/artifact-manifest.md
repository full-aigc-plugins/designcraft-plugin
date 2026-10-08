# AV-02 产物清单

本技能的 `scripts/artifact_manifest.py` 校验本地交付文件及其清单身份。它不连接 DesignCraft，也不证明原生工程曾经打开。只有在工程保存后由新会话完成检查，才能填写 `reopenCheck.status: "PASS"`；无法取得原生运行时或没有执行重开时必须用 `NOT_RUN`。

清单使用 schemaVersion 1，包含：

- `runId`：执行回执的 UUID。
- `projectArtifactId`：唯一的 `.designcraft` 工程条目。
- `artifacts`：项目工程和导出文件；每项包括唯一 `id`、`kind`、相对 `path`、扩展名对应的 `format`、精确 `byteCount` 与 SHA-256。回执或计划 JSON 不能作为交付产物。
- `expectations`：期望页数、每页宽高（毫米）、关键文字，以及链接素材的相对路径和 SHA-256。
- `reopenCheck`：重开状态、新会话标识、被重开的工程摘要、观察到的页数/尺寸/关键文字/链接素材、核验人和带时区时间。

校验命令：

```bash
python3 -I -B "$SKILL_DIR/scripts/artifact_manifest.py" \
  --root "/absolute/path/to/deliverables" \
  --manifest "/absolute/path/to/artifact-manifest.json"
```

成功的命令返回只证明清单字段、文件路径、格式、大小和 SHA-256 一致。`reopenEvidence` 只有在重开字段完整且与当前工程摘要、页数、尺寸、关键文字和素材清单一致时才为 `PASS`；`NOT_RUN` 和 `FAIL` 均不满足 AV-02。输出中的 `completeAcceptance` 始终为 false，因为本检查不覆盖 AV-01 问题分类、AV-03 逐页审阅或 AV-04 修订/格式兼容，也无法证明人工填写的重开观察属实。

尺寸允许每页宽高各有 0.01 毫米的舍入差异。路径不得绝对化、越级或通过符号链接逃离交付根目录。当前固定 CLI 尚未提供已验证的机器重开观测接口，因此 `PASS` 记录需要附有可复核的实际新会话操作证据，不能由退出码推导。
