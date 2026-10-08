# 真实本地 Harness 原生调用观察

当前插件公开 Harness CLI 已通过就绪和五个命令能力门禁，真实调用 vendored 源入口和固定 CLI 0.2.1，创建四页样本、检查、预检、保存工程并导出四页 PDF。原始状态保持 `NATIVE_EXIT_ZERO_REVIEW_REQUIRED`，未手工升级为完成。

`report.json`、完整 CLI trace、任务持久化文件、原生回执和实际工程/PDF 绑定本次输入与产物。第一次按文档把 Harness 参数放在 task_id 后时被 argparse 拒绝，没有发起原生调用；将 Harness 参数放在 task_id 前后，同一任务真实执行一次。这个文档/CLI 顺序问题仍待修复。

此观察不证明模型发起原生调用、新会话重开、局部修订、恢复或人工创作签核，因此 2.5c、3.4、4.4 保持开放。
