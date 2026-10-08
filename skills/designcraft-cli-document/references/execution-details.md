# 执行、输入保全与恢复细节

## 命令目录、参数与单会话计划

`scripts/commands.py list` 从实际固定CLI读取完整原生目录，`describe <命令ID>` 返回参数与分类。
显式 `--catalog <原生JSON目录文件>` 支持离线查询与检查，执行禁止使用离线目录。
计划格式为 `{"domain":"designcraft","steps":[{"command":"实际命令ID","params":{}}]}`。
`check <计划JSON>` 检查结构、命令存在及原生 schema 的受支持约束；纯文本参数只展示原文，参数类型和状态前置条件由原生程序判断，不能将检查通过当成执行通过。
`run <计划JSON> --output <新目录>` 重新读取真实目录，在一个原生会话中执行整个计划，保留执行回执；零退出状态仍标记 REVIEW_REQUIRED。
原生源工程用 DesignCraft `--source`，照片库用 LightCraft `--library` 与重复 `--import`，PDF 文件根用 PrintCraft `--root`。
超时或中断保留 UNKNOWN 回执，不自动重放可能已写入的命令。
