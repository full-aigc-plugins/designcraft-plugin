# 真实 Codex 已有工程局部修订记录

本目录归档已完成的 `native-existing-revision` 模型场景，安装候选为 `cb8a129af88fee6a5703f3386d898c340cad2e7a`。实际 Codex 宿主显式使用已安装 Harness，经公开网关将第三页 Story 65 标题改为 A Considered Grid，另存四页工程、导出普通 PDF，并在独立原生会话中重开。两个原生回执均为 NATIVE_EXIT_ZERO_REVIEW_REQUIRED；两次预检均为 0 错误、0 警告。

`model.public-tool-calls.json` 保留该模型回合全部 16 对公共工具调用与输出，包括辅助检查失败，未筛去非零退出；未包含模型推理、凭据或服务器内部状态。`installed-file-sha.json` 保存安装文件核对结果；计划、原始回执、任务快照及产物均保留。回执中的临时绝对路径为实际执行路径，归档后不改写。

`before/` 是按 baseline-reuse.json 逐文件摘要复用的既有基线，不代表新模型调用。独立读取前后 ZIP 的 document.json，确认只有 Story 65 改变、spreads 和其他字段一致。

当前只归档实际完成的局部修订、导出与重开，不声称显式导出技能场景、完整逐页审阅、AV-01 至 AV-04 登记或人工签核完成。旧基线页审阅不是本次修订的当前审阅。任务仍为 EXECUTING revision 3；完整创作验收、重启恢复及正式发布任务保持开放。
