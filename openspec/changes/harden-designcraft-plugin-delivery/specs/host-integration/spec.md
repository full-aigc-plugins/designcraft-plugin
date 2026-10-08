## Purpose

使插件在首个目标宿主中能够被发现并正确选择技能，同时保持包可移植性和公开能力声明的真实性，通过独立的安装、发现、模型路由及实际调用证据避免把清单存在等同于宿主支持。

## ADDED Requirements

### Requirement: HI-01 真实宿主入口与单一默认路由

首个支持目标 SHALL 为 Codex；提供该宿主实际支持的发现元数据，未指定操作的 DesignCraft 请求默认交给 use，原子技能和 Harness 显式调用。必须通过宿主场景验证路由，不能仅凭 metadata 宣称自动选用。

#### Scenario: 自然语言与显式调用
- **WHEN** 用户分别请求多页手册、显式导出和无关任务
- **THEN** 宿主分别选择 use、export 和不调用 DesignCraft，记录选择与实际执行证据。

#### Scenario: Codex 默认和显式技能输入
- **WHEN** Codex 构建未指定技能或显式指定原子技能的模型输入
- **THEN** agents/openai.yaml 仅允许 use 隐式调用；原子技能和插件本地 Harness 的 allow_implicit_invocation 为 false，仍可显式加载。包校验拒绝缺失或错误策略；宿主输入验证不代替实际模型路由和原生验收。

### Requirement: HI-02 声明组件与实际组件一致

插件 SHALL 检查 portable 与宿主清单、技能集合、资源路径、版本、图标和存在的命令入口；没有实际可用服务时不声明 MCP，没有执行实现时不登记 hook。建议型 hook 不得阻塞无关任务或自动安装外部依赖。

#### Scenario: 空 MCP 声明
- **WHEN** 包声明 MCP 但无可运行服务与接入证据
- **THEN** 分发验证拒绝该声明，不因底层 CLI 有 mcp 子命令就报告接入完成。

### Requirement: HI-03 安装与任务授权边界

技能加载 SHALL 从实际安装路径定位，运行数据与缓存分离；安装、发现、模型选用和原生执行分别验收。已有任务授权在阶段切换后继续有效；缺少依赖安装授权时停止该安装而继续可做的离线检查。

#### Scenario: 从新缓存路径加载
- **WHEN** 插件安装路径包含中文空格且原开发目录不存在
- **THEN** 技能可定位资源并执行离线检查，不依赖兄弟工作区或硬编码开发路径。

### Requirement: HI-04 平台与宿主支持声明

支持矩阵 SHALL 只将完成当前版本验收的宿主/平台标为支持；初期 macOS arm64 与 Python 3.11+ 不等于已支持所有 Python 版本、Windows 或其他宿主。原生/宿主/创作证据独立。

#### Scenario: 其他宿主只有清单
- **WHEN** 为其他宿主生成了配置但未实测
- **THEN** 状态标为配置已生成或未验收，不宣传完整支持。

### Requirement: HI-05 只读运行能力预检

Harness SHALL 在可能产生副作用的任务前提供只读 readiness 结果，分别报告宿主插件加载、技能快照/来源身份、固定 CLI 路径与版本、共享回执契约兼容性，以及请求所需能力的状态。每项状态 SHALL 使用 `READY`、`DEGRADED`、`UNAVAILABLE` 或 `NOT_CHECKED` 并附可核对依据和安全下一步。宿主、模型路由和命令能力的 PASS SHALL 引用证据清单中的对应记录，并验证证据仍绑定当前插件/来源/运行时、输入和产物摘要；仅在支持矩阵或调用方 JSON 中写入 PASS 不构成证据。缺少依赖、CLI/契约版本不兼容或能力未验证时 SHALL 阻止依赖该能力的写入；预检不得自动安装、登录、升级或改写工程。能力可发现不等于原生调用通过，原生/宿主/创作证据继续分层记录。

#### Scenario: CLI 缺失时请求修改工程
- **WHEN** readiness 发现固定 CLI 不存在或无法读取版本，用户请求执行排版修改
- **THEN** 结果报告 `UNAVAILABLE` 及缺少项，Harness 不启动安装器或原生写入，仍可提供只读诊断。

#### Scenario: CLI 可用但请求能力未验证
- **WHEN** CLI 版本可识别，但请求命令/能力没有当前版本的验证记录
- **THEN** readiness 将该能力标为 `DEGRADED` 或 `NOT_CHECKED`，不得路由到写入执行，也不得宣传受支持。

#### Scenario: 预检通过
- **WHEN** 宿主、候选身份、CLI 和共享契约均匹配，且请求能力存在有效当前证据
- **THEN** 返回 `READY` 和证据引用；后续写入仍遵循既有用户授权、PH-02 状态机及 AV 验收门禁。

#### Scenario: 能力证据绑定已过期
- **WHEN** 能力报告不在插件证据目录、未由证据清单引用，或其绑定的插件/来源/运行时/产物摘要已经变化
- **THEN** readiness 报告 `UNAVAILABLE` 或 `NOT_CHECKED`，并拒绝依赖该能力的原生写入。
