# 真实宿主失败检查点与重启核对

关联插件任务 3.4、4.4 和 PH-02；任务仍开放。固定公开提交 68fe772 安装到隔离 Codex CLI 0.162.0-alpha.2 / gpt-6-astra 宿主。模型实际 readiness READY 后经 Harness 创建唯一恢复验收任务，原生创建、保存检查点后，第三步故意打开不存在文件失败。原始回执区分完成前缀、可能部分失败的一步及未启动后缀，没有自动重放。

模型通过源公开入口在独立原生会话重开保存工程、检查 4 页，再运行源 recover。首次 Harness reconcile 正确报告 persistent_project_checkpoint_missing。第一个 app-server 终止后，新进程/新线程只依据原始保存回执及工程 SHA，通过公开 update 登记原 taskId 的 checkpointRefs，再只读 reconcile。只变更 checkpointRefs、revision、updatedAt，原 runId/状态仍保留，没有新任务。

最终计划核对通过，仅剩 document.inspect；但进程后代终止未被源回执确认，Harness 显示 process_descendants_termination_unverified，resumeAllowed=false。尚未取得人工单独风险确认和同一计划摘要确认，未调用 prepare-recovery、未执行剩余步骤、未标记 COMPLETED。不得把源 RECOVERY_READY 或原生重开退出零当作完整恢复续跑。report.json、两阶段公共调用、原/重开回执、任务前后状态和实际工程均可审查。

归档保留原临时路径用于身份追踪，不含认证、全局配置、服务 stderr 或模型分析内容。此记录不替代创作签核、格式外部认证或发行门禁。
