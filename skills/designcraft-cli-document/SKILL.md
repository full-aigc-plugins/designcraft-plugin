---
name: designcraft-cli-document
description: 用户已确定内容和版式方案，只要求单独新建空白工程、打开、保存、另存或重开核验时使用；从大纲或素材制作成品时走 designcraft-use。首次使用从固定摘要制品安装原生 CLI，保留源素材与可编辑工程。
license: Apache-2.0
---

# 排版工程管理

候选实现，尚未完成实际宿主、原生安装与创作验收。仅 macOS arm64、Python 3.11+。

## 路由范围

仅处理用户明确只要求一个已确定方案上的工程生命周期操作：新建空白工程、打开、另存、保存或重新打开核验。若用户从大纲、文字或素材开始制作一份或多页成品，即使尚缺输入、只说“创建可编辑文档”或目标需要页面规划，交给 `designcraft-use`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-use`），不得仅因出现“新建”或“可编辑”触发本技能。版面对象调整交给 `designcraft-cli-layout`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-cli-layout`），已有工程导出交给 `designcraft-cli-export`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-cli-export`）。新建或保存会写入指定位置；开始前确认源工程、工作副本、输出路径和覆盖授权。遇到失败或 UNKNOWN 时检查现有工程与回执，不重做可能已完成的创建或保存。以目标文件存在、工程能重新打开且页面和链接素材符合约定为验收。

## When to Use

当用户单独要求对一个已经确定方案的工程执行空白工程创建、打开、另存、保存或重开检查时使用。若还要从大纲、内容或素材规划页面与成品，交给 `designcraft-use`；只改对象或导出文件时转交对应技能。

## 不适用范围与安全边界

- 不负责文字框、图像框、文字串联等局部排版；转交 `designcraft-cli-layout`。
- 不负责导出与格式损失分析；转交 `designcraft-cli-export`。
- 脚本以当前用户权限读写文件。工作副本和输入摘要用于保全与发现漂移，不提供沙箱、回滚或隔离。
- 无安装授权时不下载或安装运行时；任何失败都不能自动重试保存或创建。

## 工作流

### Step 1：登记工程与路径

确认新建或既有工程、原件位置、工作副本位置、保存目标及覆盖范围。

### Step 2：检查前置

确认固定 CLI 和工程格式可用；只使用真实 CLI 已发现的打开、保存能力，不依据研究源码推测。

### Step 3：准备编辑对象

先复制或登记要保全的输入，将命令绑定到任务工程；保存前核实目标路径不会覆盖未授权文件。

### Step 4：保存并重开

记录保存结果后启动独立新会话重新打开目标工程；超时或 UNKNOWN 时先检查旧回执和文件，不重复保存。

### Step 5：核对结果

确认工程文件身份、页数、页面内容与链接素材符合用户约定；将缺少原生重开证据的结果标为待验收。

## Rules（执行约束）

- 文件存在不证明它能被 DesignCraft 重新打开；使用独立会话核验。
- 创建和保存属于写入；确认授权的输出位置和覆盖边界后再执行。
- 目录、模型路由、原生调用、工程重开是分层证据，互不替代。

## Gotchas（常见误区）

1. **不要对未知保存结果再保存一次：** 先看回执和目标文件，可能已产生写入。
2. **不要把源工程当工作副本：** 使用登记输入并复制到任务目录。
3. **不要沿用旧会话状态作为重开证明：** 必须新建会话检查。
4. **不要静默覆盖：** 同路径写入需要明确授权并留存原件。
5. **运行时安装成功不等于宿主或工程验收通过：** 分别记录状态。

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
python3 -I -B "$SKILL_DIR/scripts/cli.py" -- run --sample --export /absolute/path/sample.designcraft
```

交付原生 .designcraft 工程、收集素材与字体许可清单、逐页预览及适用的 PDF／IDML／EPUB。重新打开原生工程核对页数、文字和链接素材；交换格式损失单独记录。

CLI 参数按 argv 传递，不执行 shell。原生命令可能具有文件写入和网络行为；仅在任务授权范围内使用。
执行失败先核对工程与输出，未知结果不重放写入。同路径输出需先保护已有文件。
命令查询或零退出不等于交付通过：检查实际文件、保存重开、内容与修改后的结果，另记录创作审阅。
运行时与技能安装、宿主技能发现、模型自然语言选用是分别验收的门禁。

## 命令目录、参数与单会话计划

`scripts/commands.py list` 从实际固定CLI读取完整原生目录，`describe <命令ID>` 返回参数与分类。
显式 `--catalog <原生JSON目录文件>` 支持离线查询与检查，执行禁止使用离线目录。
计划格式为 `{"domain":"designcraft","steps":[{"command":"实际命令ID","params":{}}]}`。
`check <计划JSON>` 检查结构、命令存在及原生 schema 的受支持约束；纯文本参数只展示原文，参数类型和状态前置条件由原生程序判断，不能将检查通过当成执行通过。
`run <计划JSON> --output <新目录>` 重新读取真实目录，在一个原生会话中执行整个计划，保留执行回执；零退出状态仍标记 REVIEW_REQUIRED。
原生源工程用 DesignCraft `--source`，照片库用 LightCraft `--library` 与重复 `--import`，PDF 文件根用 PrintCraft `--root`。
超时或中断保留 UNKNOWN 回执，不自动重放可能已写入的命令。

## 场景示例

本技能的新建/重开成功路径以及保存结果未知时的恢复边界见 [场景示例](examples/workflow-cases.md)、[新建工作副本](examples/new-working-copy.md)、[既有工程重开](examples/reopen-existing.md)和[保存结果未知](examples/unknown-save.md)。这些场景只说明判断流程，不证明固定原生 CLI 已验收。



输入登记、工程副本和执行回执字段的细节见本技能 [工程生命周期参考](references/project-lifecycle.md)。这些摘要仅提供身份与漂移证据，不代表写入隔离或回滚。
