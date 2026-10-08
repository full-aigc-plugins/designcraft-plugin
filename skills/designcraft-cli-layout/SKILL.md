---
name: designcraft-cli-layout
description: 需要查询版面、文字框及图像框的参数并执行排版命令时使用；首次使用从固定摘要制品安装原生 CLI，保留源素材与可编辑工程。
license: Apache-2.0
---

# 版面与文字框

候选实现，尚未完成实际宿主、原生安装与创作验收。仅 macOS arm64、Python 3.11+。

## 路由范围

处理用户明确提出的版面查询与局部操作，包括文字/图像框、文字串联和素材放置；完整多页成果交给 `designcraft-use`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-use`），工程生命周期交给 `designcraft-cli-document`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-cli-document`），导出交给 `designcraft-cli-export`（Install: `npx skills add full-aigc-skills/designcraft-skills --skill designcraft-cli-export`）。布局命令可能修改工程，先确认对象、工作副本和修改范围；查询可先用离线目录，执行须使用真实原生目录。失败后保留已完成修改并检查受影响页面，不盲目重放。验收检查目标对象、文字流、溢出、链接素材和受影响页面。

## When to Use

用户只要求查看或局部修改现有版面对象时使用，包括文字/图像框、文字串联、素材放置和溢出检查。整稿目标交给 `designcraft-use`，文件保存/重开交给 `designcraft-cli-document`，交付格式交给 `designcraft-cli-export`。

## 不适用范围与安全边界

- 不负责超出明确页面/对象范围的全稿重排；先确认新增授权或交回通用编排入口。
- 不猜测对象 ID、命令参数、溢出状态或跨会话引用；从当前工程和真实命令目录重新发现。
- 脚本以当前用户权限访问工程与登记素材。摘要检查不提供沙箱或自动回滚。
- 新建工作副本和任何对象写入都须满足用户的路径与范围授权。

## 工作流

### Step 1：圈定对象与影响范围

记录工程、页面、对象类型、要修改的属性以及明确不应触及的区域。

### Step 2：读取当前工程状态

从当前会话重新发现对象和命令 schema；查询可以使用离线目录，写操作不能使用离线目录。

### Step 3：准备工作副本

登记并复制输入工程，确认素材链接与目标保存路径，避免对原件直接修改。

### Step 4：执行最小修改

只执行本次授权的对象操作；文字流、对象引用或参数不确定时先停下查询，不扩大范围。

### Step 5：检查受影响页面

复查目标对象、文字串联、溢出、裁切、素材链接和其他受影响页，保存后再报告真实验证状态。

## Rules（执行约束）

- 同一计划保持单原生会话；重开后必须重新发现对象，不沿用旧对象 ID。
- 批次级退出状态不能推出每个对象操作都成功。
- 对超范围变更、缺素材或未知结果停止写入，并保留已发生的修改记录。

## Gotchas（常见误区）

1. **查询结果可能已过期：** 计划执行前重新读取当前工程和原生目录。
2. **文字框溢出会影响后续页面：** 检查文字流及全部受影响页面。
3. **图片链接可用不等于图片内容正确：** 核对目标资源与预览。
4. **对象 ID 不保证跨会话有效：** 重新打开后重新发现目标对象。
5. **修改成功不证明版面可交付：** 另做导出和逐页审阅。

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
python3 -I -B "$SKILL_DIR/scripts/cli.py" -- describe frame.create
```

交付原生 .designcraft 工程、收集素材与字体许可清单、逐页预览及适用的 PDF／IDML／EPUB。重新打开原生工程核对页数、文字和链接素材；交换格式损失单独记录。

CLI 参数按 argv 传递，不执行 shell。原生命令可能具有文件写入和网络行为；仅在任务授权范围内使用。
执行失败先核对工程与输出，未知结果不重放写入。同路径输出需先保护已有文件。
命令查询或零退出不等于交付通过：检查实际文件、保存重开、内容与修改后的结果，另记录创作审阅。
运行时与技能安装、宿主技能发现、模型自然语言选用是分别验收的门禁。

## 场景示例

本技能的局部排版成功路径及对象身份不明时的拒绝/恢复边界见 [场景示例](examples/workflow-cases.md)、[文字串联](examples/story-flow.md)、[图像放置](examples/image-placement.md)和[溢出处理](examples/overflow-review.md)。示例只说明流程，不证明固定原生 CLI 已验收。



对象发现、影响页检查和输入/回执证据边界见本技能 [版面审阅参考](references/layout-review.md)。摘要检查不代表沙箱或回滚。

## 执行前必读

在执行命令计划、检查点恢复或交付验证前，必须读取本技能的 [执行与验收细节](references/execution-details.md)，按其中的输入保全、UNKNOWN、回执与格式验证要求操作。摘要只能检测变化，不能隔离或回滚写入；未知结果不得自动重放。
