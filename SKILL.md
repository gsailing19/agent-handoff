---
name: agent-handoff
description: >
  TWO PRODUCTS, ONE INSTALL.

  Product 1 — Agent Handoff Protocol (AHP): file-based inter-agent communication.
  Use when dispatching multiple agents, orchestrating agent pipelines, coordinating
  parallel subagents, or running text-intensive multi-agent tasks (research, analysis,
  writing) where upstream output must survive context compression.

  Product 2 — Goal Relay (multi-step task splitting): methodology for breaking large
  tasks into independent goals. Use when the user needs to split a complex task into
  sequential steps, wants a Master Plan with copy-paste-ready goal prompts, or asks
  about "goal relay", "goal 接力", "拆 goal", "多 goal", "多步任务", "分步执行",
  "master plan". Also trigger for large refactors, multi-phase migrations, or any
  task where the user expresses concern about context window quality degrading over
  long conversations.

  Do NOT trigger for single-agent tasks, casual mentions of "agent" in non-tool
  contexts (e.g. "travel agent", "browser user-agent"), or simple one-shot tasks.
---

# Agent Handoff Protocol — Skill

**这个仓库包含两个产品。先判断你需要哪个：**

| 你的情况 | 用这个 | 怎么做 |
|---------|--------|--------|
| 要在多个 Agent 之间传递信息、防止上下文压缩丢失 | **AHP 协议** | 继续往下读 |
| 要把一个大任务拆成多个 Goal 分步执行 | **Goal Relay** | 告诉我你的任务，我自动读取方法论并输出方案 |
| 两个都要 | **都用** | 先读下文了解 AHP，再用 Goal Relay 拆任务 |

---

## Product 1: Agent Handoff Protocol (AHP)

### 问题

Claude Code 的多 Agent 架构是 Hub-and-Spoke。Coordinator 分发子 Agent、收集结果、传递给下一个。Agent A 和 Agent B 之间夹着 Coordinator 的上下文窗口——当上下文被压缩时，上游 Agent **高达 80% 的信息**在到达下游 Agent 之前就丢失了。

### 解决方案

AHP 完全绕过 Coordinator 的上下文。Agent 把完整输出写到磁盘文件，下游 Agent 直接读文件。Coordinator 只传递文件路径（~50 字节），不传递内容本身。

```
没有 AHP：Agent A → Coordinator → [80% 丢失] → Agent B
有 AHP：  Agent A → file.md → Agent B 直接读
          Coordinator：".claude/agent-handoffs/xxx/01-report.md"（50 字节，零丢失）
```

### 核心约定

**三个角色**：Producer（写文件）、Consumer（读文件）、Controller（协调者）

**文件格式**：`.claude/agent-handoffs/{session-id}/{seq}-{role}-report.md`
- YAML frontmatter + 5 个 body section
- `.done` 标记文件保证原子性（下游 Agent 等 `.done` 出现后才读）
- 模板：`templates/agent-handoff-template.md`

**Controller 检查清单**（每次 Agent 返回后执行）：
```bash
ls -la .claude/agent-handoffs/{session-id}/{seq}-{role}-report.md   # 文件存在？
wc -c ...                                                            # ≥ 200 字节？
ls -la ...done                                                       # .done 标记存在？
```

### 脚本

| 脚本 | 用途 |
|------|------|
| `scripts/validate-handoff.py` | 校验 handoff 文件完整性（退出码 0=通过, 1=警告, 2=阻断） |
| `scripts/handoff-init.sh` | 生成 `## Handoff Files` 提示词块 |
| `scripts/hook-validate-handoff.sh` | PostToolUse hook —— 自动校验 |
| `scripts/pre-agent-handoff-check.sh` | PreToolUse hook —— 检查 Agent 提示词含 handoff 指令 |

### 安装

```bash
git clone https://github.com/gsailing19/agent-handoff.git ~/.claude/skills/agent-handoff/
```

重启 Claude Code。Skill 自动发现。

如需 hooks 自动校验，把 `examples/settings-hooks.json` 合并到 `~/.claude/settings.json`。

---

## Product 2: Goal Relay（多步任务接力）

### 问题

一个复杂任务从头跑到尾，到后期 Agent 会忘记早期的设计决策、混淆相似模块、产出不一致的代码。`/goal` 命令解决了"自动跨轮继续"，但没有解决"上下文膨胀导致质量下降"。

### 解决方案

把大任务拆成 N 个独立 Goal，每个 Goal 在新对话中运行（干净上下文），通过 AHP 的 handoff 文件串起来。

### 触发方式

直接告诉我你的任务，比如：

> "我要把 Python 扫描引擎迁移到 Rust，涉及 30 个文件、约 3000 行代码。"

我会自动读取 `goal-relay/` 下的方法论文档，判断模式，然后输出一份完整的 Master Plan——包含 session-id、每个 Goal 的可粘贴提示词、handoff 路径、操作说明。

你不需要懂任何方法论细节。拿到 Master Plan 后照着操作即可。

### 三种模式

| 模式 | 什么时候用 |
|------|-----------|
| A | 你已有方案文档 → 我读方案 → 拆 Goal → 输出 Master Plan |
| B | 你只有需求 → 我先设计方案 → 再拆 Goal → 输出 Master Plan |
| C | 你想手动审查每步 → 我输出 Master Plan → 每步你粘贴到新对话跑，回来确认后再继续 |

### 手动使用

如果你不想走编排者自动模式，也可以直接读方法论文档：

> "读 goal-relay/00-orchestrator-prompt.md，按指示执行。"

---

## 参考文档

| 文档 | 什么时候读 |
|------|-----------|
| [AHP Protocol Spec](docs/protocol.md) | 需要了解 AHP 的角色、文件约定、并行协调 |
| [AHP Architecture](docs/architecture.md) | 需要了解系统设计 |
| [AHP Scripts Reference](docs/scripts.md) | 需要了解脚本用法和退出码 |
| [Goal Relay: Orchestrator](goal-relay/00-orchestrator-prompt.md) | Goal Relay 编排者入口 |
| [Goal Relay: Goal Template](goal-relay/03-goal-template.md) | 需要了解 Goal 提示词怎么写 |
| [Goal Relay: FAQ](goal-relay/07-faq.md) | Goal Relay 常见问题 |
