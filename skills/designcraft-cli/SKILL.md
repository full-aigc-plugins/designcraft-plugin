---
name: designcraft-cli
description: 需要查询或执行 designcraft 原生命令及参数时使用；首次使用从固定摘要制品安装原生 CLI，保留源素材与可编辑工程。
license: Apache-2.0
---

# 完整原生 CLI

候选实现，尚未完成实际宿主、原生安装与创作验收。仅 macOS arm64、Python 3.11+。

## 路由范围

仅在用户明确要求查询原生命令、查看参数或检查/执行命令计划时使用。面向完整排版成果的请求交给 `designcraft-use`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-use`）；单独安装诊断交给 `designcraft-cli-setup`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-cli-setup`）。查询命令目录和描述参数不修改工程；`run` 可能安装固定运行时并编辑文件，必须先核对用户授权的输入、输出和范围。失败或 UNKNOWN 时保留回执，检查工程后再决定后续动作；成功标准是对应计划完成且产物经独立检查，不以退出码作为业务验收。

## When to Use

用户明确要求查看 DesignCraft 原生命令、查询参数、检查计划或执行单项计划时使用。无明确命令问题的完整出版目标交给 `designcraft-use`。

## 不适用范围与安全边界

- 不使用研究源码、缓存或离线 catalog 执行原生写操作；写入必须使用固定版本的真实命令目录。
- `run` 可安装运行时并修改本地文件，必须分别核实安装授权、输入、输出和计划范围。
- 脚本以当前用户权限运行；`--input` 未登记的路径不在摘要保护范围内。
- 不把计划结构校验、进程退出码或回执存在说成业务完成。

## 工作流

### Step 1：分类请求

区分只读查询与可能安装/写入的命令；完整文档目标转交 use，纯安装问题转交 setup。

### Step 2：确定运行时与目录

只读核对固定 CLI 版本和当前命令目录；目录缺失或版本不符时阻止依赖该能力的写操作。

### Step 3：检查计划

用真实 schema 检查命令与参数，并登记需保全的输入。离线 catalog 仅用于查询或静态检查。

### Step 4：受控执行

核实输出路径和用户范围授权后运行一次计划，保存原始 stdout/stderr、回执与身份摘要。

### Step 5：核对副作用

按产物契约检查文件和工程重开状态；未知或部分失败时不重放命令，列明缺失证据。

## Rules（执行约束）

- CLI / Python 参数通过 argv 传递，不拼接或执行 shell 命令。
- 每个多步计划保持单原生会话，但整体退出码不能证明每个步骤成功。
- 执行前后都核对输入和技能资源身份；摘要不能替代沙箱或进程隔离。

## Gotchas（常见误区）

1. **真实目录缺失不等于命令不存在：** 可以只读报告缺少证据，不能猜测后写入。
2. **零退出可能包含业务警告：** 检查原始问题和产物内容。
3. **UNKNOWN 不能自动重试：** 先核对进程、回执和已有副作用。
4. **单会话不能证明步骤级完成：** 无逐步回执时保留批次级状态。
5. **安装成功不是模型或业务验收：** 分层报告各项状态。

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
python3 -I -B "$SKILL_DIR/scripts/cli.py" -- commands
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

本技能的目录查询成功路径和不支持命令时的拒绝/恢复边界见 [场景示例](examples/workflow-cases.md)、[只读查询](examples/catalog-read.md)、[计划执行](examples/authorized-run.md)和[未知结果](examples/unknown-result.md)。示例只说明流程，不证明固定原生 CLI 已验收。



## 输入保全与执行回执

计划执行可重复传入 `--input <需保全的文件或目录>`，登记输入摘要；`--source` 与 `--import` 输入自动登记。DesignCraft `--source` 会复制到新任务目录的 `working-copy/<源名称>`，原生命令只接收副本路径，不直接编辑原件。
目录按普通文件登记，拒绝缺失文件和符号链接；每个目录最多登记100000条目。未显式登记、且只藏在命令参数里的路径不在此保全检查内；这不是文件系统沙箱。
安装／目录查询后、编辑开始前重新核对输入与当前技能执行资源；漂移时拒绝编辑。
回执保存当前计划、命令目录、输入、运行时锁定身份及技能资源摘要，标记输出目录执行前不存在，并记录工作副本执行前后的文件摘要。多步计划保留有序 command/params 身份引用和批次级 stepResults；在固定 CLI 未提供逐步回执时，只标记“批次零退出待审阅”或 UNKNOWN，不推断某一步成功/失败。超时保存可获得的部分日志，不自动重放。运行时身份字段是锁定期望值，不证明二进制已安装或实际运行；工作副本的摘要用于追踪改动，不代表写入范围沙箱。
原生零退出却改动登记输入会标记INPUT_CHANGED_REVIEW_REQUIRED并返回失败；这是事后检测，不会回滚已经发生的写入。需要修改原图或源工程时应先另存可编辑副本，再明确登记需保持的原始输入。

计划编排、执行状态和回执的字段解释见本技能 [命令计划参考](references/command-plans-and-receipts.md)。
