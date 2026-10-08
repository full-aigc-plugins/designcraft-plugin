# DesignCraft 支持与验收矩阵

当前可确认的是离线检查：运行宿主为 macOS 27 arm64、Homebrew Python 3.14.3；本地插件单测和包结构/候选快照检查通过。该结果只说明本地 Python 离线层。

固定 CLI 0.2.1 尚未安装或运行，目标 Python 3.11+ 与 macOS arm64 尚无原生验收。Codex 宿主发现、模型自动路由、重启后的真实任务恢复、真实工程与导出质量、CI 和正式发行均保持 `NOT_RUN`/`UNPUBLISHED`。未实测的操作系统、宿主、模型和 Python 组合不列为支持。其他宿主、其他操作系统、自动多轮修改及 ArtCraft 集成明确留给后续变更。

联网下载并安装原生 CLI 会在选定 runtime-home 写入固定制品，必须先取得覆盖该安装的明确授权；离线查询与检查不安装 CLI。安装授权不自动授权工程读写、工程导出或市场发布，这些按各自任务范围判断。

机器可校验状态见 [support-matrix.json](../support-matrix.json) 与 [project-status.json](../project-status.json)。包校验会拒绝矩阵版本或验收状态与项目状态不一致，以及宿主状态为 `NOT_RUN` 时出现已测平台声明。
