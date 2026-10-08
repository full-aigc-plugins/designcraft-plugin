---
name: designcraft-cli-export
description: 需要将已有排版工程输出为 PDF、图片、IDML 或 EPUB 时使用；首次使用从固定摘要制品安装原生 CLI，保留源素材与可编辑工程。
license: Apache-2.0
---

# 排版导出

候选实现，尚未完成实际宿主、原生安装与创作验收。仅 macOS arm64、Python 3.11+。

## 路由范围

仅导出已有 DesignCraft 工程到用户指定格式和位置；新建或整体修订交给 `designcraft-use`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-use`），工程重新打开与保存交给 `designcraft-cli-document`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-cli-document`）。导出会创建文件，开始前确认源工程、目标格式、输出位置及覆盖范围。失败或 UNKNOWN 时检查已经生成的文件，不自动重放导出。验收核对文件身份、格式、页数/尺寸和实际内容；PDF、IDML、EPUB 与图片的格式损失分别记录，零退出不等于视觉或可编辑性验收。

## When to Use

当用户已提供可打开的 DesignCraft 工程，并明确要求输出 PDF、图片、IDML 或 EPUB 时使用。工程修订、重新打开检查与全稿排版请求分别转交相应技能。

## 不适用范围与安全边界

- 不把研究源码或本地开发分支支持的格式推定为固定 CLI 支持；以真实目录为准。
- 不覆盖既有输出，除非用户授权；失败后先检查是否已有有效文件。
- 以当前用户权限读写源工程和目标目录。输入摘要不能防止参数内未登记路径产生的副作用。
- 导出格式转换可能丢失编辑能力或语义；说明经验证的损失，未知项保持未知。

## 工作流

### Step 1：核对源工程

确认工程路径、当前摘要、页面数、目标格式以及是否需要先另存工作副本。

### Step 2：查询格式能力

从固定 CLI 的真实命令目录确认支持的导出操作和参数，不用研究源码或离线目录执行。

### Step 3：确认输出范围

记录目标路径、文件类型、覆盖授权、预期页数/尺寸和用户要求保留的内容。

### Step 4：执行并核验文件

导出后检查文件存在、摘要、格式及页数/尺寸；失败或 UNKNOWN 时读取回执，不自动重放。

### Step 5：说明损失并审阅

检查关键文本、链接素材与视觉结果；分别记录该格式的实测损失和未验证项。PDF/X 内部检查不等于外部认证。

## Rules（执行约束）

- 导出存在文件不表示页内容正确；依据格式做内容检查。
- 导出成功不证明源工程保存或重开通过。
- 只报告被当前产物摘要绑定的验证，不沿用旧导出审阅。

## Gotchas（常见误区）

