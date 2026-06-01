#!/bin/bash
# PreToolUse hook: 在 Agent dispatch 前检查 prompt 是否包含 handoff 指令
# stdin: JSON with tool_name, tool_input (prompt, description)
# 只在多 Agent 场景（使用 Agent 工具）时触发

JSON=$(cat)
TOOL_NAME=$(echo "$JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null) || TOOL_NAME=""

# 只拦截 Agent 工具
if [ "$TOOL_NAME" != "Agent" ]; then
    exit 0
fi

PROMPT=$(echo "$JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('prompt',''))" 2>/dev/null) || PROMPT=""
SUBTYPE=$(echo "$JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('subagent_type',''))" 2>/dev/null) || SUBTYPE=""

# Explore 和 Plan 是只读/设计型 agent，不需要 handoff
if [ "$SUBTYPE" = "Explore" ] || [ "$SUBTYPE" = "Plan" ]; then
    exit 0
fi

# 显式声明不需要 handoff 的任务
if echo "$PROMPT" | grep -q "## No Handoff Required"; then
    exit 0
fi
# 检查 prompt 中是否包含 handoff 指令
HAS_HANDOFF_SECTION=$(echo "$PROMPT" | grep -c "## Handoff Files" || true)
HAS_HANDOFF_PATH=$(echo "$PROMPT" | grep -cE "agent-handoffs/[^/]+/[0-9]+-.*-report\.md" || true)
HAS_DONE_INSTRUCTION=$(echo "$PROMPT" | grep -cE "\.done|handoff-end" || true)
HAS_RETURN_FORMAT=$(echo "$PROMPT" | grep -c "Handoff written" || true)

MISSING=()

if [ "$HAS_HANDOFF_SECTION" -eq 0 ]; then
    MISSING+=("## Handoff Files section")
fi
if [ "$HAS_HANDOFF_PATH" -eq 0 ]; then
    MISSING+=("handoff file path (e.g., .claude/agent-handoffs/{session-id}/{seq}-{role}-report.md)")
fi
if [ "$HAS_DONE_INSTRUCTION" -eq 0 ]; then
    MISSING+=(".done marker instruction (touch {path}.done)")
fi
if [ "$HAS_RETURN_FORMAT" -eq 0 ]; then
    MISSING+=("Agent return value format (✅ Handoff written to ...)")
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "::error::Agent dispatch BLOCKED — prompt missing handoff instructions:" >&2
    for m in "${MISSING[@]}"; do
        echo "  ❌ Missing: $m" >&2
    done
    echo "" >&2
    echo "Fix: Run 'bash scripts/handoff-init.sh <role> <task-id>'" >&2
    echo "     Then copy the output into your Agent prompt." >&2
    echo "" >&2
    echo "If this is NOT a multi-agent task (single agent, no handoff needed)," >&2
    echo "add '## No Handoff Required' to the prompt to bypass this check." >&2
    exit 2
fi

exit 0
