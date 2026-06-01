#!/bin/bash
# handoff-init.sh — 生成 Agent Handoff prompt 块
# 用法: bash handoff-init.sh <role> <task-id> [session-id]
# 输出: 可直接插入 Agent prompt 的 ## Handoff Files 节

set -euo pipefail

ROLE="${1:?Usage: $0 <role> <task-id> [session-id]}"
TASK_ID="${2:?}"
SESSION_ID="${3:-}"

# 生成 session-id（如果未提供）
if [ -z "$SESSION_ID" ]; then
    SESSION_ID="$(date +%Y%m%d-%H%M%S)-$(uuidgen 2>/dev/null | head -c8 || python3 -c 'import uuid; print(uuid.uuid4().hex[:8])' 2>/dev/null || openssl rand -hex 4 2>/dev/null || echo $RANDOM | md5 | head -c4)"
fi

# 自动计算序号（检查目录中已有文件数 + 1）
HANDOFF_DIR=".claude/agent-handoffs/${SESSION_ID}"
mkdir -p "$HANDOFF_DIR"
EXISTING=$(find "$HANDOFF_DIR" -name "*.md" ! -name "*.done" 2>/dev/null | wc -l | tr -d ' ')
SEQ=$(printf "%02d" $((EXISTING + 1)))

HANDOFF_PATH=".claude/agent-handoffs/${SESSION_ID}/${SEQ}-${ROLE}-report.md"

# Auto-detect install method and find the template
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# If we're inside a skill directory (scripts/ is under a skill root with SKILL.md), use skill template path
if [ -f "$SCRIPT_DIR/../SKILL.md" ]; then
    TEMPLATE_PATH="$SCRIPT_DIR/../templates/agent-handoff-template.md"
else
    # Traditional install — scripts were copied to ~/.claude/scripts/, template to ~/.claude/templates/
    TEMPLATE_PATH="$HOME/.claude/templates/agent-handoff-template.md"
fi

cat << BLOCK

## Handoff Files

### Output (write your complete report here)
- \`${HANDOFF_PATH}\`

### Output Rules
1. Write your COMPLETE report using the template format from \`${TEMPLATE_PATH}\`
   - YAML frontmatter: \`agent_role: "${ROLE}"\`, \`task_id: "${TASK_ID}"\`, \`session_id: "${SESSION_ID}"\`, \`sequence: ${SEQ}\`, \`status: "written"\`, \`handoff_type: "full"\`
   - 5 required sections (What Was Done / Output Artifacts / Decisions / Concerns / Next Agent Actions)
2. End the file with \`<!-- handoff-end -->\`
3. Create .done marker: \`touch ${HANDOFF_PATH}.done\`

### Agent Return Value
Write ONLY: \`✅ Handoff written to \\\`${HANDOFF_PATH}\\\`. Summary: {one sentence}\`

### CRITICAL
- The handoff file is the SOURCE OF TRUTH. Write EVERYTHING there.
- Your Agent return value is SECONDARY (it gets compressed).
- Do NOT put important content only in the return value.
BLOCK

# 同时输出元数据到 stderr（供脚本调用者使用）
echo "SESSION_ID=${SESSION_ID}" >&2
echo "HANDOFF_PATH=${HANDOFF_PATH}" >&2
echo "SEQ=${SEQ}" >&2
