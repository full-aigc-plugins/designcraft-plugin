# 授权范围内的局部修订

- **授权：** “Only change page 3 title and recheck that page”。
- **允许：** 修订描述 “Change page 3 title”，受影响页面 `page-3`，使用最新任务 revision。
- **拒绝：** “Rewrite all pages”超出原授权，不迁移状态、不调用原生入口。
- **预期状态：** 范围内申请最多回到 `PREPARED` 并等待新的执行指令；不自动启动。
- **边界：** 页面标识必须来自当前已核验工程，不能沿用未知跨会话对象 ID。
