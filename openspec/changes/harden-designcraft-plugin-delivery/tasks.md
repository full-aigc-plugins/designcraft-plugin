> 2026-10-09 过度设计裁剪：删除平台机制范围（任务生命周期/网关状态机/写锁/重启恢复 2.1、2.3、2.4、2.4b、2.4c，AV 评审证据闭环 2.5a、2.5b、2.5d，支持矩阵与授权边界 3.5，readiness 证据门禁 3.6，证据清单失效与分层结论 4.2、4.5，P2 正式来源锁与发行门禁/验收追溯 5.1～5.5）及执行约定流水账；历史见 git 与 docs/verification/。保留功能行：来源身份与受控快照、Harness 技能与入口、宿主安装/发现/路由、真实创作修订与交付、回归与 CI。未完成任务收敛为实现导向单行。

## 1. P0 来源身份与受控快照

- [x] 1.1 [SP-01, RG-01] 固化 sourceProject、sourceVersion、sourceStatus、releaseTag 漂移仍被接受的失败测试；证据：真实校验入口面对错误候选的红灯，fixture 不依赖兄弟仓库。
- [x] 1.2 [SP-01] 定义候选 schemaVersion/类型及携带的源身份清单，校验项目、源版本、候选状态与空 releaseTag；证据：1.1 回归通过，插件和源版本不相同但契约兼容的合法样本通过。
- [x] 1.3 [SP-03, HI-02] 分别登记六项外部技能和本地 Harness，验证无冲突并集、实际文件与来源摘要范围；证据：缺项、多项、重名和误将本地技能加入外部锁的拒绝测试。
- [x] 1.4 [SP-04] 使用临时源/插件 fixture 定义漂移、越界链接、未审查删除及中断同步验收；依赖源方 QG-01 和受控同步器实现，证据：用户文件保留、失败候选不可消费、成功后新快照一致。
- [x] 1.5 [SP-01, SP-03, SP-04] 更新候选迁移、共享修复回源和源方同步器使用说明，保留旧元数据副本；证据：从旧候选到新候选的演练，不直接修改共享技能快照。

## 2. P1 本地 Harness 与任务生命周期

- [x] 2.2 [PH-01, SP-03] 新增本地 designcraft-harness 技能、执行入口和兼容版本声明，通过公开入口消费源契约；依赖源 EX 版本化接口，证据：不导入私有函数、无重复安装/参数实现的兼容测试。
- [x] 2.4d [PH-01] 修复真实 Harness 调用暴露的参数顺序错误：显式 `--` 前接受 TASK_ID 前/后的 Harness 参数，之后逐字保留源参数及嵌套边界；未知头部参数、缺 revision 和多余位置参数在 dispatch 前拒绝；保留旧无边界调用。证据：先复现文档顺序缺 revision 的红灯，再通过三项参数边界回归；真实四页流程重验单独记录，不把受控 dispatch 测试当作原生/宿主验收。
- [x] 2.5c [PH-03, AV-01, AV-04] 基于固定 CLI 原生证据完成问题分类、授权局部修订和导出重验，并取得真实创作审阅证据。旧 evidence/native/harness-integration-20261008.json 的 AV-01 为人工附加，现已注明失效原因。新 evidence/native/av01-verified-integration-20261008/report.json 通过公开 verify-business 和 AV-02/03/04 校验器完成已保存候选的证据登记及状态门禁；已完成宿主发现与只读模型路由，已有 `evidence/native/harness-real-20261009/report.json` 证明本地 Harness 真实创建/保存四页工程及导出 PDF，但未证明模型宿主发起原生调用、局部修订或完成创作接受，因此本项保持开放。当前 evidence/native/model-revision-export-20261009/ 已补齐真实模型发起的局部修订、显式导出、逐页自动审阅与公开 AV-01～AV-04 登记，原任务仍为 REVIEW_REQUIRED；自动审阅不能替代人工签核。 2026-10-09 人工验收补充：用户明确表示“产出我看了，不说内容，单说排版，已经通过了”。四页修订产物排版验收通过，内容未评审；签核绑定当前工程/PDF SHA，见 `evidence/native/model-revision-export-20261009/human-layout-acceptance/review.json`。此记录关闭本项人工排版门禁；历史 Harness REVIEW_REQUIRED 快照不改写，不代表全部格式、恢复、发行或归档通过。
- [x] 2.6 [PH-03, PH-04] 实现明确范围内的局部修订和统一 status/scope/actions/evidence/artifacts/skipped/risks/next_action 输出；证据：第三页标题修订复用授权、追踪受影响页面且不自动开启全稿下一轮。Harness 要求修订描述匹配原授权文本、显式登记受影响页面，并仅迁移到 PREPARED；超出范围继续停留在 REVISION_REQUIRED，CLI 输出包含 affectedPages 和下一动作。

## 3. P1 首个宿主与可移植安装

