# 执行、输入保全与恢复细节

## 命令目录、参数与单会话计划

`scripts/commands.py list` 从实际固定CLI读取完整原生目录，`describe <命令ID>` 返回参数与分类。
显式 `--catalog <原生JSON目录文件>` 支持离线查询与检查，执行禁止使用离线目录。
计划格式为 `{"domain":"designcraft","steps":[{"command":"实际命令ID","params":{}}]}`。
`check <计划JSON>` 检查结构、命令存在及原生 schema 的受支持约束；纯文本参数只展示原文，参数类型和状态前置条件由原生程序判断，不能将检查通过当成执行通过。
`run <计划JSON> --output <新目录>` 重新读取真实目录，在一个原生会话中执行整个计划，保留执行回执；零退出状态仍标记 REVIEW_REQUIRED。`receipt <旧回执路径>` 仅离线读取历史回执；`recover <原回执路径> --checkpoint-receipt <重开回执>` 只核对保存工程并输出安全恢复计划，不安装、不自动执行，也不重放原计划。
原生源工程用 DesignCraft `--source`，照片库用 LightCraft `--library` 与重复 `--import`，PDF 文件根用 PrintCraft `--root`。
超时或中断保留 UNKNOWN 回执，不自动重放可能已写入的命令。

对包含已完成 `file.saveAs` 的部分失败回执，先用一个新计划执行 `file.open` 与 `document.inspect`，并用 `--input` 登记保存工程；之后 `commands.py recover <原回执> --checkpoint-receipt <重开回执>` 只核对身份并生成未启动后缀。机器结果按 `designcraft-checkpoint-recovery/v1` 输出 `originalRunId`、`reopenRunId`、保存工程 SHA 和剩余计划，供插件 Harness 交叉核验。只有返回 `RECOVERY_READY` 才可人工审阅后显式提交为新计划；已完成前缀和可能有副作用的失败步永不重放。旧对象的 `step:N` 跨会话引用会被拒绝自动恢复，必须先按新 inspection 的对象身份人工重绑。检查点缺失、摘要漂移、未知状态或回执缺字段时只返回诊断。


## 安装诊断补充

需要只检查安装时：

```bash
python3 -I -B "$SKILL_DIR/scripts/bootstrap.py"
python3 -I -B "$SKILL_DIR/scripts/cli.py" -- --version
```

`--runtime-home` 或 CRAFT_RUNTIME_HOME 指定隔离运行时目录，放在 `--` 之前。
`--archive` 指向已有固定 ZIP，仍校验归档与二进制摘要。
安装失败返回 dependencySetup，不自动重试编辑或渲染；校验失败保留已有目录。
当前锁仅固定原生 CLI，发布快照与宿主自动发现仍须另行验证。
