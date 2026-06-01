<p align="center">
  <img src="logo/agent-handoff-logo-256.png" alt="Agent Handoff Logo" width="128" height="128">
</p>

# Agent Handoff Protocol (AHP)

<p align="center">
  <strong>基于文件的多 Agent 间通信协议，专为 Claude Code 多智能体协作设计。</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="docs/verification.md"><img src="https://img.shields.io/badge/%E6%B5%8B%E8%AF%95-31%2F31%20%E9%80%9A%E8%BF%87-green" alt="Tests"></a>
</p>
<p align="center">
  <a href="README.md">
    <img src="logo/lang-en.svg" alt="English" height="48">
  </a>
</p>

## 问题

Claude Code 的多 Agent 采用 Hub-and-Spoke 架构：Coordinator（协调者）派发子 Agent，收集结果，再把结果传给下一个 Agent。Agent A 和 Agent B 之间隔着 Coordinator 的上下文窗口——当上下文被压缩时，上游 Agent **最多 80% 的信息**会在到达下游之前丢失。

这对文本密集型任务是致命的：研究报告丢失数据点，分析报告丢失细节，大纲丢失结构。Coordinator 成了一个有损的中间人。

## 解决方案

AHP 完全绕过 Coordinator 的上下文。Agent 不再让 Coordinator "记住和转述"结果，而是把完整输出写入文件。下游 Agent 直接读取原始文件。Coordinator 只传递文件路径（约 50 字节），不传递内容本身。

```
没有 AHP：  Agent A → Coordinator → [丢失 80%] → Agent B
有了 AHP：  Agent A → file.md → Agent B 直接读取原文
                    Coordinator 只传："{路径}"（50 字节，零损失）
```

## 工作原理

1. **Agent 写入**完整输出到 `.claude/agent-handoffs/{session-id}/{seq}-{role}-report.md`
2. **Agent 标记完成**，创建 `.done` 标记文件
3. **Coordinator 只传文件路径**给下一个 Agent
4. **下游 Agent 直接读取**原始文件——无压缩、无转述、无信息丢失

系统通过 Hook 强制约束：PreToolUse 检查 Agent prompt 是否包含 handoff 指令，PostToolUse 校验输出文件，Python 校验器检查文件完整性、YAML frontmatter、章节结构和内容质量。

## 文档

| 文档 | 内容 |
|------|------|
| [协议规范](docs/protocol.md) | 角色职责、文件约定、原子性机制（`.done`）、检查清单 |
| [系统架构](docs/architecture.md) | 四层架构设计、组件关系、数据流、部署 |
| [模板说明](docs/template.md) | Handoff 文件格式——YAML frontmatter + 五段正文 |
| [脚本参考](docs/scripts.md) | 4 个脚本详解——用法、退出码、错误分类 |
| [验证报告](docs/verification.md) | 31/31 测试通过，信息保真度对比 |
| [进化机制](docs/evolution.md) | 自我改进——故障日志、META 规则、人类把关 |

## 快速上手

### 1. 安装

```bash
cp scripts/* ~/.claude/scripts/
cp templates/agent-handoff-template.md ~/.claude/templates/
cp rules/agent-handoff.md ~/.claude/rules/
```

### 2. 配置 Hook

将 [examples/settings-hooks.json](examples/settings-hooks.json) 中的 hook 合并到 `~/.claude/settings.json`。

### 3. 生成 session 和 handoff 块

```bash
SESSION_ID="$(date +%Y%m%d-%H%M%S)-$(uuidgen | head -c8)"
mkdir -p .claude/agent-handoffs/$SESSION_ID
```

在 Agent prompt 中加入：

```
## Handoff Files
### Output
- .claude/agent-handoffs/{session-id}/01-{role}-report.md

After writing: touch {path}.done
Return only: ✅ Handoff written to `{path}`. Summary: {one sentence}
```

### 4. 校验

```bash
python3 scripts/validate-handoff.py <handoff-file>
python3 scripts/validate-handoff.py --recent-failures
```

### 5. 触发协议进化

> "分析最近的 handoff 失败记录，抽象出重复模式，提出对协议的改进方案。"

## 架构一览

| 层 | 内容 | 位置 |
|----|------|------|
| 规则层 | 协议规范 + 核心原则 | `~/.claude/rules/agent-handoff.md` |
| 模板层 | Handoff 文件模板 | `~/.claude/templates/agent-handoff-template.md` |
| 执行层 | 脚本 + Hook + 校验器 | `~/.claude/scripts/` + `~/.claude/settings.json` |

## 集成的 Skills

- **subagent-driven-development** — implementer → spec-reviewer → code-quality-reviewer
- **write-draft** — 12 Agent 三层流水线：研究 → 大纲 → 撰写

## License

MIT — 详见 [LICENSE](LICENSE)
