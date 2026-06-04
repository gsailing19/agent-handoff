# 04 — Handoff 文档规范

Handoff 文档是 Goal 之间唯一的上下文传递通道。下一阶段的 Agent 不读对话历史，只读这份文档。

## 文件约定

```
.claude/agent-handoffs/{session-id}/
├── 01-{name}-report.md
├── 01-{name}-report.md.done     ← 写完 .md 后 touch 这个，下游等它出现才读
├── 02-{name}-report.md
├── 02-{name}-report.md.done
└── ...
```

## 六段式结构

| Section | 标题 | Goal 接力场景下的特殊要求 |
|---------|------|--------------------------|
| 1 | What Was Done | **至少 400 字**。包含所有关键实现细节、函数签名、数据结构字段列表。下游 Agent 只靠这个理解你做了什么 |
| 2 | Output Artifacts | 新增/修改/删除的文件完整路径列表 + 代码行数统计 |
| 3 | Decisions and Trade-offs | 技术决策和原因。比如"为什么用 walkdir 而不用 std::fs::read_dir" |
| 4 | Concerns and Caveats | 已知限制、未完成的部分、需要下游特别注意的点 |
| 5 | Next Agent Actions | **给下游 Agent 的明确指令**：读什么文件、加什么 mod 声明、改什么函数。不是建议，是指令 |
| 6 | Verification Results | Goal 验证步骤的执行输出（命令 + 结果），让下游 Agent 相信"代码是可用的" |

## Handoff 模板

使用现有模板 `~/.claude/templates/agent-handoff-template.md`，但 Section 1 和 Section 5 必须严格按照上表要求填写。

简版：

```markdown
---
agent_role: "{角色}"
task_id: "{goal-id}"
session_id: "{session-id}"
sequence: {序号}
status: "written"
handoff_type: "summary"
---

# Agent Handoff: {角色} — {任务}

## 1. What Was Done
[至少 400 字，包含所有关键实现细节]

## 2. Output Artifacts
[文件路径列表 + 行数统计]

## 3. Decisions and Trade-offs
[技术决策和原因]

## 4. Concerns and Caveats
[已知限制、需要下游注意的点]

## 5. Next Agent Actions
[给下游的明确指令]

## 6. Verification Results
[验证命令和输出]
```

## .done 标记文件

写 handoff 的 Agent 在文件写完、确认完整后，执行 `touch {path}.done`。

读 handoff 的 Agent 在读取前，必须先检查 `.done` 文件是否存在。不存在 = 文件可能还在写，不能读。
