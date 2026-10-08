# 本地交付架构

独立技能项目是源码来源，每项技能携带固定CLI安装器、公开argv入口、命令目录网关及运行时锁。插件保存逐文件摘要的本地快照；来源未发布，不能登记为可安装市场发行。

PrintCraft使用原生JSON Schema；LightCraft、DesignCraft保留参数说明文本。计划在一个原生进程中执行；超时保留未知状态，不自动重放。零退出仍需检查工程、输出、保存重开和创作质量。安装、宿主发现、模型选用及最终交付分别验收。

[OpenSpec 优化变更](../openspec/changes/harden-designcraft-plugin-delivery/proposal.md)已建立并通过格式校验，实现任务仍未完成。开发候选已推送至[公开 GitHub 仓库](https://github.com/full-aigc-plugins/designcraft-plugin)的 `main` 分支；尚无版本标签、GitHub Release 或插件市场发行。原生安装尚未执行，执行时须具备对应授权。已有五套仍使用原OpenSpec；三领域的ArtCraft公共协议映射、依赖交接、返工和移动交付仍未接入。


安装锁现在绑定发行标签、归档名、二进制身份与版本；不一致时在创建运行时目录前拒绝。当前所有三领域真实固定发行仍为0.2.1。
