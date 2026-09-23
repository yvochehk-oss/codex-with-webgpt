# codex-with-webgpt

这是一个供 Codex 使用的 skill：Codex 通过**内置浏览器 + Computer Use** 向用户指定的 ChatGPT 网页对话发送一个阶段任务，读取该阶段的新回复，核验结果，再决定后续工作。仓库只包含 skill 说明和使用文档；不需要浏览器扩展、CDP 端口或独立桥接脚本，也不需要开启开发者模式的完整 CDP 访问。

## 准备

1. 在本机用 **GitHub CLI** 登录要使用的 GitHub 账号，并检查当前账号：

   ```bash
   gh auth login --hostname github.com --git-protocol ssh --web
   gh auth status
   ```

   已登录时只需运行 `gh auth status`。使用 GitHub 仓库之前，Codex 应核对当前账号、仓库地址和 Git 远端。GitHub CLI 登录用于本机拉取、提交和推送；它不会替 ChatGPT 网页授权 GitHub。

2. 确认 Codex 当前环境能够使用 Computer Use 控制内置浏览器。在内置浏览器中登录 [ChatGPT](https://chatgpt.com/)，打开希望协作的已有对话，复制完整地址 `https://chatgpt.com/c/<conversation-id>`。交互式登录由用户自己完成；不要把账号密码或验证码发给 Codex。
3. 将本仓库的 `SKILL.md` 放到 `~/.codex/skills/codex-with-webgpt/SKILL.md`，然后在 Codex 中提出任务，并附上目标对话的完整地址。已安装过该 skill 时，用仓库中的新版本覆盖即可。

## 使用过程

1. 用户告诉 Codex 任务和目标 ChatGPT 对话地址；需要 GitHub 文件协作时，另说清目标仓库及允许的操作范围。
2. Codex 检查 GitHub CLI 登录状态，精确绑定指定网页对话，记下发送前的最后一个助手回合。
3. Codex 把当前工作整理成一个范围明确、可以核验的阶段任务，在该对话发送一次，并确认页面出现对应的新用户消息。
4. Codex 等待其后的**新助手回合**生成完毕，读取完整回复。发送是否成功或回复是否完整不明确时，先检查会话，不直接重复可能产生副作用的操作。
5. Codex 核验网页端所声称的文件、提交、测试或外部结果，然后决定完成、补证、修正或发送下一阶段任务。最终向用户报告已核验的结果与仍未验证的部分。

例如，可以向 Codex 说：

> 使用 `codex-with-webgpt`，通过内置浏览器与这个对话协作：`https://chatgpt.com/c/<conversation-id>`。目标是……。如需修改 GitHub 仓库，请使用我已登录的 GitHub CLI 账号，并将操作限制在……。

完整的执行规则与阶段提示模板见 [SKILL.md](SKILL.md)。

## 权限说明

本机 `gh` 登录、ChatGPT 网页登录，以及 ChatGPT 会话内可能存在的 GitHub 连接，是三种不同的状态。Codex 不会因为本机已登录 `gh`，就假设网页端也能读写 GitHub。网页端的回复需要由 Codex 用实际文件、提交和运行结果核对。
