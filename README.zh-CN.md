# DesignCraft Use

# designcraft 插件本地开发项目

包含独立 `designcraft-skills` 的六项自包含技能快照及逐文件摘要。来源未发布；宿主发现与九项真实只读模型路由在内置 Codex CLI 0.162.0-alpha.2 / gpt-6-astra / macOS arm64 通过；原生执行、完整领域流程与创作验收仍开放。

校验：`python3 -I -B scripts/validate_package.py`；测试：`python3 -I -B -m unittest discover -s tests`。

运行 `python3 -I -B scripts/record_offline_evidence.py` 会执行离线测试和包校验，生成绑定 runId、环境、插件/来源/运行时摘要以及输入/报告摘要的 `evidence-manifest.json`。运行 `python3 -I -B scripts/evidence_freshness.py evidence-manifest.json` 检查证据是否仍绑定当前文件，并核对层状态与 `project-status.json`、`support-matrix.json`；身份变化会将相关记录报告为 `STALE`。原生、CI、宿主、平台、模型、创作和发行层分别记录实际状态，不用宿主只读通过代替原生或创作验收。

详见[架构](docs/architecture.zh-CN.md)、[支持矩阵](docs/support-matrix.zh-CN.md)、[快照维护](docs/snapshot-maintenance.zh-CN.md)及 project-status.json。[OpenSpec 优化规范与任务](openspec/changes/harden-designcraft-plugin-delivery/proposal.md)已建立并通过严格校验，Harness 与候选校验已实施；宿主发现与只读路由通过；原生、创作与发行验收待完成。开发候选源码已推送至[公开 GitHub 仓库](https://github.com/full-aigc-plugins/designcraft-plugin)的 `main` 分支；尚无版本标签、GitHub Release 或插件市场发行。

## 场景技能开发候选

已增加 6 个领域场景技能及 1 个内嵌编辑器入口。详见 [场景目录](docs/scene-skills.md)。本地未发布候选，不代表全部场景的创作质量已验收。

## 内嵌编辑器候选

新增 MCP Apps 与宿主浏览器接入，详见 [配置与构建](docs/editor-integration.md)。`ui/dist/` 为本地生成物；首次分发须带齐生成物。

插件展示使用上游官方图标；名称为 **DesignCraft Use**。图标来源与许可证保存在 `assets/official-icon-source.json` 和相邻 LICENSE 文件中。

源码增强候选采用 `ui/source.lock.json` 与 `ui/build-source.py`；兼容更新查询本插件自有 GitHub Releases，失败回退内置，原版 Web 不替换增强自动化运行时。当前会话保留；宿主安装验收另行记录。

## 排版场景操作手册

新增8条带具体方法、参数与结果检查的排版流程，见 [designcraft-scenario-playbooks](skills/designcraft-scenario-playbooks/SKILL.md)。包含原生脚本返回引用、活表格、溢出与PDF交付；技术运行与真实宿主/创作验收分别记录。

## main开发候选补充

新增[main工作流与参数](skills/designcraft-scenario-playbooks/references/main-workflows.md)：SVG导入并交付可编辑PPTX、Flex模块布局、60个新增方法与119处参数变化的索引。来源为固定main实际目录；SVG/PPTX已通过Windows main专项39008681404；Flex仍待执行，不等于稳定版支持或宿主验收通过。