1. **旧导出记录可能过期：** 源工程或输入变化后重新验证。
2. **一个格式的成功不证明其他格式可用：** 按格式分别验收。
3. **零退出不证明文件完整：** 核对字节数、摘要及预期内容。
4. **图片预览尺寸不是文档页数：** 依照导出类型检查相应维度。
5. **内部 PDF/X 检查不是认证：** 不对外声称通过认证。

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
python3 -I -B "$SKILL_DIR/scripts/cli.py" -- run --in /absolute/path/input.designcraft --export /absolute/path/output.pdf
```

交付原生 .designcraft 工程、收集素材与字体许可清单、逐页预览及适用的 PDF／IDML／EPUB。重新打开原生工程核对页数、文字和链接素材；交换格式损失单独记录。

CLI 参数按 argv 传递，不执行 shell。原生命令可能具有文件写入和网络行为；仅在任务授权范围内使用。
执行失败先核对工程与输出，未知结果不重放写入。同路径输出需先保护已有文件。
命令查询或零退出不等于交付通过：检查实际文件、保存重开、内容与修改后的结果，另记录创作审阅。
运行时与技能安装、宿主技能发现、模型自然语言选用是分别验收的门禁。

结构化产物清单字段、重开核验记录和状态含义见本技能的 `references/artifact-manifest.md`。使用 `scripts/artifact_manifest.py` 校验清单与本地文件；`NOT_RUN` 表示只核对了产物身份，不能作为 AV-02 重开通过证据，也不能标记任务完成。

需要单独核对导出文件的可识别结构时，使用 `scripts/format_probe.py --file <绝对路径>`；格式检查覆盖范围及 `PASS`/`PARTIAL` 边界见 `references/format-checks.md`。探针结果不是视觉、内容、可编辑性、损失或原生支持验收。

逐页预览审阅记录和固定 rubric 见 `references/page-review.md`。仅在 AV-02 的工程重开通过后，使用 `scripts/page_review.py` 校验逐页预览摘要、审阅来源和独立结论；校验器绑定记录，不代替人或视觉模型实际审阅页面。

页/对象/Story 局部修订、受影响页面闭包和修订后导出身份重验见 `references/revision-evidence.md`；`scripts/revision_evidence.py` 校验两轮 AV-02/AV-03 证据、规范化对象快照和授权声明的一致性。它不执行原生编辑，也不证明这些声明真实发生；真实 CLI 目录与创作验收仍需单独完成。

## 命令目录、参数与单会话计划

`scripts/commands.py list` 从实际固定CLI读取完整原生目录，`describe <命令ID>` 返回参数与分类。
显式 `--catalog <原生JSON目录文件>` 支持离线查询与检查，执行禁止使用离线目录。
计划格式为 `{"domain":"designcraft","steps":[{"command":"实际命令ID","params":{}}]}`。
`check <计划JSON>` 检查结构、命令存在及原生 schema 的受支持约束；纯文本参数只展示原文，参数类型和状态前置条件由原生程序判断，不能将检查通过当成执行通过。
`run <计划JSON> --output <新目录>` 重新读取真实目录，在一个原生会话中执行整个计划，保留执行回执；零退出状态仍标记 REVIEW_REQUIRED。
原生源工程用 DesignCraft `--source`，照片库用 LightCraft `--library` 与重复 `--import`，PDF 文件根用 PrintCraft `--root`。
超时或中断保留 UNKNOWN 回执，不自动重放可能已写入的命令。

## 场景示例

本技能的已有工程导出成功路径及警告/未知结果的恢复边界见 [场景示例](examples/workflow-cases.md)、[PDF 检查](examples/pdf-review.md)、[IDML 往返](examples/idml-roundtrip.md)和[未知导出结果](examples/unknown-export.md)。示例只说明流程，不证明固定原生 CLI 已验收。



## 输入保全与执行回执

计划执行可重复传入 `--input <需保全的文件或目录>`，登记输入摘要；`--source` 与 `--import` 输入自动登记。DesignCraft `--source` 会复制到新任务目录的 `working-copy/<源名称>`，原生命令只接收副本路径，不直接编辑原件。
目录按普通文件登记，拒绝缺失文件和符号链接；每个目录最多登记100000条目。未显式登记、且只藏在命令参数里的路径不在此保全检查内；这不是文件系统沙箱。
安装／目录查询后、编辑开始前重新核对输入与当前技能执行资源；漂移时拒绝编辑。
回执保存当前计划、命令目录、输入、运行时锁及技能资源摘要，并记录工作副本执行前后的文件摘要；超时保存可获得的部分日志并标记UNKNOWN，不自动重放。工作副本的摘要用于追踪改动，不代表写入范围沙箱。
原生零退出却改动登记输入会标记INPUT_CHANGED_REVIEW_REQUIRED并返回失败；这是事后检测，不会回滚已经发生的写入。需要修改原图或源工程时应先另存可编辑副本，再明确登记需保持的原始输入。

格式可验证属性和损失边界见本技能 [格式检查参考](references/format-checks.md)。
