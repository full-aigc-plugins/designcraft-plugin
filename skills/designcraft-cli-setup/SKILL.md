---
name: designcraft-cli-setup
description: 首次使用 designcraft、缺少运行时或需要检查安装失败时使用；首次使用从固定摘要制品安装原生 CLI，保留源素材与可编辑工程。
license: Apache-2.0
---

# 固定 CLI 安装

候选实现，尚未完成实际宿主、原生安装与创作验收。仅 macOS arm64、Python 3.11+。

## 路由范围

只在用户要求首次安装、检查安装状态或排查固定 CLI 安装失败时使用。普通排版工作交给 `designcraft-use`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-use`）；查询原生命令交给 `designcraft-cli`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-cli`）。安装会联网获取固定制品并写入用户选择的 runtime-home，必须先取得覆盖该操作的授权；只检查时不触发安装。失败保留日志和已有文件，不自动重试写入。验收依据是固定摘要、版本检查和实际命令发现记录；安装成功不代表宿主已发现技能或创作流程通过。

## When to Use

用户明确要求检查 DesignCraft 固定 CLI 是否安装、首次安装该运行时或排查安装失败时使用。普通查询交给 `designcraft-cli`，普通编辑请求交给 `designcraft-use`。

## 不适用范围与安全边界

- 只读检查不等于安装许可；联网下载和安装必须有针对本次依赖的明确授权。
- 不使用 sudo、不修改 PATH、不登录账号、不升级到锁定版本以外的制品。
- 目标 runtime-home 必须由用户选择或遵循已批准的默认目录，绝不覆盖无法核验的旧文件。
- 运行时安装与宿主发现、模型路由、原生创作分别验收。

## 工作流

### Step 1：确认平台和目标目录

记录 macOS 架构、Python 版本和隔离 runtime-home；不在不支持平台上尝试安装。

### Step 2：先做只读检查

查看锁文件、目标目录和已安装身份；已有制品必须同时符合摘要、版本和安装回执。

### Step 3：核实安装授权

安装前明确核对用户是否授权本次网络下载和文件写入。没有授权时只报告依赖缺口。

### Step 4：校验并安装锁定制品

只取锁定 URL 对应制品，校验归档与二进制摘要；安装失败保留错误分类，不覆盖异常目录、不自动重试。

### Step 5：分层验证

核对安装回执、版本输出及命令发现记录；单独标记插件发现、模型路由和创作验收状态。

## Rules（执行约束）

- 本技能不会把用户的排版目标解释为下载运行时的授权。
- 摘要或安装回执不匹配时保留目录供诊断，不静默重装。
- 安装成功只证明锁定二进制的本地身份检查，不证明宿主或业务能力。

## Gotchas（常见误区）

1. **平台不符时不尝试兼容安装：** 报告当前支持范围和缺失证据。
2. **下载链接可用不等于制品可信：** 每次校验归档摘要与二进制摘要。
3. **目录已存在不表示安装通过：** 核对安装收据与版本输出。
4. **安装失败后不自动重试覆盖：** 保存日志和目录状态供人工核对。
5. **安装通过不代表 Codex 已加载：** 宿主发现需要单独验证。

## 首次使用

把 `SKILL_DIR` 设置为宿主实际加载的本 SKILL.md 所在绝对目录。
技能可独立安装到项目 `.agents/skills`、用户技能目录或插件缓存；不猜测兄弟目录，不修改技能文件。
用户请求已授权必要依赖时，公开 cli.py 自动校验并安装固定原生版本到用户数据目录；不使用 sudo，不修改 PATH。

```bash
: "${SKILL_DIR:?设置为本技能真实加载目录}"
python3 -I -B "$SKILL_DIR/scripts/cli.py" -- commands
```

需要只检查安装时：

```bash
python3 -I -B "$SKILL_DIR/scripts/bootstrap.py"
python3 -I -B "$SKILL_DIR/scripts/cli.py" -- --version
```

`--runtime-home` 或 CRAFT_RUNTIME_HOME 指定隔离运行时目录，放在 `--` 之前。
`--archive` 指向已有固定 ZIP，仍校验归档与二进制摘要。
安装失败返回 dependencySetup，不自动重试编辑或渲染；校验失败保留已有目录。
当前锁仅固定原生 CLI，发布快照与宿主自动发现仍须另行验证。

## 当前场景

先记录用户素材、目标、输出位置、尺寸／页码／格式及修改边界。
从原生目录查询真实参数，确认命令后执行；不虚构命令、不把本地源码的新接口当成固定制品已支持。
以下示例中的素材路径与输出位置必须替换成当前任务实际授权路径。

```bash
python3 -I -B "$SKILL_DIR/scripts/cli.py" -- --version
```

交付原生 .designcraft 工程、收集素材与字体许可清单、逐页预览及适用的 PDF／IDML／EPUB。重新打开原生工程核对页数、文字和链接素材；交换格式损失单独记录。

CLI 参数按 argv 传递，不执行 shell。原生命令可能具有文件写入和网络行为；仅在任务授权范围内使用。
执行失败先核对工程与输出，未知结果不重放写入。同路径输出需先保护已有文件。
命令查询或零退出不等于交付通过：检查实际文件、保存重开、内容与修改后的结果，另记录创作审阅。
运行时与技能安装、宿主技能发现、模型自然语言选用是分别验收的门禁。

## 场景示例

本技能的安装后验证成功路径及缺少授权/安装失败时的拒绝与恢复边界见 [场景示例](examples/workflow-cases.md)、[只读检查](examples/inspect-only.md)、[授权安装](examples/authorized-install.md)和[校验失败](examples/rejected-artifact.md)。示例只说明流程，不证明固定原生 CLI 已验收。

## 执行前必读

在执行命令计划、检查点恢复或交付验证前，必须读取本技能的 [执行与验收细节](references/execution-details.md)，按其中的输入保全、UNKNOWN、回执与格式验证要求操作。摘要只能检测变化，不能隔离或回滚写入；未知结果不得自动重放。
