# Goal 接力工作法

> 一套让 AI 编程 Agent 在多步大型任务中保持上下文干净、产出质量稳定的方法论。
>
> **属于 [Agent Handoff](https://github.com/gsailing19/agent-handoff) 仓库。** 依赖 AHP 的 handoff 文件约定和校验基础设施。
>
> **支持 Agent**：Claude Code、Codex。

---

## 快速上手

**方式一（推荐）：通过 AHP Skill 自动触发**

如果你已安装 AHP skill（`git clone` 到 `~/.claude/skills/agent-handoff/`），直接在 Claude Code 里说你的任务即可。SKILL.md 会自动路由到编排者模式。

> "我要把 Python 扫描引擎迁移到 Rust，涉及 30 个文件。"

Claude 自动读方法论 → 判断模式 → 输出 Master Plan。

**方式二：手动指定入口文件**

```
读 goal-relay/00-orchestrator-prompt.md，按指示执行。
```

---

## 文档索引

| 序号 | 文件 | 内容 | 什么时候读 |
|------|------|------|-----------|
| 0 | `00-orchestrator-prompt.md` | **编排者入口** | 每次用这套方法论时，第一个读它 |
| 1 | `01-problem-and-scope.md` | 解决什么问题、适用范围 | 第一次接触 |
| 2 | `02-usage-modes.md` | 三种使用方式 | 决定用了，想知道怎么开始 |
| 3 | `03-goal-template.md` | Goal 提示词六要素 + 模板 | **核心文件** |
| 4 | `04-handoff-template.md` | Handoff 文档规范 | 写完成条件时参考 |
| 5 | `05-splitting-guide.md` | 拆 Goal 的原则 | 不确定怎么拆的时候看 |
| 6 | `06-verification.md` | 三层验证链 | 想知道怎么保证不出错 |
| 7 | `07-faq.md` | 常见问题 | 有疑问时翻 |
| 8 | `08-real-example.md` | 真实案例 | 想看完整实例 |
| 9 | `09-manual-relay-mode.md` | 手动接力模式（人在回路） | 想主动审查每步产出 |
