---
name: designcraft-harness
description: 当需要跨会话管理 DesignCraft 排版任务、核对 UNKNOWN 运行、绑定交付验收证据或安全推进局部修订时使用；它维护插件本地任务状态并通过技能源公开入口衔接技能，不自行安装或执行原生 CLI。
license: Apache-2.0
---

# DesignCraft 任务 Harness

Harness 管理任务身份、用户给出的修改范围、技能路由、技能源 runId、候选工程摘要、检查点和验收证据。外部六项技能由 `designcraft-skills` 维护；本技能只属于本插件。执行原生命令时交给技能源的公开 `commands.py`，不导入快照的私有 Python 函数。

## When to Use

用户要跨会话继续 DesignCraft 任务、核对 UNKNOWN、绑定当前候选的验收证据或执行已授权局部修订时使用。首次任务也由 Harness 建立任务身份和范围。

## 不适用范围与安全边界

- Harness 管理任务状态和门禁，不安装 CLI、不替用户授权、不取代技能源执行契约。
- `READY` 仅说明当前技术前置证据有效；它本身不是写入授权，也不是原生调用成功。
- 缺失检查点、回执不匹配或证据过期时保留原状态，只读诊断，不重放、不覆盖。
- Harness 的证据校验确认记录与身份绑定，不证明视觉判断或外部系统真实性。

## 工作流

### Step 1：记录目标和授权范围

创建任务时保存用户目标、明确的修改范围和任务 revision；只执行授权内的路径和页面。

### Step 2：核对只读 readiness

确认插件快照、来源、固定运行时、宿主发现及请求能力各有当前证据。任何缺项都阻止依赖该能力的写入。

### Step 3：经公开入口执行

在状态机允许时调用技能源公开入口，保存同一 runId 对应的回执和执行结果；不导入 vendored 私有实现。

### Step 4：处理 UNKNOWN 和恢复

进入 RECONCILING 后，默认只读核对 task/runId 与原回执。若技能源提供 `designcraft-checkpoint-recovery/v1`，可额外提供原计划、保存工程、重开计划/回执和恢复报告；Harness 独立核验原运行身份、步骤前缀/失败步/未启动后缀、工程 SHA、重开会话与 inspection。任一文件、摘要或步骤不匹配时只报告阻塞并保留原状态。

恢复分两步：先 `reconcile` 查看验证后的 `remainingPlan` 和摘要；人工审阅计划后，使用 `prepare-recovery` 提交同一摘要。它复用原 taskId，把精确后缀保存在用户任务目录并迁移到 PREPARED，不创建第二个任务。若任一原生回执未确认子进程后代已终止，`reconcile` 会显示 `process_descendants_termination_unverified` 风险；仅当实际输出列出此风险时，才通过单独的 `--acknowledge-risk` 明确确认。之后 `native run` 只能提交该后缀一次；调用前会重验持久化证据、计划和保存工程摘要；失败、中断或 UNKNOWN 均不允许重放。计划及来源回执只证明合同内部一致，不证明文件报告的签名真实性，也不构成新的写入授权。

### Step 5：验证候选并报告

只附加绑定当前候选的 AV 证据；工程重开、逐页审阅与导出分别检查。完成报告列出未运行层和下一动作。

## Rules（状态与证据规则）

- 每次更新携带最新 revision，状态损坏时保留文件并只读诊断。
- 当前候选变化会使旧证据失效，不能只复用人工 JSON 中的 PASS 字段。
- 一次局部修订完成后等待用户新的指令，不自动启动全稿下一轮。

## Gotchas（常见误区）

1. **`READY` 不等于授权：** 继续写入前核实具体输入、输出和副作用范围。
2. **UNKNOWN 不等于可恢复：** 没有检查点时只读核对并保持 `resumeAllowed: false`。
3. **状态文件不等于验收证据：** AV 证据必须绑定当前候选摘要。
4. **文件哈希不证明创作判断正确：** 真实页预览仍需人工或标注来源的自动审阅。
5. **修订范围不能扩大：** 仅允许原授权明确包含的变化和受影响页面。

## 执行前必读

把 `HARNESS_SKILL_DIR` 设置为宿主实际加载的本 SKILL.md 所在绝对目录。任何创建、查询、执行、恢复、修订或证据登记前，必须读取本技能的 [任务操作细节](references/task-execution.md)，使用其中公开的 `scripts/harness.py` 入口和当前 `--help`；不得猜测 `designcraft task` 等不存在的命令。

运行数据只写用户任务目录，不写插件缓存。复用已有 taskId 和最新 revision；UNKNOWN 先只读核对，恢复要求持久检查点及明确计划摘要，不自动重放。完成必须有当前候选绑定的 AV-01 至 AV-04 实际证据；技术就绪、哈希或手写 PASS 都不能代替授权和验收。

常见状态迁移、UNKNOWN 恢复拒绝和范围内修订示例见 [工作流案例](examples/workflow-cases.md)、[候选证据失效](examples/stale-evidence.md)和[局部修订范围](examples/scoped-revision.md)。
