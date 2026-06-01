# Agent Handoff 协议

## 适用范围

任何使用 Agent 工具进行多 Agent 协作的工作流，包括但不限于：
- 同一任务串行调用多个 Agent（Agent A → Agent B → Agent C）
- 并行调用多个 Agent 后汇总
- `subagent-driven-development` 等 skill 的多 Agent 流水线
- 文本密集型任务（研究、分析、写作、内容创作）——强制要求
- 代码任务（决策、理由、注意事项的传递）——强制要求

## 核心规则

### 1. Handoff 文件是 Source of Truth

Agent 工具返回值（对话上下文中的返回文本）是**次要索引**，会被压缩。Handoff 文件是**一手来源**，不会被压缩。下游 Agent 必须从 Handoff 文件获取信息，不能依赖 Controller 的口头转述。

### 2. 生产方职责（写 Handoff 的 Agent）

- 将**完整输出**写入 `.claude/agent-handoffs/{session-id}/{seq}-{role}-report.md`
- 使用 `~/.claude/templates/agent-handoff-template.md` 中的模板格式
- YAML frontmatter 的 `handoff_type` 字段：
  - `full`：文本密集型任务，Section 1 包含**完整交付物**
  - `summary`：代码任务，Section 1 包含决策和上下文（代码在 git 中）
- YAML frontmatter 的 `status` 字段：设为 `"written"`（表示写入完成）
- **写入完成后，创建 `.done` 标记文件**：`touch {path}.md.done`
- Agent 返回值只写：`✅ Handoff 写入 \`{path}\`。摘要：{一句话}`
- **不要把重要内容只放在返回值里**——返回值会被压缩

### 3. 消费方职责（读 Handoff 的 Agent）

- **第一步**：用 Read 工具读取所有上游 Handoff 文件
- 从 Handoff 文件获取完整上下文，不从 Controller 的摘要转述中推断
- 如果 Handoff 文件中信息不足以完成任务，明确报告需要什么
- 如果你发现 Controller 转述的内容与 Handoff 文件不一致，**以 Handoff 文件为准**

### 4. Controller 职责（协调者）

- 确定当前 session-id（会话 UUID 前 6 位）
- 创建 handoff 目录（如不存在）
- 在 Agent prompt 中明确指定 handoff 文件路径
- 向下游 Agent 传递上游 handoff 文件路径，**不自行总结内容**
- 如果上游 Agent 只在返回值中写了重要内容而没有写入 handoff 文件，**要求它补写**
- **并行 Agent 等待机制**：当任务调度了多个并行 Agent，Controller 必须在所有并行 Agent 全部完成后才继续下一步。不能在任何并行 Agent 还在运行时就进入下游步骤。

### 5. 原子性与防丢失机制（Fatal 级别防护）

#### 5a. `.done` 标记文件约定

Agent 写入 handoff 文件本身不是原子操作。为防止下游 Agent 读到半写入的文件，**必须使用 `.done` 标记文件作为写入完成的信号**。

流程：
1. Agent 将完整内容写入 `{path}.md`
2. Agent 创建空的 `{path}.md.done` 文件（`touch {path}.md.done`）
3. 下游 Agent 在读取前**先检查 `.done` 文件是否存在**，不存在则等待或报错
4. `.done` 文件只由写 Agent 创建，不预先创建

注意：写入 `.done` 文件前，Agent 必须先关闭 `.md` 文件的文件句柄（或确保 flush）。

#### 5b. `status` 字段枚举

handoff 模板 YAML frontmatter 中的 `status` 字段必须为以下三个值之一：

| 值 | 含义 |
|----|------|
| `writing` | 正在写入文件，内容可能不完整（文件存在但 `.done` 不存在时= `writing`） |
| `written` | 文件写入完成，`.done` 已就绪，等待下游消费 |
| `verified` | 下游 Agent 已读取并确认内容完整、可读（由下游 Agent 在确认后标记） |

Agent 写入 handoff 文件后，`status` 字段写 `"written"`。Controller 和下游 Agent 应根据 `status: "written"` + `.done` 存在来判断文件是否可以安全读取。

#### 5c. 文件存在性检查（Controller Checklist 强制步骤）

Controller 在**每次 Agent 返回后**必须执行以下检查步骤：

```bash
# 第一步：检查文件是否存在
ls -la .claude/agent-handoffs/{session-id}/{seq}-{role}-report.md

# 第二步：检查文件大小（至少 200 字节，防止空洞文件）
wc -c .claude/agent-handoffs/{session-id}/{seq}-{role}-report.md

# 第三步：检查 .done 标记文件是否存在
ls -la .claude/agent-handoffs/{session-id}/{seq}-{role}-report.md.done
```

如果文件不存在、size < 200 字节、或 `.done` 不存在，**立即重新 dispatch Agent**，prompt 中添加：
> "You forgot to write the handoff file. Ensure you write the full report to the specified path, then create the `.done` marker with `touch {path}.done`."

## 文件约定

### 目录结构

```
.claude/agent-handoffs/
├── {session-id}/
│   ├── 01-{role}-report.md
│   ├── 02-{role}-report.md
│   └── ...
```

### 命名规则

- `{session-id}` = 当前会话 UUID 前 6 位
- `{seq}` = 两位序号（01, 02, 03...），按执行顺序递增
- `{role}` = Agent 角色名（implementer, spec-reviewer, code-quality-reviewer, researcher, writer 等）

### Session-ID 生成规则

Controller 按以下优先级确定 session-id：

