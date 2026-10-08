# 局部修订证据

`scripts/revision_evidence.py` 校验 AV-04 的规范化修订记录：用户授权范围、修订前后工程和快照摘要、完整页审阅、受影响页面集合及所有导出身份。它只校验记录之间的一致性，不执行原生编辑，也不能证明用户授权、原生快照、视觉审阅或导出判断真实发生。

## 生成顺序

1. 保存修订前工程，完成新会话重开和 AV-02 产物清单；按当前任务 rubric 完成逐页审阅记录。
2. 记录明确授权范围：页、对象或 Story，以及授权原文。生成规范化快照，列出每个对象的稳定 ID、所在页、内容摘要和可用 Story ID。
3. 执行一次授权修订后，保存为新的工程身份；重新生成 AV-02 清单、完整 AV-03 逐页审阅和规范化快照。快照摘要必须与工程摘要一致。
4. `affectedPages` 必须等于根据对象变化及其 Story 流关系计算出的完整集合。Story 修订会覆盖修订前后该 Story 涉及的全部页面。
5. 为修订前清单中每个导出项提供修订后对应产物的 `PASS` 重验记录。路径、格式或摘要不匹配会拒绝通过。
6. 在同时包含两轮证据文件的根目录运行：

```bash
python3 -I -B "$SKILL_DIR/scripts/revision_evidence.py" \
  --root /absolute/path/revision-evidence \
  --revision /absolute/path/revision-evidence/revision.json
```

修订记录使用 `designcraft-revision/v1`。`before` 和 `after` 各包含 artifact manifest、page review、revision snapshot 的相对路径与 SHA-256；授权、`affectedPages` 和 `revalidatedExports` 绑定两轮身份。路径不能越出证据根目录，也不能经过符号链接。

例如只改第三页标题时，授权 scope 为 `{"type":"page","page":3}`，快照中仅第三页标题对象的摘要可以变化，且重验受影响页和导出。若该标题属于跨页 Story，Story 关联页也必须进入 `affectedPages`。对象或 Story 范围使用 `objectId` 或 `storyId`。

校验器输出 `PASS` 只表示引用、摘要和范围声明相互匹配；结果的 `completeAcceptance` 固定为 `false`。真实原生 CLI 执行、实际视觉审阅及内容正确性仍须单独验证。
