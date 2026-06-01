# AHP 系统架构

## 定位

AHP 是 Coordinator 的**持久化外部记忆**，不是 Agent 间直连通道。Claude Code 的多 Agent 是 Hub-and-Spoke 架构——子 Agent 之间不直接通信，所有信息通过 Coordinator 中转。AHP 让 Coordinator 用文件系统替代自己的压缩上下文来传递上游结果给下游。

## 整体架构

```
┌─ 规则层（全局，所有项目生效）────────────────────┐
│                                                    │
│  ~/.claude/CLAUDE.md                               │
│  ├── "文件优先于上下文" 核心原则                    │
│  ├── Session-ID 生成规则                           │
│  ├── 进化触发语引用                                │
│  └── 校验脚本引用                                  │
│                                                    │
│  ~/.claude/rules/agent-handoff.md                  │
│  ├── 完整协议规范（角色职责 + 文件约定 + 原子性）   │
│  ├── 文件生命周期策略                              │
│  └── META 自我进化规则                             │
│                                                    │
│  ~/.claude/templates/agent-handoff-template.md     │
│  └── YAML frontmatter + 五段正文 + handoff-end     │
│                                                    │
└────────────────────────────────────────────────────┘
         ↓ 被引用                ↓ 被引用
┌─ Skill 层 ────────────────────────────────────────┐
│                                                    │
│  subagent-driven-development                       │
│  ├── SKILL.md (File-Based Handoff 必选节)          │
│  ├── implementer-prompt.md (写文件 + .done)        │
│  ├── spec-reviewer-prompt.md (读文件 + 写审查)     │
│  └── code-quality-reviewer-prompt.md (读双文件)    │
│                                                    │
│  write-draft (12 Agent 三层流水线)                 │
│  ├── research_mgr → 4 研究员(并行) → 汇总          │
│  ├── outline_mgr → 3 设计师(并行) → 汇总           │
│  └── draft_mgr → writer_agent → citation_agent     │
│                                                    │
└────────────────────────────────────────────────────┘
         ↓ 运行时写入
┌─ 执行层（全局，所有项目生效）─────────────────────┐
│                                                    │
│  ~/.claude/settings.json                           │
│  ├── PreToolUse Hook (Agent)                       │
│  │   └── 触发 → pre-agent-handoff-check.sh        │
│  │       检查 prompt 是否含 ## Handoff Files       │
│  │       缺失 → exit 2 阻塞 dispatch              │
│  └── PostToolUse Hook (Write + Bash)               │
│       └── 触发 → hook-validate-handoff.sh          │
│                                                    │
│  ~/.claude/scripts/                                │
│  ├── pre-agent-handoff-check.sh (dispatch 前检查)  │
│  │   ├── 只拦截 Agent 工具调用                     │
│  │   ├── Explore/Plan 自动跳过                     │
│  │   ├── 检查 4 个必需要素                         │
│  │   └── 缺失时输出修复指引                        │
│  ├── handoff-init.sh (生成 handoff prompt 块)      │
│  │   ├── 自动生成 session-id (uuidgen)             │
│  │   ├── 自动计算序号                              │
│  │   └── 输出完整 ## Handoff Files 节             │
│  ├── validate-handoff.py (完整校验器)              │
│  │   ├── 文件存在 + 大小                           │
│  │   ├── .done 标记                                │
│  │   ├── YAML frontmatter (8 必填字段 + 枚举)      │
│  │   ├── 五段正文完整性                            │
│  │   ├── handoff-end 标记                          │
│  │   ├── 占位内容检测 (中英文)                     │
│  │   ├── 分段长度检查                              │
│  │   ├── Section 5 可执行性检查                    │
│  │   ├── 失败日志写入 (~/.claude/logs/)            │
│  │   └── 失败记录查看 (--recent-failures)          │
│  └── hook-validate-handoff.sh (Hook 入口)          │
│      ├── 解析 Write/Bash 工具输入                  │
│      ├── 过滤非 handoff 路径                       │
│      └── 调用 validate-handoff.py                  │
│                                                    │
│  ~/.claude/logs/                                   │
│  └── handoff-failures.jsonl (失败日志)             │
│                                                    │
└────────────────────────────────────────────────────┘
         ↓ 运行时写入
┌─ 数据层（项目级，临时文件）───────────────────────┐
│                                                    │
│  {project}/.claude/agent-handoffs/                 │
│  └── {session-id}/                                 │
│      ├── 01-{role}-report.md                       │
│      ├── 01-{role}-report.md.done                  │
│      └── ...                                       │
│                                                    │
└────────────────────────────────────────────────────┘
```

