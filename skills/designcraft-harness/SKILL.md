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

## 创建和恢复

首次工作时记录明确目标和用户授权范围：

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" new \
  --goal "创建可编辑的多页手册" \
  --scope "只编辑提供的工作副本并保存到指定目录"
```

任务数据默认写入用户数据目录 `~/.local/share/designcraft/tasks`，可用 `DESIGNCRAFT_TASK_HOME` 指定其他可写位置。不得把任务状态、日志或工程写进只读插件缓存。

执行前先查看只读就绪报告。它分别核对插件快照、源版本、固定 CLI 安装身份、宿主验收和请求命令的版本绑定验证记录；不会下载、安装、登录或修改工程。报告不是用户授权，只有 `READY` 表示技术前置齐全：

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" readiness \
  --runtime-home "${CRAFT_RUNTIME_HOME:-$HOME/.local/share/craft-runtimes}" \
  --command-id "<计划中的原生命令 ID>" \
  --capability-evidence "$HARNESS_SKILL_DIR/../../evidence/native-capabilities.json"
```

能力报告必须位于插件 `evidence/` 目录，并由 `evidence-manifest.json` 中 `native-capabilities` 记录引用；校验器还会核对当前插件/来源/运行时绑定和报告文件摘要。报告须绑定固定 CLI 版本与二进制摘要，并为计划命令提供 `NATIVE_TESTED`/`HOST_TESTED` 记录。只有目录发现、离线 fixture、缺失记录或过期摘要时会阻止 Harness 的原生调用。宿主发现和模型路由未验收时也不能声称就绪。未通过时按 `components` 和 `nextAction` 修复缺口，勿通过省略预检绕过门禁。

读取 `new` 输出的 `taskId` 后，可跨会话查看任务：

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" show "$TASK_ID"
```

每次状态更新都必须使用返回的最新 `revision`。状态损坏、回执缺失或身份不符时保留原文件，只读诊断，不删除后重跑。

## 状态推进

允许的路径是准备、执行、未知核对、验证、待审阅、局部修订或完成。UNKNOWN/FAILED_OR_PARTIAL 必须先进入 `RECONCILING`。无恢复合同或任何身份/摘要错配时，`reconcile` 保持只读且 `resumeAllowed: false`。只有验证技能源公开合同并人工确认精确计划 SHA 后，`prepare-recovery` 才能将原任务恢复为 PREPARED；自由文本不能解除阻塞。

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" transition \
  "$TASK_ID" EXECUTING --expected-revision 0

python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" reconcile "$TASK_ID"
```

具备检查点恢复材料时，先只读核验（路径指向同一次源端观察的文件）：

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" reconcile "$TASK_ID" \
  --recovery-report "$RECOVERY_REPORT" \
  --reopen-receipt "$REOPEN_RECEIPT" \
  --reopen-plan "$REOPEN_PLAN" \
  --original-plan "$ORIGINAL_PLAN" \
  --saved-project "$SAVED_PROJECT"
```

核对输出 `resumeAllowed: true` 后，人工检查 `remainingPlan`，再用其 `remainingPlanSha256` 和当前 task revision 显式准备恢复。若输出列出 `process_descendants_termination_unverified`，还需明确确认这项风险；不要对未列出的风险传入确认参数。返回的 `recoveryPlanRef` 指向持久化在 task 目录中的同一计划；后续 `native run` 若计划、保存工程或证据文件摘要发生变化，会在调用源技能前拒绝。

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" prepare-recovery "$TASK_ID" \
  --expected-revision "$REVISION" \
  --confirm-plan-sha256 "$REMAINING_PLAN_SHA256" \
  --recovery-report "$RECOVERY_REPORT" \
  --reopen-receipt "$REOPEN_RECEIPT" \
  --reopen-plan "$REOPEN_PLAN" \
  --original-plan "$ORIGINAL_PLAN" \
  --saved-project "$SAVED_PROJECT"
```

若且仅若 `reconcile` 的 `risks` 包含该风险，在上面的命令中添加：

```bash
--acknowledge-risk process_descendants_termination_unverified
```