1. **从环境变量读取**（如果 Claude Code 提供）：检查 `$CLAUDE_SESSION_ID`、`$ANTHROPIC_SESSION_ID`、`$CLAUDE_CONVERSATION_ID` 是否存在。
2. **从 Claude Code 内部数据读取**：部分版本在 session 数据目录中包含 UUID。
3. **手动生成（兜底）**：如果以上都不可用，Controller 用以下命令生成 session-id：
   ```bash
   SESSION_ID="$(date +%Y%m%d-%H%M%S)-$(uuidgen 2>/dev/null | head -c8 || python3 -c 'import uuid; print(uuid.uuid4().hex[:8])' 2>/dev/null || openssl rand -hex 4 2>/dev/null || echo $RANDOM | md5 | head -c4)"
   ```
   优先使用 `uuidgen`（128 位熵），依次 fallback 到 Python uuid、openssl、最后才是 bash RANDOM（仅 15 位熵）。格式 `YYYYMMDD-HHMMSS-xxxxxxxx`。

4. **碰撞检测**：生成 session-id 后，检查 `.claude/agent-handoffs/{id}/` 目录是否已存在。如存在且非当前任务，追加计数器：
   ```bash
   if [ -d ".claude/agent-handoffs/$SESSION_ID" ]; then
     SESSION_ID="${SESSION_ID}-2"
   fi
   ```

### 模板

完整模板见 `~/.claude/templates/agent-handoff-template.md`

## 检查清单

Controller 在每次 Agent 调用后检查：

- [ ] Agent 是否写入了 handoff 文件？（`ls -la {path}` 确认文件存在，size >= 200 bytes）
- [ ] `.done` 标记文件是否存在？（`ls -la {path}.done`）
- [ ] YAML frontmatter 中 `status` 是否为 `"written"`？
- [ ] handoff 文件是否包含完整内容（不是空洞的摘要）？
- [ ] Agent 返回值是否只包含文件路径和一句话摘要？
- [ ] 下游 Agent 的 prompt 中是否指定了要读取的 handoff 文件路径？
- [ ] 并行 Agent 场景：是否所有并行 Agent 都已返回且文件验证通过？

## 文件生命周期

Handoff 文件是**临时中间产物**，不是永久记录。它们在 Agent 间传递信息，任务完成后即失去主要价值。

### 保留策略

| 阶段 | 行为 |
|------|------|
| 任务进行中 | 保留全部 handoff 文件（Agent 间还需要读取） |
| 任务完成后当次会话 | 保留（用于调试和问题追溯） |
| 会话结束后 | **可安全删除**。有价值的决策如需永久保留，应迁移到 `docs/decisions/` 或项目文档 |

### 清理方式

```bash
# 清理所有 handoff 文件
rm -rf .claude/agent-handoffs/*/

# 只清理已完成任务的目录（status: verified 的）
python3 scripts/validate-handoff.py --dir .claude/agent-handoffs/{session-id}/
# 全部通过后：
rm -rf .claude/agent-handoffs/{session-id}/
```

Handoff 目录不会被 git 追踪（via `.gitignore`）。

### 什么需要永久保留

以下信息应该从 handoff 文件中提取并保存到项目文档，而不是依赖临时 handoff 文件：

- 架构决策 → `docs/decisions/`
- 关键数据发现 → 项目 MEMORY.md
- 测试结果 → commit message 或 PR description
- 已知限制 → 代码注释或 issue

---

## META — 本协议的自我进化

### 失败日志

所有 handoff 校验失败自动记录到 `~/.claude/logs/handoff-failures.jsonl`。查看最近失败：

```bash
python3 ~/.claude/scripts/validate-handoff.py --recent-failures
python3 ~/.claude/scripts/validate-handoff.py --recent-failures -n 50  # 最近 50 条
```

### 触发进化（人类把关）

当发现重复性 handoff 故障时，对 Controller 说：

> **"分析最近的 handoff 失败记录，抽象出重复模式，提出对协议的改进方案。"**

Controller 会：
1. 读取 `~/.claude/logs/handoff-failures.jsonl`
2. 识别重复出现的错误类型和 Agent 角色
3. 分析根因（是模板问题？规则问题？校验缺失？）
4. 提出具体修改建议（更新协议规则 / 加强校验逻辑 / 修改模板）
5. **等待人类确认后再执行修改**（绝不自动改规则）

### 写规则的规则（META-Rules）

当向本协议添加新内容时，遵循以下原则：

**必须遵守：**
1. 用"必须"/"严禁"开头——模糊的建议在 Agent 上下文中会被忽略
2. 先说为什么——1-2 句解释这个规则解决什么问题
3. 给具体命令——不要只说"检查文件"，给出 `ls -la` 或 `python3 validate-handoff.py` 命令
4. 一条规则解决一个问题——不要在一个段落里塞多个不相关的规则
5. 控制长度——每条规则不超过 10 行，本文件总长不超过 200 行

**避免：**
- ❌ 给显而易见的规则加长篇解释
- ❌ 重复其他文件已有的内容（如 CLAUDE.md 中的内容）
- ❌ 添加未经实际 handoff 失败证明过的"预防性"规则
- ❌ 用段落解释列表能说清的内容

**每次修改后：**
- 在顶部加 `> 最后更新: YYYY-MM-DD — 简述改动` 注释
- 如果新增了校验需求，同步更新 `~/.claude/scripts/validate-handoff.py`

下游 Agent 在开始工作前检查：

- [ ] 每个指定 handoff 文件的 `.done` 标记是否存在？（不存在 = 文件可能未写完，必须等待或报错）
- [ ] 是否已读取所有指定的 handoff 文件？
- [ ] 是否理解了上游 Agent 的完整输出（不是 Controller 的转述）？
