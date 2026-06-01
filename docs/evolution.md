# AHP 自我进化机制

AHP 不是静态协议。它包含轻量级自我进化能力：自动记录失败 → 人工触发分析 → 人类确认改进。

## 进化记录

| 日期 | 触发 | 改动 |
|------|------|------|
| 2026-06-01 | write 项目生产审计：26 session、23 handoff 文件、发现 Session-ID 散射 + 空目录 + 文件方差 15x | 模板加角色字数指引（editor 800字、reader 500字等），确认 PreToolUse + handoff-init 已覆盖前两项 |
| 2026-05-31 | chan 项目生产故障：3 Agent 全未写 handoff | 新增 dispatch 前三层防御：PreToolUse(Agent) Hook + handoff-init.sh + pre-agent-handoff-check.sh |
| 2026-05-31 | 二次红队审计 | 修复 Hook 轻量校验盲区、Bash 绕过、CLAUDE.md 规则矛盾等 7 项 |
| 2026-05-31 | 一次红队审计 | 新增 .done 标记、status 枚举、session-id 生成、文件检查步骤 |

## 设计原则

- **不自动修改**：进化机制只分析、只建议，不自主修改协议或代码
- **人类把关**：所有改进需人类确认后才执行
- **数据驱动**：基于实际失败日志，不基于假设
- **零额外依赖**：复用现有 `validate-handoff.py` 的日志功能

## 失败日志

### 自动记录

`validate-handoff.py --log-failures` 校验失败时自动追加到 `~/.claude/logs/handoff-failures.jsonl`。

Hook 自动携带 `--log-failures` 标志，无需手动操作。

### 日志格式

```json
{
  "timestamp": "2026-05-31T12:21:29+00:00",
  "file": "/path/to/handoff.md",
  "error_types": ["handoff_end_missing"],
  "error_count": 2,
  "errors": ["⚠️ .done 标记缺失", "❌ 缺少完整性标记"]
}
```

### 查看失败记录

```bash
# 最近 20 条（按错误类型分组 + 最近 5 条详情）
python3 ~/.claude/scripts/validate-handoff.py --recent-failures

# 最近 50 条
python3 ~/.claude/scripts/validate-handoff.py --recent-failures -n 50
```

## 进化触发语

当发现重复性 handoff 故障时，对 Controller 说：

> **"分析最近的 handoff 失败记录，抽象出重复模式，提出对协议的改进方案。"**

### Controller 会做什么

1. 读取 `~/.claude/logs/handoff-failures.jsonl`
2. 识别重复出现的错误类型（如 80% 的失败是 `handoff_end_missing`）
3. 识别哪个 Agent 角色最容易出问题（如 writer_agent 频繁缺 Section 4）
4. 分析根因：
   - 模板问题？（Section 说明不够清晰）
   - 规则问题？（协议没强制某项检查）
   - 校验缺失？（某个常见错误没被 validate-handoff.py 覆盖）
   - Prompt 问题？（Agent prompt 模板里的指令被忽略）
5. 提出具体修改建议（更新协议规则 / 加强校验逻辑 / 修改模板措辞 / 调整 prompt）
6. **等待人类确认**后再执行修改

### 不会做什么

- ❌ 不自动修改 `agent-handoff.md`
- ❌ 不自动修改 `validate-handoff.py` 的校验逻辑
- ❌ 不自动修改 `CLAUDE.md`
- ❌ 不自动修改 Skill 的 prompt 模板
- ❌ 不在无人确认的情况下执行任何文件变更

## META 规则

在 `agent-handoff.md` 的 META 节中定义了写规则的规则：

### 必须遵守

1. **用"必须"/"严禁"开头**——模糊建议在 Agent 上下文中会被忽略
2. **先说为什么**——1-2 句解释这个规则解决什么问题
3. **给具体命令**——不要只说"检查文件"，给出 `ls -la` 或具体的 Python 命令
4. **一条规则解决一个问题**——不塞多个不相关的规则
5. **控制长度**——每条规则 ≤10 行，协议总长 ≤200 行

### 避免

- 给显而易见的规则加长篇解释
- 重复其他文件已有的内容
- 添加未经实际 handoff 失败证明过的"预防性"规则
- 用段落解释列表能说清的内容

### 修改后同步

- 在协议顶部标注更新日期和简述
- 如果新增了校验需求，同步更新 `validate-handoff.py`

## 进化示例

### 场景

失败日志显示：writer_agent 频繁出现 `section_missing`（缺 Section 3 或 4），连续 8 次。

### 触发

> "分析最近的 handoff 失败记录，抽象出重复模式，提出对协议的改进方案。"

### Controller 分析

```
📊 最近 20 条失败记录中：
   section_missing: ████████████ 12 次 (60%)
   content_too_short: ████ 4 次 (20%)
   handoff_end_missing: ██ 2 次 (10%)

section_missing 的详细分布：
   Section 3 (Decisions): 8 次 — writer_agent 和 citation_agent
   Section 4 (Concerns): 4 次 — 同上

根因分析：
   模板中 Section 3/4 的引导文字是英文（"Decisions and Trade-offs"），
   而 write-draft 的 Agent 主要处理中文内容，
   Agent 可能认为这两个 Section 只适用于代码任务。
```

### 建议

```
建议 1（模板）：在模板 Section 3/4 的注释中加中文说明
建议 2（prompt）：在 writer_agent/citation_agent 的 Handoff Protocol 中
              加一句 "Sections 3 和 4 必须填写，即使是中文任务也要写"
```

### 执行

人类确认后，Controller 修改模板和两个 Agent 定义文件。

---

## 与 claude-meta 的关系

AHP 的自我进化直接借鉴了 [claude-meta](https://github.com/aviadr1/claude-meta) 的核心理念：

| 概念 | claude-meta | AHP |
|------|-----------|-----|
| META 规则 | 在 CLAUDE.md 中 | 在 agent-handoff.md META 节中 |
| 触发语 | "Reflect, abstract, generalize, add to CLAUDE.md" | "分析最近的 handoff 失败记录，抽象出重复模式，提出改进方案" |
| 把关机制 | 人工审查 | 人工确认后才执行 |
| 失败记录 | 无（依赖会话上下文） | 结构化 JSONL 日志 |

AHP 多了失败日志的结构化记录和统计分析（`--recent-failures`），这是对 claude-meta 模式的实际增强。

---

> 最后更新: 2026-05-31 — 初始版本
