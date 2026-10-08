# 技能快照维护与旧候选迁移

共享技能只在 `designcraft-skills` 源项目修改。先在源项目运行包校验和离线测试，再使用源项目拥有的 `scripts/sync_local_snapshot.py` 同步当前本地未发布插件。同步器先核对候选旧文件摘要，保留插件本地 `designcraft-harness`；已发布来源、来源错配、用户改动、链接及删除问题都要先处理，不能强制覆盖。

旧版本地候选若缺少 `schemaVersion`、`candidateType` 或 `bundledSourceIdentity`，先保留完整副本并确认旧摘要与当前技能文件一致：

```bash
python3 -I -B /path/to/designcraft-skills/scripts/sync_local_snapshot.py \
  --plugin-root /path/to/designcraft-plugin --migrate-legacy
```

升级会把原始元数据保存为 `candidate-source.json.legacy`，再原子替换为当前候选 schema；它只接受当前版本、当前技能源身份、未发布且逐文件摘要完全一致的候选。已发布来源、过期源版本、快照漂移或备份内容冲突都会拒绝迁移。迁移后再运行同一脚本（省略 `--migrate-legacy`）同步源技能更新，并在插件侧运行测试与包校验。

脚本会排除 `.DS_Store`、`__pycache__`、`.pyc` 和 `.pyo` 等机器生成文件；其余文件摘要均参与来源锁。候选插件本身不是正式发行身份，迁移不会创建 Git、tag、发行或市场记录。

共享 EX/AV 契约的版本、公开入口和验收范围见技能源 [契约交付说明](https://github.com/full-aigc-skills/designcraft-skills/blob/main/docs/plugin-handoff.zh-CN.md)。本地联合报告为 `evidence/source-handoff-20261008.json`，其中的两个仓库摘要、候选锁、资源清单和离线报告必须与当前状态一致；源方副本为 `evidence/plugin-handoff-20261008.json`。合同离线兼容通过不代替宿主、原生、创作或正式发行。