在执行态，通过 Harness 的 `native` 子命令调用技能源公开入口。原生 `run` 可能安装固定运行时并修改工程；调用前必须确认用户授权范围覆盖实际输入、输出和副作用：

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" native \
  "$TASK_ID" --expected-revision 1 \
  --runtime-home "${CRAFT_RUNTIME_HOME:-$HOME/.local/share/craft-runtimes}" \
  --capability-evidence "$HARNESS_SKILL_DIR/../../evidence/native-capabilities.json" -- \
  run "$PLAN_JSON" --output "$NEW_TASK_OUTPUT_DIR"
```

Harness 只接受其支持的版本化运行回执；缺失或不兼容时将结果记为 `UNKNOWN`，停止后续写入并进入核对。

完成状态要求任务具有当前候选摘要、没有未解决阻塞项，并绑定 AV-01 至 AV-04 的 PASS 证据。证据文件须在任务的 `evidence/` 目录内，JSON 至少包含 `taskId`、`kind`、`status: PASS`、`candidateSha256`；通过 `attach-evidence` 登记时按内容摘要保存。修改候选后，旧候选证据不再满足完成门禁。

AV-02/AV-03 不能手工提交 `status: PASS` JSON。AV-02 必须验证当前候选文件身份和工程新会话重开；AV-03 必须基于该 AV-02 证据并校验当前逐页预览摘要及审阅记录。具体命令、字段和失败条件见本技能 [交付证据参考](references/acceptance-evidence.md)。

AV-03 使用同一交付目录和产物清单，并提供页级预览与审阅记录：

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" verify-review \
  "$TASK_ID" --expected-revision "$REVISION" \
  --root "$DELIVERABLE_DIR" \
  --artifact-manifest "$DELIVERABLE_DIR/artifact-manifest.json" \
  --review "$DELIVERABLE_DIR/page-review.json"
```

Harness 会调用技能源公开页审阅校验器，核对 AV-02 清单摘要、当前候选工程 SHA、rubric、每页预览摘要和审阅来源；之后 freshness 检查会重新运行校验器。预览、清单或审阅内容变化都会使 AV-03 证据失效。校验器只证明记录与当前输入绑定，不证明人工或自动视觉判断本身正确。

AV-04 在修订后的 AV-02/AV-03 通过后核对两轮工程身份、规范化对象快照、用户授权范围、Story 影响页闭包及全部修订后导出。使用 `verify-revision` 登记：

```bash
python3 -I -B "$HARNESS_SKILL_DIR/scripts/harness.py" verify-revision \
  "$TASK_ID" --expected-revision "$REVISION" \
  --root "$REVISION_EVIDENCE_DIR" \
  --revision "$REVISION_EVIDENCE_DIR/revision.json"
```

技能源 `revision_evidence.py` 会重新核验前后 AV-02 清单和 AV-03 审阅，并绑定修订记录摘要与当前任务候选。修改修订记录、快照、清单、预览或审阅会使 AV-04 失效。它只验证证据链的一致性，不证明用户授权、原生修改或视觉/导出判断真实发生；原生修订仍须单独验收。

Harness 检查状态迁移、文件摘要和候选身份，不替代技能源的原生工程重开、视觉审阅或导出检查。仅在对应实际证据完成后登记 PASS。修订须明确范围，完成一次后等待用户新的指令，不自动开启下一轮。

从 `REVISION_REQUIRED` 恢复时，`revisionScope` 必须是原授权范围内的明确变更描述，`revisionPageRefs` 必须列出受影响页面标识。Harness 以原授权文本包含规范化修订描述作为保守的离线范围检查；无法匹配时保留 `REVISION_REQUIRED`，不得自行扩大授权。范围内修订迁移只到 `PREPARED`，状态输出将给出 `affectedPages` 和 `execute_scoped_revision`，不会自动执行或启动全稿新一轮。例如用户授权“Only change page 3 title and recheck that page”时，修订描述“Change page 3 title”、页面 `page-3` 可以复用该授权；“Rewrite all pages”会被拒绝。

状态输出包含 `status`、`scope`、`actions`、`evidence`、`artifacts`、`skipped`、`risks` 和 `next_action`，并带任务 revision、runId 和检查点引用。共享回执语义和原生参数以 `designcraft-skills` 的公开契约为准。

常见状态迁移、UNKNOWN 恢复拒绝和范围内修订示例见 [工作流案例](examples/workflow-cases.md)、[候选证据失效](examples/stale-evidence.md)和[局部修订范围](examples/scoped-revision.md)。
