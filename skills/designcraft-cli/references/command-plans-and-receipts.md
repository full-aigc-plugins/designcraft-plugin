# 命令计划与回执

## 查询和检查

`scripts/commands.py list` 和 `describe <command-id>` 从固定 CLI 读取当前目录与参数。离线 catalog 可供查看/结构检查，不得用于执行。`check` 的检查范围取决于固定原生命令 schema；纯文本参数、业务前置和对象状态可能仍需原生运行时判断。

计划采用 `{"domain":"designcraft","steps":[{"command":"<真实命令 ID>","params":{}}]}`。多步计划在一个原生会话中执行，以保留同一会话内的对象引用。

## 写入与回执

执行前确认安装授权、输入保全范围、输出路径和任务授权；执行入口会记录计划、目录、输入、技能资源和运行时摘要。执行后保留 stdout/stderr、退出信息、终止状态和步骤级观察粒度。

如果原生端只返回整体结果，每步标记 `BATCH_EXIT_ZERO_REVIEW_REQUIRED` 或 `UNKNOWN`，不推断单步成功/失败。超时或终止不明时禁止自动重放。旧回执缺少身份只能只读展示缺口，不能升级为恢复许可。

结果身份和哈希可以发现部分漂移，但不会沙箱化参数内的路径、子进程或其他副作用。`--source`/`--input` 登记的文件和目录会在执行前后比较；目录中新建文件可触发 `INPUT_CHANGED_REVIEW_REQUIRED`，这是执行后检测，不会阻止写入。原生命令参数中的路径不会自动登记，也不限制在 `--output` 内；未登记路径上的副作用不会出现在输入摘要中。固定 CLI 0.2.1 的实测回执与摘要位于 `evidence/native/designcraft-cli-0.2.1/path-side-effects/`。工程保存重开和内容验收需通过独立产物契约完成。

## 业务结果分类

DesignCraft 回执增加 `businessAssessment`（`designcraft-business-assessment/v1`），仅分类具有固定结果结构的 `preflight.run`、`links.list`、`data.fields`、`data.merge` 和 `file.exportPdf`。错误预检和缺失链接为 `REJECTED`；预检警告、被修改链接、合并计数但未核对字段内容、或带警告的 PDF 导出为 `REVIEW_REQUIRED`；已知结构之外的字段、计数不一致或无法解析的原生批次为 `UNKNOWN`。其他命令保持 `NOT_CLASSIFIED`。

该分类与原生进程退出状态分离：业务拒绝不会改写 `NATIVE_EXIT_ZERO_REVIEW_REQUIRED`，也不会声称单步命令独立成功。未知结构保持未知，避免新 CLI 字段被忽略。对于 `data.merge`，`records` 和 `pages` 只证明原生端返回了计数；字段替换仍须从输出工程或预览核对。固定 0.2.1 目录没有 `data.placeholder.add`，本次含 `{{Name}}` 的试验保留了原样占位文本，因此单凭合并计数不能接受交付。

固定 CLI 0.2.1 的 macOS arm64 实测与失败样本位于 `evidence/native/designcraft-cli-0.2.1/business-assessment/`；目录摘要与原始回执见同层 `assessment-summary.json`。离线回归覆盖溢出、缺图、警告、未知字段与新字段拒绝。
