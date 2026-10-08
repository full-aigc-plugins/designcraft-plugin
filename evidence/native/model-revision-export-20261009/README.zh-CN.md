# 真实 Codex 已有工程局部修订记录

本目录归档已完成的 `native-existing-revision` 模型场景，安装候选为 `cb8a129af88fee6a5703f3386d898c340cad2e7a`。实际 Codex 宿主显式使用已安装 Harness，经公开网关将第三页 Story 65 标题改为 A Considered Grid，另存四页工程、导出普通 PDF，并在独立原生会话中重开。两个原生回执均为 NATIVE_EXIT_ZERO_REVIEW_REQUIRED；两次预检均为 0 错误、0 警告。

`model.public-tool-calls.json` 保留该模型回合全部 16 对公共工具调用与输出，包括辅助检查失败，未筛去非零退出；未包含模型推理、凭据或服务器内部状态。`installed-file-sha.json` 保存安装文件核对结果；计划、原始回执、任务快照及产物均保留。回执中的临时绝对路径为实际执行路径，归档后不改写。

`before/` 是按 baseline-reuse.json 逐文件摘要复用的既有基线，不代表新模型调用。独立读取前后 ZIP 的 document.json，确认只有 Story 65 改变、spreads 和其他字段一致。

随后完成显式 export 技能真实模型场景（thread 01a11c81-761a-7913-8202-e27ebc491c3e）：独立原生 run dcef98df-c27f-44cc-a1f1-d49c1f9e48a9 重开修订工程、检查标题/四页结构、预检并输出普通 PDF。原件摘要保持不变，0 errors、0 warnings；公共调用及回执见 explicit-export/。安装仍为固定 cb8a129，当前代码与该安装逐文件一致；7d64cf6 只新增之前已完成场景的归档证据。

本轮实际查看前后各四页预览，逐页六维观察保存在 before/current-page-review.json 和 after/current-page-review.json，明确标记自动来源。新导出 PDF 与先查看的修订 PDF 字节身份不同，但四页渲染像素逐字节一致，记录见 render-verification.json；审阅绑定新 PDF 派生的预览摘要。两个 current-revision-snapshot.json 都从保存工程 ZIP 按同一算法生成：所有 spread 对象的完整序列化数据与其 Story 内容参与摘要，继承父版对象按实际页/side 展开。另有独立全量文档字段比较，确认只有 Story 65 改变，防止未建模全局字段绕过局部范围判断。

公开 AV-02、AV-01、AV-03、AV-04 校验均通过（*.validation.json）。首次 AV-04 登记使用错误字段 id，被校验器拒绝；改为契约要求的 artifactId 后通过，原失败报告保留。这是证据编制错误，未重放原生编辑。

随后使用安装候选的公开 Harness，在原任务 ee080135-babb-401d-9830-36b37a7f6b9b 登记四项证据，未新建任务或替换原修改 runId。harness-verification/ 保存实际 CLI 输出、AV 附件与前后任务；最终 REVIEW_REQUIRED revision 9。验证器操作由外层验收流程执行，显式 export 模型回合本身不宣称已登记 AV。初始 task.json、verification.json 和 model-final.md 保留其当时 EXECUTING revision 3 状态，不用后续状态改写历史。

人工创作签核、完整原生创建验收、重启恢复及正式发布仍开放。旧基线产物/重开证据按 baseline-reuse.json 复用，当前页审阅和规范化快照为本轮新生成，不把旧基线自动审阅充作本次审阅。task-metadata-requalification.json 证明任务跟踪文档之外代码、测试、源锁与固定安装资源未改变；既有离线、宿主、CI 等观察保留原 runId/时间，只补充复用依据，不伪造重跑。
