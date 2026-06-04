<p align="center">
  <img src="logo/agent-handoff-logo-256.png" alt="Agent Handoff Logo" width="96" height="96">
</p>

# Agent Handoff — AHP + Goal Relay

**一个仓库，两个工具。**

| | Agent Handoff Protocol | Goal Relay |
|------|------------------------|------------|
| **解决什么** | 多个 Agent 之间传递信息，防止上下文压缩丢失 80% 内容 | 大任务拆成多个 Goal，每个 Goal 干净上下文独立运行 |
| **什么时候用** | 调度多个 Agent、并行子任务、文本密集型多 Agent 工作流 | 大型重构、分阶段迁移、多模块顺序实现、需要人在回路的质量把关 |
| **怎么触发** | Claude Code 在多 Agent 场景自动加载 | 告诉我你的任务，我自动读方法论并输出 Master Plan |
| **产出** | 结构化的 handoff 文件（`.done` 保证原子性） | 完整的 Master Plan：session-id + 每个 Goal 的可粘贴提示词 + 操作说明 |

---

## 安装（一行）

```bash
git clone https://github.com/gsailing19/agent-handoff.git ~/.claude/skills/agent-handoff/
```

重启 Claude Code。两个工具同时就绪，无需分别安装。

> **可选**：把 `examples/settings-hooks.json` 合并到 `~/.claude/settings.json` 以获得自动 handoff 校验。

---

## 快速开始

### 用 AHP（Agent 间传递信息）

当你调度多个 Agent 时，告诉每个 Agent handoff 文件路径即可。SKILL.md 中的规范会自动生效。

详细协议见 [docs/protocol.md](docs/protocol.md)。

### 用 Goal Relay（大任务分步执行）

直接在 Claude Code 中说你的任务，比如：

> "我要把 2000 行的认证模块从 JWT 迁到 OAuth，涉及 15 个文件"

Claude 自动读方法论 → 判断模式 → 输出 Master Plan。你拿到后照着操作就行。

---

## 文档

| 文档 | 内容 |
|------|------|
| [AHP 协议规范](docs/protocol.md) | 角色、文件约定、原子性（`.done`）、检查清单 |
| [AHP 架构](docs/architecture.md) | 系统设计 |
| [AHP 模板](docs/template.md) | Handoff 文件格式 |
| [AHP 脚本](docs/scripts.md) | 4 个脚本的用法和退出码 |
| [AHP 验证报告](docs/verification.md) | 31/31 测试通过 |
| [AHP 自进化](docs/evolution.md) | 失败日志分析 + 人类把关 |
| [AHP 规则](rules/agent-handoff.md) | 协议完整规范文本 |
| [Goal Relay 编排者入口](goal-relay/00-orchestrator-prompt.md) | 编排者自动模式入口 |
| [Goal Relay 目录](goal-relay/) | 完整方法论（10 个文件） |

---

## License

MIT — see [LICENSE](LICENSE)
