---
agent_role: ""
task_id: ""
session_id: ""
sequence: 0
status: "written"
created: ""
handoff_type: ""
summary: ""
tags: []
---

# Agent Handoff: {role} — {task}

## 1. What Was Done

[文本密集型任务：这里是完整交付物，不是摘要。代码任务：关键决策、理由、上下文]

**各角色最低字数指引**：

| 角色类型 | Section 1 最低 | 说明 |
|---------|:---:|------|
| researcher / fact_check / language / devil_advocate / reader | 500 字 | 审稿/研究报告需包含完整分析和证据 |
| editor_in_chief | 800 字 | 主编报告需覆盖全部上游 Agent 的结论 + 独立判断 |
| revision_agent | 300 字 | 修改报告需逐项列出修改内容 |
| implementer / writer | 400 字 | 代码任务包含决策和上下文，文本任务包含完整交付物 |
| 其他 | 200 字 | 校验脚本的最低通过线，低于此线会被拦截 |

**"终局验证"/"final" 轮也不例外**——即使是最后一轮，仍需要完整报告。下游 Agent（editor_in_chief 或 publish skill）依赖你的完整输出来做最终判断。

## 2. Output Artifacts

[文件路径、commit SHA、测试结果、数据引用]

## 3. Decisions and Trade-offs

[为什么这样做而不那样做。考虑过但放弃的替代方案。这不是事后合理化——记录真实权衡过程]

## 4. Concerns and Caveats

[已知限制。需要下游 Agent 特别注意的点。不确定是否正确的地方]

## 5. Next Agent Actions

[给下游 Agent 的明确指令：读什么、查什么、验证什么、做什么]

<!-- handoff-end -->
