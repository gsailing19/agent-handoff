#!/bin/bash
# PostToolUse hook: 在 Write 或 Bash 写入 handoff 文件后触发完整校验
# stdin: JSON with tool_name, tool_input

JSON=$(cat)
TOOL_NAME=$(echo "$JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null) || TOOL_NAME=""

# 提取文件路径
FILE_PATH=""
if [ "$TOOL_NAME" = "Write" ]; then
    FILE_PATH=$(echo "$JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null) || FILE_PATH=""
elif [ "$TOOL_NAME" = "Bash" ]; then
    CMD=$(echo "$JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null) || CMD=""
    # 只检测实际写入 agent-handoffs 的命令（cat/tee/cp/mv/touch 到 agent-handoffs 路径）
    if echo "$CMD" | grep -qE "(cat|tee|cp|mv|touch).*agent-handoffs"; then
        FILE_PATH=$(echo "$CMD" | grep -oE '[^ ]*agent-handoffs/[^ ]+\.md' | head -1) || FILE_PATH=""
    fi
fi

# 不需要校验的情况：路径为空、不是 handoff 文件、是 .done 文件
if [ -z "$FILE_PATH" ]; then
    exit 0
fi
if ! echo "$FILE_PATH" | grep -q "agent-handoffs"; then
    exit 0
fi
if echo "$FILE_PATH" | grep -q "\.done$"; then
    exit 0
fi

# 校验脚本
# Find validator — self-locating: resolves next to this script regardless of install path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATOR="$SCRIPT_DIR/validate-handoff.py"

if [ ! -f "$VALIDATOR" ]; then
    echo "::error::Validator not found at: $VALIDATOR" >&2
    echo "::error::Expected validate-handoff.py in same directory as this hook script ($SCRIPT_DIR/)" >&2
    exit 2
fi

# 完整校验
OUTPUT=$("$VALIDATOR" "$FILE_PATH" 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 2 ]; then
    echo "::error::Handoff validation FAILED for $FILE_PATH" >&2
    echo "$OUTPUT" >&2
    exit 2
elif [ $EXIT_CODE -eq 1 ]; then
    # 警告不阻塞
    echo "::warning::Handoff validation warnings for $FILE_PATH: $OUTPUT" >&2
fi
exit 0
