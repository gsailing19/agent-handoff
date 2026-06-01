# AHP 脚本参考

## validate-handoff.py

**路径**：`~/.claude/scripts/validate-handoff.py`（全局）  
**语言**：Python 3.10+，零依赖（仅 stdlib）  
**行数**：~390 行

### 校验维度

| 类别 | 检查项 | 严重程度 |
|------|--------|:---:|
| 存在性 | 文件存在 | 致命 |
| 存在性 | 文件大小 ≥ 200 字节 | 致命 |
| 原子性 | `.done` 标记文件存在 | 警告 |
| 格式 | YAML frontmatter 存在（文件以 `---` 开头） | 致命 |
| 格式 | 8 个必填字段完整（agent_role, task_id, session_id, sequence, status, created, handoff_type, summary） | 致命 |
| 格式 | status 值 ∈ {writing, written, verified} | 致命 |
| 格式 | status = "written" | 警告 |
| 格式 | handoff_type 值 ∈ {full, summary} | 致命 |
| 格式 | created 为 ISO 8601 格式 | 警告 |
| 结构 | 5 个 Section 全部存在 | 致命 |
| 完整性 | `<!-- handoff-end -->` 标记 | 致命 |
| 内容 | Section 1 ≥ 200 字符, Sections 2-5 各有最小长度 | 警告 |
| 内容 | 无中英文占位文本（N/A, TBD, None, TODO, WIP, [待写] 等） | 致命 |
| 内容 | Section 5 包含可执行动词 | 警告 |

### 命令

```bash
# 校验单个文件
python3 ~/.claude/scripts/validate-handoff.py <file.md>

# 校验单个文件 + 失败时写日志
python3 ~/.claude/scripts/validate-handoff.py --log-failures <file.md>

# 轻量检查（仅存在性 + .done）
python3 ~/.claude/scripts/validate-handoff.py --check-done <file.md>

# 校验整个目录
python3 ~/.claude/scripts/validate-handoff.py --dir <directory>

# 查看最近 20 条失败记录
python3 ~/.claude/scripts/validate-handoff.py --recent-failures

# 查看最近 50 条
python3 ~/.claude/scripts/validate-handoff.py --recent-failures -n 50
```

### 退出码

| 码 | 含义 | Hook 行为 |
|:--:|------|---------|
| 0 | 全部通过 | 放行 |
| 1 | 有警告 | 记录警告，放行 |
| 2 | 有致命错误 | **阻塞写入**，错误发送回模型 |

### 失败日志格式

```json
{
  "timestamp": "2026-05-31T12:21:29+00:00",
  "file": "/path/to/handoff.md",
  "error_types": ["handoff_end_missing", "done_missing"],
  "error_count": 2,
  "errors": ["⚠️ .done 标记缺失", "❌ 缺少完整性标记"]
}
```

日志位置：`~/.claude/logs/handoff-failures.jsonl`

### 11 种自动错误分类

| error_type | 含义 |
|-----------|------|
| `file_missing` | 文件不存在 |
| `frontmatter_missing` | 缺少 YAML frontmatter |
| `frontmatter_field_missing` | frontmatter 必填字段缺失 |
| `status_invalid` | status 枚举值无效 |
| `handoff_type_invalid` | handoff_type 枚举值无效 |
| `section_missing` | Section 标题缺失 |
| `handoff_end_missing` | 缺少 `<!-- handoff-end -->` |
| `placeholder_content` | 包含占位文本 |
| `content_too_short` | Section 内容低于最小长度 |
| `no_actionable_steps` | Section 5 无动作动词 |
| `date_format` | created 日期格式错误 |

---

## hook-validate-handoff.sh

**路径**：`~/.claude/scripts/hook-validate-handoff.sh`（全局）  
**语言**：Bash  
**行数**：~50 行

### 工作流

```
stdin JSON (tool_name + tool_input)
  │
  ├── tool_name = "Write" → 提取 file_path
  ├── tool_name = "Bash"  → 解析命令中的 agent-handoffs 路径
  │
  ├── 路径不包含 "agent-handoffs" → exit 0 (跳过)
  ├── 路径是 .done 文件 → exit 0 (跳过)
  │
  └── 路径是 handoff .md 文件 → 调用 validate-handoff.py (完整校验)
       ├── exit 0 → 放行
       ├── exit 1 → 警告（放行）
       └── exit 2 → 阻塞 + stderr 发送回模型
```

### 配置

在 `~/.claude/settings.json` 中：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [{
          "type": "command",
          "command": "bash ~/.claude/scripts/hook-validate-handoff.sh",
          "timeout": 15,
          "async": false,
          "statusMessage": "🔍 校验 handoff 文件..."
        }]
      },
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "bash ~/.claude/scripts/hook-validate-handoff.sh",
          "timeout": 15,
          "async": false,
          "statusMessage": "🔍 校验 handoff 文件 (Bash)..."
        }]
      }
    ]
  }
}
```

### 安全边界

- 非 handoff 路径的 Write/Bash 不触发校验
- `.done` 文件不触发校验
- 校验脚本不存在时 exit 2（宁可阻塞也不错放）
- 15 秒超时防止卡死

---

## handoff-init.sh

**路径**：`~/.claude/scripts/handoff-init.sh`（全局）  
**语言**：Bash · ~51 行

### 用途

自动生成 `## Handoff Files` prompt 块，Controller 直接复制到 Agent prompt 中，消除手写路径的出错风险。

### 命令

```bash
bash ~/.claude/scripts/handoff-init.sh <role> <task-id> [session-id]
```

### 自动化

- session-id：uuidgen → Python uuid → openssl → bash RANDOM 四级 fallback
- 序号：自动扫描 handoff 目录已有文件数 +1
- 目录：自动创建

---

## pre-agent-handoff-check.sh

**路径**：`~/.claude/scripts/pre-agent-handoff-check.sh`（全局）  
**语言**：Bash · ~57 行

### 用途

PreToolUse Hook 入口——Agent dispatch 前检查 prompt 是否包含 handoff 指令。缺失则 exit 2 阻塞 dispatch。

### 工作流

```
Agent 工具调用
  ├── 非 Agent 工具 → 跳过
  ├── Explore/Plan → 跳过（只读 agent 不需要 handoff）
  └── 检查 4 个必需要素：
       ├── ## Handoff Files 节
       ├── handoff 文件路径
       ├── .done 标记指令
       └── 返回值格式 (✅ Handoff written to)
  exit 2 时输出：缺什么 + 怎么修（运行 handoff-init.sh）
```

绕过：单 Agent 任务加 `## No Handoff Required`。

---

## 三层防御

| 时机 | Hook | 脚本 | 拦截什么 |
|------|------|------|---------|
| dispatch 前 | PreToolUse(Agent) | pre-agent-handoff-check.sh | prompt 缺 handoff 指令 |
| 写入后 | PostToolUse(Write/Bash) | hook-validate-handoff.sh | 文件格式错误 |
| 返回后 | Controller 手动 | validate-handoff.py | 文件缺失/过小 |
