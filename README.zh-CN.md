# designcraft 插件本地开发项目

包含独立 `designcraft-skills` 的六项自包含技能快照及逐文件摘要。来源未发布；宿主发现与九项真实只读模型路由在内置 Codex CLI 0.162.0-alpha.2 / gpt-6-astra / macOS arm64 通过；原生执行、完整领域流程与创作验收仍开放。

校验：`python3 -I -B scripts/validate_package.py`；测试：`python3 -I -B -m unittest discover -s tests`。

运行 `python3 -I -B scripts/record_offline_evidence.py` 会执行离线测试和包校验，生成绑定 runId、环境、插件/来源/运行时摘要以及输入/报告摘要的 `evidence-manifest.json`。运行 `python3 -I -B scripts/evidence_freshness.py evidence-manifest.json` 检查证据是否仍绑定当前文件，并核对层状态与 `project-status.json`、`support-matrix.json`；身份变化会将相关记录报告为 `STALE`。原生、CI、宿主、平台、模型、创作和发行层分别记录实际状态，不用宿主只读通过代替原生或创作验收。

详见[架构](docs/architecture.zh-CN.md)、[支持矩阵](docs/support-matrix.zh-CN.md)、[快照维护](docs/snapshot-maintenance.zh-CN.md)及 project-status.json。[OpenSpec 优化规范与任务](openspec/changes/harden-designcraft-plugin-delivery/proposal.md)已建立并通过严格校验，Harness 与候选校验已实施；宿主发现与只读路由通过；原生、创作与发行验收待完成。开发候选源码已推送至[公开 GitHub 仓库](https://github.com/full-aigc-plugins/designcraft-plugin)的 `main` 分支；尚无版本标签、GitHub Release 或插件市场发行。
