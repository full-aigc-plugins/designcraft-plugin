# 跨仓库完成追溯（验收仍开放）

本报告为 OpenSpec 源端 5.4 / 插件端 5.5 的追溯材料。核对当前规格、全部场景、任务、实现文件摘要和实际已通过的离线测试方法；未以任务勾选、模块测试或报告存在推定需求整体完成。代码与测试未变化，复用原始测试 runId/时间，未声称本轮重跑。

覆盖 35 项需求、88 个规格场景、73 项任务。64 项已勾选、9 项开放；已记录 207 个离线 PASS 方法的当前文件摘要。全局 `completeAcceptance/releaseAllowed/archiveAllowed` 均为 false。

| 仓库 | 需求 | 场景数 | 关联开放任务数 | 支持性测试数 | 需求整体验收 |
|---|---|---:|---:|---:|---|
| designcraft-skills | AV-01 业务结果与警告分类 | 4 | 1 | 40 | 未作通过结论 |
| designcraft-skills | AV-02 产物身份与可编辑工程重开 | 3 | 0 | 6 | 未作通过结论 |
| designcraft-skills | AV-03 逐页审阅与证据绑定 | 2 | 0 | 4 | 未作通过结论 |
| designcraft-skills | AV-04 局部修订与格式兼容 | 2 | 1 | 12 | 未作通过结论 |
| designcraft-skills | EX-01 组合调用保留执行语义 | 2 | 0 | 31 | 未作通过结论 |
| designcraft-skills | EX-02 短任务与长驻进程生命周期 | 2 | 0 | 31 | 未作通过结论 |
| designcraft-skills | EX-03 运行身份与可核对检查点 | 3 | 0 | 27 | 未作通过结论 |
| designcraft-skills | EX-04 单会话与兼容回执 | 4 | 0 | 27 | 未作通过结论 |
| designcraft-skills | EX-05 输入保全与写入范围 | 3 | 0 | 27 | 未作通过结论 |
| designcraft-skills | QG-01 自包含测试与文档检查 | 1 | 0 | 28 | 未作通过结论 |
| designcraft-skills | QG-02 组合与拒绝场景 | 1 | 0 | 39 | 未作通过结论 |
| designcraft-skills | QG-03 固定原生首用验收 | 1 | 1 | 5 | 未作通过结论 |
| designcraft-skills | QG-04 证据时效与能力声明 | 2 | 2 | 13 | 未作通过结论 |
| designcraft-skills | QG-05 技能正文与渐进式资料质量 | 2 | 0 | 18 | 未作通过结论 |
| designcraft-skills | SK-01 六项技能职责与路由 | 6 | 0 | 18 | 未作通过结论 |
| designcraft-skills | SK-02 场景契约与渐进式资料 | 1 | 0 | 18 | 未作通过结论 |
| designcraft-skills | SK-03 命令归属与原生事实源 | 4 | 0 | 20 | 未作通过结论 |
| designcraft-skills | SK-04 独立安装与路径契约 | 2 | 0 | 45 | 未作通过结论 |
| designcraft-plugin | HI-01 真实宿主入口与单一默认路由 | 3 | 1 | 17 | 未作通过结论 |
| designcraft-plugin | HI-02 声明组件与实际组件一致 | 1 | 0 | 17 | 未作通过结论 |
| designcraft-plugin | HI-03 安装与任务授权边界 | 1 | 1 | 60 | 未作通过结论 |
| designcraft-plugin | HI-04 平台与宿主支持声明 | 1 | 0 | 23 | 未作通过结论 |
| designcraft-plugin | HI-05 只读运行能力预检 | 4 | 0 | 43 | 未作通过结论 |
| designcraft-plugin | PH-01 本地 Harness 与共享契约 | 3 | 0 | 53 | 未作通过结论 |
| designcraft-plugin | PH-02 单任务状态与可恢复身份 | 7 | 0 | 43 | 未作通过结论 |
| designcraft-plugin | PH-03 完成与显式修订 | 5 | 1 | 48 | 未作通过结论 |
| designcraft-plugin | PH-04 状态输出与保留边界 | 2 | 0 | 43 | 未作通过结论 |
| designcraft-plugin | RG-01 分层门禁与独立夹具 | 1 | 0 | 70 | 未作通过结论 |
| designcraft-plugin | RG-02 当前证据绑定 | 2 | 0 | 6 | 未作通过结论 |
| designcraft-plugin | RG-03 来源发行与市场一致性 | 6 | 3 | 22 | 未作通过结论 |
| designcraft-plugin | RG-04 完成归档与后续范围 | 1 | 1 | 6 | 未作通过结论 |
| designcraft-plugin | SP-01 候选身份一致性 | 1 | 0 | 17 | 未作通过结论 |
| designcraft-plugin | SP-02 正式发行来源锁 | 2 | 2 | 11 | 未作通过结论 |
| designcraft-plugin | SP-03 外部技能与本地技能边界 | 1 | 0 | 17 | 未作通过结论 |
| designcraft-plugin | SP-04 受控同步与用户修改保护 | 2 | 1 | 17 | 未作通过结论 |

模块级测试可同时支持多项需求，表中数量不能相加当作新增测试或逐场景通过数。report.json 给出每个规格/实现/测试路径、行号、SHA、原始测试 runId 及场景清单；所有需求均保留 NOT_CONCLUDED，不把此追溯表当成验收证书。

剩余门禁及所需证明：

- HUMAN_CREATIVE_REVIEW：Human signoff for current four-page revised project/PDF; automated review is not a substitute. 当前：Current revision task REVIEW_REQUIRED revision 9; no human signoff received.
- CONFIRMED_RECOVERY_SUFFIX：Explicit acknowledgement of unverified process descendants and exact remaining-plan SHA, then actual installed-host single execution of the suffix and receipt. 当前：Task 337385e7-c334-4cf4-8e9c-79ba86503df6 RECONCILING revision 5; resumeAllowed false; no prepare-recovery or suffix run.
- FORMAT_TARGET_ACCEPTANCE：IDML actual target-application interoperability, external PDF/X verification, and explicit qualification of fixed-CLI format losses/unsupported outputs. 当前：Partial native format observations and actual Apple Books EPUB observations do not complete this gate.
- FORMAL_SOURCE_IDENTITY：Necessary source gates completed, real authorized release tag/commit/content identity, online trusted resolution, controlled formal-lock synchronization. 当前：Public main branches and unpublished drafts exist, but no release tags.
- RELEASE_AND_ARCHIVE：All required acceptance layers, actual release package/tag/marketplace identity, verified specification sync and archive. 当前：Nine tasks remain open; no release or archive allowed.

历史重复编号 2.4b 的参数边界修复项已最小改为 2.4d；先前契约集成项继续保留 2.4b，旧证据不改写。当前报告不宣称规格已同步、change 已归档、目标应用已验收或 Release 已发布。
