# 真实模型宿主原生场景

关联任务：插件 3.4、4.4、2.5c，均保持开放。使用已存在 ChatGPT.app 内置 Codex CLI 0.162.0-alpha.2、默认 gpt-6-astra，从公开仓库固定 f8809f0 安装到隔离 CODEX_HOME；安装文件摘要在调用前后与该提交核对。仅使用既有固定运行时，不安装或升级，不修改全局配置或缓存。

missing-runtime.trace.json 保存模型实际读取技能与参考、公开 readiness 调用及原始输出：UNAVAILABLE / locked_cli_not_installed / dispatchPrerequisitesMet=false；目标运行时目录实际不存在，没有原生派发。

native-create-export.trace.json 保存模型实际通过 Harness new、transition、native 的调用及输出；源公开网关执行五步创建、检查、预检、保存与 PDF 导出。四页工程与 PDF、原始计划/回执、原 task/run 持久化材料均在本目录，摘要见 report.json。状态为 EXECUTING/revision 3，原生 NATIVE_EXIT_ZERO_REVIEW_REQUIRED；未标记 COMPLETED。

此处不证明既有工程局部修订、重启恢复续跑、逐页创作审阅或人工签核，不替代 AV-02/03/04 完整验收和正式来源/发行门禁。原始临时路径保留用于追踪；本目录为可审查归档副本。仅归档公共执行命令、输出与最终答复，未复制认证、全局配置、宿主分析内容或服务 stderr。

重启只读场景暴露旧 show 以 a+b 打开锁文件而被沙箱拒绝；原始调用/失败见 restart-show.public-tool-calls.json。修复后从新进程显式加载当前工作树技能（尚非已更新安装缓存），公开 show 实际返回同一任务 EXECUTING/revision 3 和原 runId，任务文件逐字节不变；完整公共调用/输出及修复脚本摘要见 restart-show-fixed.trace.json。这只证明当前脚本在只读宿主的持久化读取，不代表 UNKNOWN 恢复续跑或完整安装候选验收。
