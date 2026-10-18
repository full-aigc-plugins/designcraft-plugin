# DesignCraft Use

## 插件市场导航

本插件所属分类：**AIGC 内容创作**。

| 分类 | 插件市场入口 | 用途 |
| --- | --- | --- |
| 全栈开发 | [Full Stack Plugins](https://github.com/partme-ai/full-stack-plugins) | 架构与 UI 设计、代码理解、质量检查、代码审查、流程治理与服务器运维 |
| AIGC 内容创作 | [Full AIGC Plugins](https://github.com/partme-ai/full-aigc-plugins) | 图像、视频、音频、音乐、3D 与多模态内容创作 |

![DesignCraft Use——页面排版与出版](assets/official-logo.png)

> 把宣传册、目录、简报、海报与长文档排成可编辑的 `.designcraft` 工程，经过印前检查后再导出 PDF、IDML、EPUB 或图片。

[![版本](https://img.shields.io/badge/release-0.1.0--dev.20261019.1-1A73E8)](.codex-plugin/plugin.json)
[![技能数](https://img.shields.io/badge/skills-16-00A67E)](#技能)
[![MCP server](https://img.shields.io/badge/MCP%20server-1-00A67E)](#mcp-工具)
[![许可证](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

[English](README.md) | [简体中文](README.zh-CN.md) · [安装](#安装) · [快速开始](#快速开始) · [可完成的工作](#可完成的工作) · [技能](#技能) · [故障排查](#故障排查)

## 项目定位

DesignCraft Use 把内容与素材排成可编辑的版式工程，而不是压平的示意图。它规划页面、通过一个小型命令目录驱动固定的原生排版 CLI，让文字框、图像框与链接素材保持可寻址，并且只有在工程保存、在新会话中重新打开并逐页审阅之后，才把交付视为完成。

它仍是开发候选：静态包校验与 CI 通过，而 `support-matrix.json` 与 `project-status.json` 中的原生安装、目标平台验收、当前宿主发现与创作验收都仍是 `NOT_RUN`。

| 16 个技能 | 1 个编辑器服务 | 4 种导出格式 | macOS arm64 |
|:---:|:---:|:---:|:---:|
| 6 个原子技能 + 10 个本地技能 | `designcraft-editor` | PDF、IDML、EPUB、图片 | 唯一已验证平台 |

## 状态与版本

`0.1.0-dev.20261019.1` · 开发预览 · `docs/verification/release-candidate.json` → `releaseStatus: BLOCKED`、`installableDevelopmentCandidate: true`。

## 安装

### 前置条件

- 原生执行需要 macOS arm64，且 `PATH` 上有 Python 3.11 或更新版本。
- 需要内嵌编辑器 MCP 服务时，需要 Node.js 24 或更新版本。
- 市场安装是自包含的。Git 检出没有 `ui/dist/`，需先用 `node build.mjs` 与 `python3 build-source.py` 构建（要求 Rust `wasm32` target 与匹配的 `wasm-bindgen`；构建脚本不会自动安装工具）。
- 原生 CLI 在首次获得授权的使用时下载到用户数据目录；不需要 `sudo`，不修改 `PATH`。

### 安装插件

```bash
codex plugin marketplace add full-aigc-plugins/designcraft-plugin
codex plugin add designcraft@full-aigc-plugins-designcraft
```

`docs/verification/release-candidate.json` 同时记录 `installableDevelopmentCandidate: true` 与 `releaseStatus: BLOCKED`；生产晋级与所有宿主内嵌 UI 验收均不作承诺。

仓库带有 Codex（`.codex-plugin/`）、Claude Code（`.claude-plugin/`）、ZCode（`.zcode-plugin/`）与 Kimi（`kimi.plugin.json`）清单，但本候选的宿主发现仍记录为 `NOT_RUN`。

## 快速开始

```bash
: "${SKILL_DIR:?请设为已加载 designcraft-use 的 SKILL.md 所在目录}"
python3 -I -B "$SKILL_DIR/scripts/cli.py" -- commands
```

直接描述你要的成品，例如“用这些图片排一份两页产品宣传册并导出可印刷 PDF”。入口技能会先澄清页数、尺寸、素材、输出位置与可修改范围，再开始规划。

```mermaid
flowchart LR
    A[目标、提纲、素材] --> B[designcraft-use 澄清范围]
    B --> C[读取真实命令目录]
    C --> D[在工作副本上生成版式计划]
    D --> E[保存并重开 .designcraft]
    E --> F[逐页审阅、导出、记录格式损失]
```

仓库自检（不需要原生运行时）：

```bash
python3 -I -B scripts/validate_package.py
python3 -I -B -m unittest discover -s tests
```

## 可完成的工作

| 工作流 | 内置路径 | 可验证输出 |
|:---|:---|:---|
| 多页宣传册 | `designcraft-brochure` → `designcraft-cli-layout` | 重开后核对页数、文字与链接图片的工程 |
| 版式统一的商品目录 | `designcraft-catalog` | 商品框与字体一致的目录工程 |
| 简报或多栏刊物 | `designcraft-newsletter` | 重开后核对分栏流向的多栏文档 |
| 信息层级清晰的海报 | `designcraft-poster-layout` | 大幅面工程与已审阅的导出 |
| 含目录与页码的长文档 | `designcraft-long-document` | 重开后可核对章节、目录与页码 |
| 印前检查 | `designcraft-print-preflight` | 交付前记录的字体、图像、出血与导出检查 |
| 从 CSV 批量生成胸牌 | `designcraft-data-merge-badges` | 逐条预览，以及字段完整的重开工程 |
| 在内嵌编辑器中修改 | `designcraft-editor` MCP 工具 | 保存后在新会话重开并检查的工程 |

## 技能

| 技能 | 作用 |
|:---|:---|
| `designcraft-use` | 新建文档与页面设计的默认入口；输入缺失时先澄清 |
| `designcraft-cli` | 用真实参数查询并执行 designcraft 原生命令 |
| `designcraft-cli-setup` | 首次安装、摘要校验、版本检查与失败诊断 |
| `designcraft-cli-document` | 对已有工程执行单个生命周期动作：打开、保存、另存、重开 |
| `designcraft-cli-layout` | 查询并驱动文字框、图像框与页面布局 |
| `designcraft-cli-export` | 把工程导出为 PDF、图片、IDML 或 EPUB |
| `designcraft-brochure` | 从素材诊断到可编辑交付的多页宣传册 |
| `designcraft-catalog` | 大量商品记录下保持版式统一的目录 |
| `designcraft-newsletter` | 多栏简报与通讯 |
| `designcraft-poster-layout` | 活动海报的信息层级与大幅输出 |
| `designcraft-long-document` | 章节、目录、页码与统一样式 |
| `designcraft-print-preflight` | 印刷前的字体、图像、出血与导出检查 |
| `designcraft-data-merge-badges` | CSV 驱动的胸牌与姓名卡，逐条预览 |
| `designcraft-scenario-playbooks` | 覆盖 8 个排版场景的逐步手册，含真实参数 |
| `designcraft-editor` | 在宿主中打开真实编辑界面，一次会话内完成全部编辑 |
| `designcraft-harness` | 跨会话任务状态、UNKNOWN 核对与交付证据 |

## MCP 工具

`mcp.json` 只声明一个 stdio server：`designcraft-editor`，从插件根目录以 `node ui/bootstrap.mjs` 启动。它在宿主中打开内置引擎并代理编辑器工具集。

| 工具 | 用途 |
|:---|:---|
| `open_editor` | 为绝对路径 `workspace` 打开编辑器 |
| `open_browser_editor` | 返回可交给宿主内置浏览器的 `editorUrl` |
| `editor_status` | 报告页面是否已连接到当前 MCP 会话 |
| `open_document` | 打开已有工程文件 |
| `new_document` | 新建文档 |
| `inspect_document` | 读取文档与框结构 |
| `get_story` | 读取文字内容流 |
| `execute` | 执行编辑器命令 |
| `save_document` | 保存原生工程 |
| `render_page` | 渲染页面用于视觉检查 |

工具名取自 `designcraft-editor` 技能合同。`_editor_attach`、`_editor_poll` 等页面内部桥接调用属于面板自身，Agent 不应直接调用。

## 配置

| 变量 | 用途 |
|:---|:---|
| `CRAFT_WORKSPACE_ROOT` | 工具未注册时，用于 `node ui/dist/adapter.mjs --serve` 的工作区根目录 |
| `CRAFT_EDITOR_CACHE_DIR` | 已核验编辑器下载的绝对目录（默认 `~/.cache/full-aigc/editors`） |
| `CRAFT_EDITOR_UPDATE=off` | 固定使用内置编辑器，跳过更新检查 |

元数据请求 5 秒超时，归档下载 45 秒超时。下载失败、缺少摘要、摘要不符、归档异常、工具 schema 变化或缓存损坏都会回退到内置编辑器；`editor_status` 会返回 `source`、`version` 与回退 `reason`。

## 架构与安全

- stdio 承载 Agent 与插件之间的通信；仅监听回环地址（`127.0.0.1`）的 HTTP 桥接承载编辑器页面与同会话编辑通道，不提供远程 MCP 端点。
- 浏览器桥接使用随机令牌并校验 Host 与 Origin；工作区之外的路径被拒绝。浏览器手动导出写到工作区的 `craft-exports/` 并使用新文件名。
- 原生 CLI、技能快照、宿主发现、模型路由、原生命令、工程重开与视觉审阅是彼此独立的门禁。退出码为零只证明进程结束。
- 素材摘要只能发现漂移，不构成沙箱、回滚或权限边界。参见[架构](docs/architecture.md)、[编辑器接入](docs/editor-integration.md)与[场景技能](docs/scene-skills.md)。

## 故障排查

| 现象 | 处理方式 |
|:---|:---|
| 缺少 `ui/dist/adapter.mjs` | 先构建编辑器资源，或安装带 `dist/` 的发布包 |
| 编辑页始终未就绪 | 调用 `editor_status`；先处理页面错误再编辑。仅有文字结果不等于界面已打开 |
| 首次启动卡住或失败 | 首次运行需要网络或已核验缓存；离线使用时保留固定归档 |
| Windows 长路径报错 | 执行 `git config --global core.longpaths true`，或改用发布 ZIP |
| 宿主没有 MCP Apps 或内置浏览器 | 在宿主内置浏览器打开返回的 `editorUrl`（Codex 内置浏览器、DSH 右侧 Sidebar Browser、Kimi 浏览器面板）；只有宿主确实没有内置浏览器时才在外部打开，并明确这不是宿主内嵌验收 |
| 保存结果未知 | 先读回执与既有工程；不要重放可能已落盘的写入 |

## 升级

```bash
codex plugin marketplace upgrade full-aigc-plugins-designcraft
codex plugin add designcraft@full-aigc-plugins-designcraft
```

升级插件不会改写 `ui/dist/editor` 或既有锁文件；内置编辑器版本始终作为回退保留。

## 贡献与支持

行为变更从 [OpenSpec](openspec/changes/harden-designcraft-plugin-delivery/proposal.md) 开始。运行上文的包校验与单元测试，保持中英文文档同步，且没有真实交付证据不得勾选任务。问题反馈：<https://github.com/full-aigc-plugins/designcraft-plugin/issues>。

## 许可证

本仓库原创内容采用 [Apache-2.0](LICENSE)。上游图标的来源与许可证记录在 `assets/official-icon-source.json` 及相邻 LICENSE 文件中；内置编辑器保留其自身的上游许可证与 NOTICE。