## 组件清单

### 规则与模板（4 文件）

| 文件 | 位置 | 作用域 |
|------|------|--------|
| 全局 CLAUDE.md | `~/.claude/CLAUDE.md` | 所有项目 |
| 协议规范 | `~/.claude/rules/agent-handoff.md` | 所有项目 |
| Handoff 模板 | `~/.claude/templates/agent-handoff-template.md` | 所有项目 |
| 项目 CLAUDE.md | `{project}/CLAUDE.md` | cc 项目 |

### Skill 集成（17 文件）

| Skill | 文件数 | 集成方式 |
|-------|--------|---------|
| subagent-driven-development | 4 | SKILL.md + 3 prompt 模板加 Handoff Protocol |
| write-draft | 13 | SKILL.md + 12 Agent 定义加 Handoff Protocol |

### 执行脚本（4 文件）

| 文件 | 位置 | 作用 |
|------|------|------|
| validate-handoff.py | `~/.claude/scripts/` | 校验器（~390 行） |
| hook-validate-handoff.sh | `~/.claude/scripts/` | PostToolUse Hook 入口（~50 行） |
| pre-agent-handoff-check.sh | `~/.claude/scripts/` | PreToolUse Hook 入口（~57 行） |
| handoff-init.sh | `~/.claude/scripts/` | Handoff prompt 块生成器（~51 行） |

### 配置（1 文件）

| 文件 | 位置 | 内容 |
|------|------|------|
| settings.json | `~/.claude/settings.json` | PostToolUse: Write + Bash 匹配器 |

### 运行时数据（自动生成）

| 路径 | 内容 |
|------|------|
| `{project}/.claude/agent-handoffs/{session-id}/` | Handoff 文件（临时） |
| `~/.claude/logs/handoff-failures.jsonl` | 失败日志（持久） |

## 数据流

```
                    Coordinator (主 Agent)
                    │                  │
               dispatch A          dispatch B
                    │                  │
              ┌─────▼─────┐      ┌─────▼─────┐
              │  Agent A  │      │  Agent B  │
              │  完成任务  │      │  读 A 的   │
              │  写 handoff│      │  handoff   │
              │  文件 +    │      │  文件      │
              │  .done     │      │  完成任务  │
              └─────┬─────┘      └─────┬─────┘
                    │                  │
              返回: "✅ Handoff   返回: 结果
              written to 01-     
              report.md"
                    │                  │
              Coordinator 只收到      Coordinator 不需要
              50 字节路径引用         记住 A 的完整输出
              (不会被压缩破坏)        (文件在磁盘上)
```

**关键**：Coordinator 的上下文只过路径引用（~50 字节），完整内容在文件系统。压缩只影响路径字符串——路径被压缩后仍然是同一个路径。

---

## 与 Claude Code 原生架构的关系

Claude Code 的 Hub-and-Spoke 架构中，子 Agent 彼此隔离——每个子 Agent 只接收 Coordinator 的 task description 字符串，完成后返回 summary 文本。AHP 不改变这个架构，只是在 Coordinator 的"传递上下文"环节用文件引用替代文本转述。

## 安全边界

- **人类把关**：协议修改、规则更新需人类确认后执行
- **不自动改代码**：进化机制只分析日志提建议，不自动修改文件
- **校验隔离**：Hook 失败不影响普通文件写入（只拦截 handoff 路径）
- **日志不膨胀**：失败日志 JSONL 格式，单条 < 1KB，可手动清理
