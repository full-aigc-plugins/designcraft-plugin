# DesignCraft 支持与验收矩阵

离线检查已在 macOS arm64 / Python 3.14.3 通过；GitHub Actions 在 Ubuntu runner 上的 Python 3.11、3.12、3.13 矩阵也通过单测、包校验和空白检查，详见 [CI run](https://github.com/full-aigc-plugins/designcraft-plugin/actions/runs/37768324487)。这两类证据只覆盖离线软件检查。

固定 CLI 0.2.1 尚未安装或运行，macOS arm64 尚无原生验收。Codex 宿主发现、模型自动路由、重启后的真实任务恢复、真实工程与导出质量和正式发行仍为 `NOT_RUN`/`UNPUBLISHED`。CI 通过不代表原生、宿主或创作验收。未实测的操作系统、宿主、模型和 Python 组合不列为支持。其他宿主、其他操作系统、自动多轮修改及 ArtCraft 集成明确留给后续变更。

联网下载并安装原生 CLI 会在选定 runtime-home 写入固定制品，必须先取得覆盖该安装的明确授权；离线查询与检查不安装 CLI。安装授权不自动授权工程读写、工程导出或市场发布，这些按各自任务范围判断。

机器可校验状态见 [support-matrix.json](../support-matrix.json) 与 [project-status.json](../project-status.json)。包校验会拒绝矩阵版本或验收状态与项目状态不一致，以及宿主状态为 `NOT_RUN` 时出现已测平台声明。

证据清单将本地运行环境与外部环境分开校验。外部 CI 记录必须把 `executionEnvironment` 放在受摘要绑定的报告中，并通过 `environmentArtifactPath` 引用该报告；检查器验证报告摘要和环境字段，不会把 GitHub runner 错判为本机环境漂移。报告摘要不证明签名者身份，来源可信度仍须由发布流程单独核验。
