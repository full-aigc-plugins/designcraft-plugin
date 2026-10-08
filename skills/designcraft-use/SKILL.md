---
name: designcraft-use
description: 用户要从目标、大纲或素材出发完成页面设计、完整排版或出版交付时使用，包括尚未提供大纲、需要先澄清的通用请求；这是默认入口。首次使用从固定摘要制品安装原生 CLI，保留源素材与可编辑工程。
license: Apache-2.0
---

# 页面排版与出版

候选实现，尚未完成实际宿主、原生安装与创作验收。仅 macOS arm64、Python 3.11+。

## 路由范围

这是用户提出 DesignCraft 页面设计、完整排版或出版目标时的唯一默认入口。即使用户只提到“两页”“可编辑文档”或尚未提交大纲，只要目标仍需内容/版面规划，就先在本入口澄清内容、页面、素材、修改范围和交付物；不能因提到新建工程就直接路由到 document。只有用户明确只要一个工程生命周期原生操作（例如打开现有工程另存，或在已确定方案后新建空白工程）时，才交给 `designcraft-cli-document`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-cli-document`）。局部版面调整交给 `designcraft-cli-layout`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-cli-layout`），已有工程的明确导出交给 `designcraft-cli-export`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-cli-export`）。用户明确只问原生命令或安装诊断时，交给对应原子技能；无关请求不触发本技能。执行可能安装运行时、修改工程并写出产物；只有在授权路径内继续。未知执行结果先核对持久工程和回执，不自动重放。完成以保存并重开工程、核对导出及逐页审阅为准，命令成功不代表验收完成。

## When to Use

用户要从目标、大纲或素材出发制作或修订页面时使用本入口；输入缺失时先问具体缺项，不跳到工程创建技能。若需求只要求一个已确定方案上的原生生命周期动作、单独安装诊断、命令查询、既有对象的局部操作或已有工程导出，才转交对应原子技能。

## 不适用范围与安全边界

- 无关 DesignCraft 的问题不触发本技能；不要把规划建议当作用户授权。
- 不从示例或研究源码推测固定 CLI 参数；执行前使用当前固定版本的原生目录。
- 脚本以当前用户权限读写本地文件。登记输入和摘要只能发现部分漂移，不能充当沙箱、回滚或权限隔离。
- 缺少依赖安装授权时仅做离线检查；不自动下载、安装、登录或升级。

## 工作流

### Step 1：明确范围

记录素材、页数/尺寸、目标格式、输出位置、需保留的原件和允许修改范围；对同路径输出先核实覆盖授权。

### Step 2：检查前置

确认宿主加载、固定运行时状态和共享回执契约。缺少安装授权时保持未就绪，不以离线目录或研究源码代替真实能力。

### Step 3：查询并计划

用本技能入口读取当前 CLI 命令目录和参数，再形成单会话计划；涉及既有工程时登记原件并使用工作副本。

### Step 4：执行并留证

只在授权范围内执行计划，记录回执、输入/资源摘要和新建产物；超时、中断或身份不完整时保留 UNKNOWN，不重放写入。

### Step 5：独立验收

保存并在新会话重开工程，核对页数、文本、链接素材和导出文件，再逐页审阅。任何一项未验证都继续标为待验收。

## Rules（执行约束）

- 原生目录查询可以离线；实际执行必须使用当前固定 CLI 的真实目录。
- 运行时、技能快照、宿主发现、模型路由、原生命令、工程重开和视觉审阅是独立门禁。
- 保存命令或导出命令退出为零，只证明进程结果，不证明内容或视觉质量通过。

## Gotchas（常见误区）

1. **`SKILL_DIR` 必须来自实际加载路径：** 不猜测兄弟技能目录或开发工作区路径。
2. **离线 catalog 不能用于执行：** 缺少真实 CLI 或真实命令参数时停止写入。
3. **UNKNOWN 不是普通失败：** 先读回执并核对已有工程，不能重跑可能已产生副作用的计划。
4. **摘要不代表隔离或回滚：** 输入未登记、参数中隐藏的路径及其副作用不受摘要保护。
5. **固定版本不代表宿主已验收：** 插件发现、模型选用和真实原生命令调用须分别留证。

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
`run <计划JSON> --output <新目录>` 重新读取真实目录，在一个原生会话中执行整个计划，保留执行回执；零退出状态仍标记 REVIEW_REQUIRED。`receipt <旧回执路径>` 仅离线读取历史回执；`recover <原回执路径> --checkpoint-receipt <重开回执>` 只核对保存工程并输出安全恢复计划，不安装、不自动执行，也不重放原计划。
原生源工程用 DesignCraft `--source`，照片库用 LightCraft `--library` 与重复 `--import`，PDF 文件根用 PrintCraft `--root`。
超时或中断保留 UNKNOWN 回执，不自动重放可能已写入的命令。

对包含已完成 `file.saveAs` 的部分失败回执，先用一个新计划执行 `file.open` 与 `document.inspect`，并用 `--input` 登记保存工程；之后 `commands.py recover <原回执> --checkpoint-receipt <重开回执>` 只核对身份并生成未启动后缀。机器结果按 `designcraft-checkpoint-recovery/v1` 输出 `originalRunId`、`reopenRunId`、保存工程 SHA 和剩余计划，供插件 Harness 交叉核验。只有返回 `RECOVERY_READY` 才可人工审阅后显式提交为新计划；已完成前缀和可能有副作用的失败步永不重放。旧对象的 `step:N` 跨会话引用会被拒绝自动恢复，必须先按新 inspection 的对象身份人工重绑。检查点缺失、摘要漂移、未知状态或回执缺字段时只返回诊断。

## 场景示例

本技能的多页排版编排成功路径及无关请求/未知结果的拒绝与恢复边界见 [场景示例](examples/workflow-cases.md)、[从提纲到可编辑工程](examples/multi-page-plan.md)、[既有工程局部修订](examples/revise-existing.md)和[UNKNOWN 恢复](examples/unknown-recovery.md)。示例只说明流程，不证明固定原生 CLI 已验收。



输入登记范围、工作副本策略、执行前后摘要与回执字段说明见本技能 [执行与回执参考](references/execution-and-receipts.md)。摘要仅用于漂移检测，不构成沙箱或回滚证明。
