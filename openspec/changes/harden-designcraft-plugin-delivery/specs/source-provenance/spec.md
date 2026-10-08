## Purpose

定义技能快照在本地候选与正式发行两种阶段的来源身份和更新边界，使插件可以验证内容与版本关系并保护用户修改，同时保持共享技能只在独立源项目维护、本地 Harness 由插件拥有。

## ADDED Requirements

### Requirement: SP-01 候选身份一致性

候选插件 SHALL 校验 sourceProject 为 designcraft-skills、sourceVersion 与输入源清单一致、sourceStatus 为本地候选且 releaseTag 为空；不能只检查摘要后输出来源有效。插件版本与技能源版本分别解释，不假定永远相等。

#### Scenario: 候选身份字段漂移
- **WHEN** sourceProject 错误、sourceVersion 与源清单不符或候选 releaseTag 非空
- **THEN** 校验失败且不复制快照、不登记公开发行、不改写原元数据。

### Requirement: SP-02 正式发行来源锁

正式发行 SHALL 绑定受信 repo、非可变 releaseTag、解析后的 commitSha、源版本和技能内容摘要；离线内容验证与在线 ref/commit 验证须分别报告，网络不可用不得伪装成在线通过。

#### Scenario: 标签指向变化
- **WHEN** 同名发行 tag 解析为不同 commit
- **THEN** 拒绝来源验收，保留原锁和技能；必须显式更新与重新验证。

#### Scenario: 离线验证
- **WHEN** 无网络但本地摘要匹配
- **THEN** 只报告离线内容通过，来源 ref 验证仍未完成。

### Requirement: SP-03 外部技能与本地技能边界

插件 SHALL 分别列出六项外部技能与本地 Harness，校验实际集合准确匹配清单；共享修复必须先进入技能源，禁止直接修改 vendored 快照绕过来源更新。

#### Scenario: 添加本地 Harness
- **WHEN** 插件新增 designcraft-harness
- **THEN** 本地清单登记 Harness，外部锁仍只包含六项技能；两类技能均进入完整分发检查。

### Requirement: SP-04 受控同步与用户修改保护

同步 SHALL 在复制前验证旧快照和全部身份，拒绝用户漂移、越界/链接及未审查源删除；成功后核对新内容并更新来源记录。中途失败必须可识别且不可当作完整快照消费。文档须明确同步器属于技能源。

#### Scenario: 插件快照已被用户修改
- **WHEN** 同步发现任一旧文件摘要不符
- **THEN** 保留用户文件与旧来源记录，报告差异，不强制覆盖。

#### Scenario: 复制中断
- **WHEN** 同步只完成部分文件即失败
- **THEN** 保留可诊断状态，分发验证拒绝该候选，不能报告同步成功。
