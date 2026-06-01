# AHP 协议规范

## 背景：Claude Code 的多 Agent 架构

Claude Code 的多 Agent 是 Hub-and-Spoke 模式。Coordinator（主 Agent）派发子 Agent，子 Agent 独立完成任务后将结果返回 Coordinator。Coordinator 再将这些信息传递给下一个子 Agent。

**问题**：Coordinator 的对话上下文会被压缩。当 Coordinator 把上游结果转述给下游时，压缩导致的信息丢失可达 80%。

**AHP 的方案**：Coordinator 不亲自"记住"和"转述"上游结果。上游子 Agent 将完整输出写入文件，下游子 Agent 自己读文件。Coordinator 只传递文件路径引用——路径不会被压缩破坏。

## 1. 核心规则

### 1.1 Handoff 文件是 Source of Truth

Agent 工具返回值（对话上下文中的返回文本）是**次要索引**，会被压缩。Handoff 文件是**一手来源**，不会被压缩。下游 Agent 必须从 Handoff 文件获取信息，不能依赖 Controller 的口头转述。

### 1.2 生产方职责（写 Handoff 的 Agent）

- 将**完整输出**写入 `.claude/agent-handoffs/{session-id}/{seq}-{role}-report.md`
- 使用 [Handoff 模板](template.md) 格式（YAML frontmatter + 五段正文）
- `handoff_type` 字段：`full`（文本任务，Section 1 包含完整交付物）或 `summary`（代码任务，Section 1 包含决策和上下文）
- `status` 字段：写完后设为 `"written"`
- 写完文件后创建 `.done` 标记：`touch {path}.done`
- 文件末尾包含 `<!-- handoff-end -->` 完整性标记
- Agent 返回值只写：`✅ Handoff written to \`{path}\`。摘要：{一句话}`
- **严禁把重要内容只放在返回值里**——返回值会被压缩

### 1.3 消费方职责（读 Handoff 的 Agent）

- **第一步**：用 Read 工具读取所有上游 Handoff 文件
- 检查 `.done` 标记存在后再信任文件内容
- 从 Handoff 文件获取完整上下文，不从 Controller 的摘要转述中推断
- 如果 Handoff 文件中信息不足以完成任务，明确报告需要什么
- 如果 Controller 转述的内容与 Handoff 文件不一致，**以 Handoff 文件为准**

### 1.4 Controller 职责（协调者）

- 确定 session-id（优先环境变量 → uuidgen → Python uuid → openssl → bash RANDOM 四级 fallback）
- 创建 handoff 目录（如不存在）
- 在 Agent prompt 中明确指定 handoff 文件路径
- 向下游 Agent 传递上游 handoff 文件路径，**不自行总结内容**
- 每次 Agent 返回后执行三步检查（文件存在 + 大小 ≥ 200B + .done 存在）
- 如果上游 Agent 只写了返回值没写文件，**要求它补写**
- 默认串行 dispatch，SKILL.md 明确要求并行时允许并行（需在各 Agent 全部返回后检查所有文件）
- 同一 Agent 最多重试 3 次，超限停止并报告用户

## 2. 文件约定

### 2.1 目录结构

```
.claude/agent-handoffs/
└── {session-id}/
    ├── 01-{role}-report.md
    ├── 01-{role}-report.md.done
    ├── 02-{role}-report.md
    ├── 02-{role}-report.md.done
    └── ...
```

### 2.2 命名规则

- `{session-id}` — 格式 `YYYYMMDD-HHMMSS-xxxxxxxx`，优先使用 uuidgen（128 位熵）
- `{seq}` — 两位序号（01, 02, 03...），按执行顺序递增
- `{role}` — Agent 角色名（implementer, spec-reviewer, code-quality-reviewer, researcher, writer 等）

### 2.3 Session-ID 生成

```bash
SESSION_ID="$(date +%Y%m%d-%H%M%S)-$(uuidgen 2>/dev/null | head -c8 || python3 -c 'import uuid; print(uuid.uuid4().hex[:8])' 2>/dev/null || openssl rand -hex 4 2>/dev/null || echo $RANDOM | md5 | head -c4)"
```

生成后检查目录是否冲突，如冲突追加 `-2` 后缀。

### 2.4 .gitignore

```
.claude/agent-handoffs/*
!.claude/agent-handoffs/.gitkeep
```

Handoff 文件不纳入版本控制。

## 3. 原子性与防丢失机制

### 3.1 `.done` 标记文件

Agent 写入 handoff 文件不是原子操作。为防止下游 Agent 读到半写入文件，使用 `.done` 标记：

1. Agent 将完整内容写入 `{path}.md`
2. Agent 创建空标记文件 `touch {path}.md.done`
3. 下游 Agent 读取前先检查 `.done` 是否存在
4. `.done` 只由写 Agent 创建，不预先创建

### 3.2 `status` 字段枚举

| 值 | 含义 |
|----|------|
| `writing` | 正在写入，内容可能不完整 |
| `written` | 写入完成，`.done` 已就绪 |
| `verified` | 下游 Agent 已确认内容完整可读 |

### 3.3 `<!-- handoff-end -->` 完整性标记

文件末尾必须包含此标记，校验脚本将其缺失视为致命错误（exit code 2）。

### 3.4 Controller 三步检查

```bash
ls -la .claude/agent-handoffs/{session-id}/{seq}-{role}-report.md      # 存在？
wc -c .claude/agent-handoffs/{session-id}/{seq}-{role}-report.md       # ≥200B？
ls -la .claude/agent-handoffs/{session-id}/{seq}-{role}-report.md.done # .done？
```

任一失败 → 重新 dispatch Agent。

## 4. 调度规则

### 4.1 默认串行

多步骤任务拆成单步骤逐个 dispatch。避免 Agent 进入 Plan Mode 不执行。每个 Agent prompt 末尾加：
```
Do NOT plan. Do NOT ask for confirmation. Just execute and report done.
```

### 4.2 并行例外

SKILL.md 明确要求并行调度（如 write-draft 的 4 研究员并行），且技能已定义等待和合并逻辑时，允许并行。Controller 在所有并行 Agent 返回后逐个检查 handoff 文件，全部通过后才继续。

### 4.3 重试上限

同一 Agent 最多重试 3 次。超过后停止并报告用户。

## 5. PostToolUse Hook（自动校验）

全局配置在 `~/.claude/settings.json`：

- **匹配 Write 工具**：每次写文件时检查是否为 handoff 文件
- **匹配 Bash 工具**：检测 `cat/tee/cp/mv/touch` 命令中的 handoff 路径
- 自动运行完整校验（YAML frontmatter + 五段 + 占位检测 + 长度检查 + handoff-end）
- 校验失败（exit 2）→ 阻塞写入，错误发送回模型自修
- `.done` 文件和非 handoff 路径自动跳过

## 6. 文件生命周期

Handoff 文件是**临时中间产物**：

| 阶段 | 行为 |
|------|------|
| 任务进行中 | 保留（Agent 间需要读取） |
| 任务完成后当次会话 | 保留（调试追溯） |
| 会话结束后 | 可安全删除 |
| 永久保留 | 迁移到 `docs/decisions/` 或 MEMORY.md |

---

> 最后更新: 2026-05-31 — 初始版本
