# DesignCraft Use

# designcraft plugin — local development project

Six standalone skills are included from `designcraft-skills`, with local snapshot checksums. Unpublished. Host discovery and nine read-only model-routing cases passed on bundled Codex CLI 0.162.0-alpha.2 / gpt-6-astra / macOS arm64. Native execution, full domain workflows and creative acceptance remain open.

Validate: `python3 -I -B scripts/validate_package.py`. Tests: `python3 -I -B -m unittest discover -s tests`.

See [architecture](docs/architecture.md), the [support matrix](docs/support-matrix.zh-CN.md), the [snapshot migration guide](docs/snapshot-maintenance.zh-CN.md), and `project-status.json`. The [OpenSpec change](openspec/changes/harden-designcraft-plugin-delivery/proposal.md) is being implemented. This package has six source-owned skills and one local Harness skill; native, creative and release acceptance remain pending; host discovery and read-only routing passed only for the recorded combination. The development candidate is on the public [GitHub repository](https://github.com/full-aigc-plugins/designcraft-plugin) `main` branch; no version tag, GitHub Release or marketplace release exists.

## 场景技能开发候选

已增加 6 个领域场景技能及 1 个内嵌编辑器入口。详见 [场景目录](docs/scene-skills.md)。本地未发布候选，不代表全部场景的创作质量已验收。

## 内嵌编辑器候选

新增 MCP Apps 与宿主浏览器接入，详见 [配置与构建](docs/editor-integration.md)。`ui/dist/` 为本地生成物；首次分发须带齐生成物。

Plugin display name: **DesignCraft Use**. Official upstream icon provenance and licenses are included under `assets/official-icon-source.json` and adjacent LICENSE files.

源码增强候选采用 `ui/source.lock.json` 与 `ui/build-source.py`；兼容更新查询本插件自有 GitHub Releases，失败回退内置，原版 Web 不替换增强自动化运行时。当前会话保留；宿主安装验收另行记录。

## 排版场景操作手册

新增8条带具体方法、参数与结果检查的排版流程，见 [designcraft-scenario-playbooks](skills/designcraft-scenario-playbooks/SKILL.md)。包含原生脚本返回引用、活表格、溢出与PDF交付；技术运行与真实宿主/创作验收分别记录。

## main开发候选补充

新增[main工作流与参数](skills/designcraft-scenario-playbooks/references/main-workflows.md)：SVG导入并交付可编辑PPTX、Flex模块布局、60个新增方法与119处参数变化的索引。来源为固定main实际目录；新增工作流尚待专项执行，不等于稳定版支持或宿主验收通过。
