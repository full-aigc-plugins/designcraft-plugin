# 技能源正式来源锁

`schemas/source-release-lock.schema.json` 定义正式来源锁字段。`repository` 必须由发布策略单独指定为受信仓库；不能因为锁文件自身声明了仓库地址就自动信任它。锁记录 release tag、tag 对应 commit、技能源版本、完整技能集合、每个技能文件的 SHA-256，以及对排序后文件摘要映射进行紧凑 JSON 序列化所得的 `contentSha256`。

离线校验将锁中的逐文件摘要与本地 `skills/<skill>/` 全量文件比较，并校验集合、路径、版本和摘要。只完成离线校验时，在线状态仍为 `NOT_RUN`，`releaseAllowed` 为 false。

```bash
python3 -I -B scripts/release_lock.py \
  --lock /path/to/source-release-lock.json \
  --source-root /path/to/designcraft-skills \
  --trusted-repository https://github.com/<owner>/<repository>
```

只有在明确需要在线核验时才添加 `--resolve-online`。该模式只调用 `git ls-remote` 解析 tag，不 clone、不 fetch 工作区、不改写 Git 状态。annotated tag 使用 peeled commit。tag 不存在或解析 commit 与锁不同时拒绝；网络或 Git 命令不可用时输出 `NOT_VERIFIED_NETWORK_UNAVAILABLE`，不能视为通过。

目前技能源没有真实 Git 仓库/tag 发布身份，所以这里的 schema 和夹具只证明校验逻辑。未有实际受信仓库与 tag 前，不创建正式锁，也不声称在线来源验证完成。