- [x] 3.1a [HI-01, HI-02] 核对并补齐 Codex/portable 静态清单格式和技能目录元数据；证据：portable root manifest 与 `.codex-plugin/plugin.json` 身份一致，`skills` 路径为包内 `./skills/`，包校验通过。格式依据 [OpenAI 插件打包规范](https://developers.openai.com/plugins/build/plugins) 核对；该项仅证明静态兼容结构。
- [x] 3.1b [HI-01, HI-02] 在实际 Codex 宿主安装并验证 use 默认隐式路由、原子技能/Harness 显式调用和技能来源路径；证据：真实加载字段、被选择的技能和文件来源记录。静态清单校验与官方格式核对不能代替真实宿主发现。证据：使用现有 ChatGPT.app 内置 Codex CLI 0.162.0-alpha.2 及默认 gpt-6-astra，从公开仓库固定 commit 5a2fad5b1fd2dadbb24c187f6bbdc5d3798011c7 实际安装；157 个已跟踪文件逐字节一致，7 项技能实际发现，默认目录只有 use。自然语言新建/既有修订、六项显式原子/Harness 和无关请求共 9 个真实只读模型场景通过，记录实际正文注入、读取命令、路径和最终回答。报告 evidence/host/bundled-codex-discovery-20261008.json 与 bundled-codex-model-routing-20261008.json；不声明原生执行、重启续跑、创作或发行通过。
- [x] 3.2 [HI-02, SP-03] 实现 portable/宿主清单、组件、资源、版本、图标和命令一致性校验；证据：离线 fixture 先复现兼容清单版本及图标资源漏检，再由完整套件验证 SemVer、portable/可选 Codex 兼容清单身份和技能路径、图标资源位置/类型、插件本地 Harness Markdown 引用，以及未实现 command/MCP/hook 声明的接受与拒绝；技能集合仍由 1.3 覆盖。此项只证明打包结构校验，未证明 Codex 实际发现或路由，后者由 3.1/3.4 验收。
- [x] 3.3 [HI-03, RG-01] 在无源工作区、中文空格安装路径及只读缓存运行离线入口和 Harness fixture；证据：资源定位正确、运行数据写到独立目录，无硬编码开发路径依赖。
- [ ] 3.4 [HI-01, HI-03] 在真实 Codex 宿主验证通用手册、已有工程修订、显式导出、无关请求、缺运行时及重启恢复，含回归测试。
- [x] 3.4a [HI-01, HI-03, PH-03] 完成真实安装候选的已有工程局部修订及显式导出子场景：Codex 0.162.0-alpha.2 / 默认 gpt-6-astra 实际加载 cb8a129 安装技能；Harness 仅修订第三页 Story 65，原件不变；export 技能在另一原生会话重开、预检并导出四页 PDF。实际模型公共调用、原始回执、工程/PDF、逐页自动审阅和同一 taskId 的公开 AV-01～AV-04 登记见 evidence/native/model-revision-export-20261009/。任务保留 REVIEW_REQUIRED revision 9；此子项不替代父项 3.4 的恢复续跑、任务 2.5c 的人工创作签核或 4.4 的完整创建验收。
- [x] 3.1c [HI-01, HI-02] 同步源端调用策略并为本地 Harness 声明仅显式调用；验证策略及实际宿主默认/显式输入，模型选用仍由 3.1b/3.4 验收。证据：历史报告记录 Codex 0.147.0 隔离实际安装、默认目录只有 use，app-server 结构化显式输入加载七项安装路径与正文；报告 evidence/host/codex-explicit-input-integrity-20261008.json。
- [x] 3.1d [HI-01, HI-02] 修复本地 Harness 正文截断，保留全部流程至本技能 references，并验证七项技能在真实 app-server 的结构化显式输入中完整加载。证据：原 Harness 12967 字节实际被截断；原流程完整迁入本技能 references/task-execution.md，入口要求操作前读取。多字节超限 fixture 先失败后通过，七项真实加载正文与安装文件全文一致。证据只证明宿主输入构建，不证明模型选择、读取参考文件或原生执行。

## 4. P1 分层验收与证据时效

- [x] 4.1 [RG-01] 建立独立临时 fixture 的结构、快照、拒绝、兼容和 Harness 回归入口；证据：只有插件检出也可运行完整离线层，不以单项快照测试代表整体通过。插件本地 Harness 的引用完整性同样由包校验测试，防止 examples/references 在单技能安装包中断链。
- [x] 4.3 [RG-01, RG-02, HI-04] 配置适用的离线 CI 与目标环境验收入口，分开执行/失败/未运行状态；证据：实际 CI 日志或明确 NOT_RUN 原因，不用本地退出 0 代替 CI。Ubuntu/Python 3.11–3.13 离线单测、包校验及 diff 检查在 GitHub Actions run `37807952859` 全部通过，测试提交 `f320d0d3a50d3fc4075473e1113eeee4c106229c`；报告绑定记录在 `evidence/ci/current-github-actions.json`。原生为 `NOT_RUN`；宿主与只读模型路由由独立真实报告验收，不由 CI 通过替代。
- [x] 4.4 [PH-03, RG-01, RG-02] 完成当前已安装候选的固定原生多页创建、重开、逐页自动审阅、局部修订和导出场景。证据：evidence/native/model-create-20261009/ 保存真实模型新建四页、保存/导出、独立重开/重导、当前 AV-01/02/03 与公开 Harness 登记；evidence/native/model-revision-export-20261009/ 保存另一既有工程第三页 Story 65 修订、显式 export 模型会话、前后四页自动审阅和同一修订任务 AV-01～AV-04 登记。工程、PDF、预览、回执及安装资源摘要分别绑定，不混用两份候选的任务/AV-04。固定 CLI 二进制与源端 QG-03 相同，执行代码与已安装 cb8a129 逐字节一致；期间仅证据与任务跟踪改变。此项仅证明所列 macOS arm64 / Python 3.13.5 场景，任务保持 REVIEW_REQUIRED；2.5c 已取得当前四页修订产物的人工排版签核（内容未评审）；3.4 恢复续跑、目标格式及正式发行仍开放，不提升全局 native/creative/release 层。
