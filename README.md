# codex-with-webgpt

让 Codex 与指定的 ChatGPT 网页会话协作：Codex 发送一个阶段任务，读取该回合回复，核验实际结果，再决定下一步。

## 工作方式

1. 用户给 Codex 任务和目标 ChatGPT 会话 URL。
2. Codex 使用 Safari、Chromium CDP 或 BrowserSkill bridge 发送本轮任务。
3. Bridge 交回回复文本、退出码和事件日志。
4. Codex 核对网页端声称的产物与证据，决定继续、修正或完成。

ChatGPT 网页端能执行哪些操作，取决于该会话启用的工具和权限。这个项目不要求 GitHub Custom GPT；网页端的结论也不替代本地验证。

## 安装给 Codex

将本仓库放入 Codex 的 skills 目录，或把 `SKILL.md` 与 `scripts/` 一起作为项目级 skill 使用。macOS Safari 版依赖系统 Safari 与 AppleScript；Chromium 版需要浏览器开启 CDP 调试端口；BrowserSkill 版需要 `bsk` CLI、扩展与已连接的 Profile。

详情与调用示例见 [SKILL.md](SKILL.md)。

## 来源

三个 bridge 脚本基于 [Antigravity2gptweb](https://github.com/yvochehk-oss/Antigravity2gptweb) 的 `macos` 分支整理，保留了目标会话绑定、消息提交检查和结构化退出码。此仓库专注 Codex 主导的交互流程，不包含旧版 GitHub 远端改码编排器。
