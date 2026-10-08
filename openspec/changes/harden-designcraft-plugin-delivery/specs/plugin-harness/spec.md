## Purpose

为插件任务提供持久编排和交付状态，将独立技能、共享执行结果与工程审阅连接起来，确保未知任务可核对、修订有明确范围且完成判定依赖真实产物证据，而不是仅依据进程退出。

## ADDED Requirements

### Requirement: PH-01 本地 Harness 与共享契约

插件 SHALL 声明本地 designcraft-harness 与六项外部技能的不同所有权，Harness 通过技能源公开入口调用并读取版本化契约，不重复定义安装、原生参数和回执语义。

#### Scenario: 共享接口不兼容
- **WHEN** 同步后的技能源回执版本不在 Harness 支持范围
- **THEN** 停止执行并报告兼容性缺口，不猜测字段或调用私有实现绕过。

### Requirement: PH-02 单任务状态与可恢复身份

Harness SHALL 持久记录任务目标、授权范围、技能路由、runId、工程/产物与检查点引用；状态至少区分准备、执行、未知核对、验证、待审阅、待修订、完成和失败。恢复继承技能源 EX-01～EX-05，不重复写入。

#### Scenario: 启动后宿主重启
- **WHEN** 任务已有 STARTED/UNKNOWN 回执且宿主重新加载
- **THEN** 读取原任务并核对进程与产物，仅在源契约恢复条件满足后执行；不新建重复任务。

#### Scenario: 状态损坏
- **WHEN** 任务状态无法解析或检查点身份不匹配
- **THEN** 保留损坏文件并报告核对步骤，不删除状态后重跑。

#### Scenario: 技能源检查点恢复合同匹配
- **WHEN** `reconcile` 收到同一原 run 的技能源 `designcraft-checkpoint-recovery/v1` 报告、原/重开计划与回执及保存工程，且所有步骤、runId、运行时、工程 SHA 和新会话 inspection 相符
- **THEN** 只读返回已核验的 `remainingPlan`、计划 SHA 和对象清单；人工确认同一计划 SHA 后，`prepare-recovery` 在原 taskId 上持久化精确未启动后缀并迁移到 `PREPARED`，不得新建重复任务或自动执行。

#### Scenario: 恢复计划摘要或执行进程身份有风险
- **WHEN** 保存工程摘要、来源回执或剩余计划不匹配，或进程后代终止未确认
- **THEN** 错配时保持 `RECONCILING` 且只读；未确认的进程后代显示为风险，并要求单独显式确认该风险后才允许准备剩余计划。

#### Scenario: 来源检查点契约缺失
- **WHEN** Harness 能读取任务回执，但技能源尚无可验证的持久工程检查点契约
- **THEN** `reconcile` 只读报告 runId、回执身份和缺少的检查点；状态保持 `RECONCILING`，`resumeAllowed` 为 false。

#### Scenario: 任意文字试图放行未知任务
- **WHEN** 调用方仅提交自由文本恢复说明，或回执 taskId/runId 与任务不一致
- **THEN** 拒绝恢复迁移并保留原回执与任务状态。

### Requirement: PH-03 完成与显式修订

Harness SHALL 仅在任务要求的 AV-01～AV-04 证据齐备且无未解决阻塞项时标记完成；修订必须有明确输入范围，复用当前授权，超出范围才追加确认。首版不自动开启下一轮创作。

#### Scenario: 退出成功但验收缺失
- **WHEN** 原生零退出而工程重开或页级审阅未完成
- **THEN** 任务保持待验证/待审阅，列出缺口，不标记 COMPLETED。

#### Scenario: AV-02 产物未由新会话重开
- **WHEN** 技能源清单只验证了产物文件身份，重开状态为 `NOT_RUN`，或工程摘要与当前候选不同
- **THEN** Harness 拒绝登记 AV-02 PASS 证据，任务不能完成。

#### Scenario: AV-03 审阅记录缺少当前候选绑定
- **WHEN** 页审阅 JSON 为手工伪造、页预览摘要已变化、rubric 不受支持，或其工程/清单摘要不匹配已验证的 AV-02
- **THEN** Harness 调用技能源公开页审阅校验器后拒绝 AV-03 PASS 证据；`_fresh_evidence` 不再将旧审阅计入完成门禁。

#### Scenario: 用户要求局部返工
- **WHEN** 用户已明确第三页标题修改范围
- **THEN** 直接推进范围内修订并重验受影响结果，不重复要求同一授权，不启动无关全稿重做。

### Requirement: PH-04 状态输出与保留边界

Harness SHALL 输出 status、scope、actions、evidence、artifacts、skipped、risks、next_action，并区分已验证、失败、未知和未运行。运行数据必须位于独立可写任务目录，不写入安装技能缓存；并发同任务写入应拒绝或串行化。

#### Scenario: 只读插件安装目录
- **WHEN** 宿主从只读缓存加载插件并发起任务
- **THEN** 任务状态写入独立可写目录；第二个写入者不会覆盖活动任务状态。
