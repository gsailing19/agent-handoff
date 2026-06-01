#!/usr/bin/env python3
"""validate-handoff.py — Agent Handoff 文件格式校验器

用法:
    python3 validate-handoff.py <filepath>          # 校验单个 handoff 文件
    python3 validate-handoff.py --dir <directory>   # 校验目录下所有 handoff 文件
    python3 validate-handoff.py --check-done <path> # 只检查 .done 和基础存在性（轻量）

退出码:
    0 = 全部通过
    1 = 格式问题（可自动修复）
    2 = 严重问题（需人工介入）
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── 常量 ──────────────────────────────────────────

MIN_FILE_SIZE = 200  # 字节
FAILURE_LOG = os.path.expanduser("~/.claude/logs/handoff-failures.jsonl")
REQUIRED_SECTIONS = [
    "What Was Done",
    "Output Artifacts",
    "Decisions and Trade",
    "Concerns and Caveat",
    "Next Agent Action",
]
REQUIRED_FRONTMATTER_FIELDS = [
    "agent_role",
    "task_id",
    "session_id",
    "sequence",
    "status",
    "created",
    "handoff_type",
    "summary",
]
VALID_STATUSES = {"writing", "written", "verified"}
VALID_HANDOFF_TYPES = {"full", "summary"}
HANDOFF_END_MARKER = "<!-- handoff-end -->"


# ── 校验函数 ───────────────────────────────────────

def check_file_exists(path: str) -> list[str]:
    errors = []
    if not os.path.exists(path):
        errors.append(f"❌ 文件不存在: {path}")
    elif os.path.getsize(path) < MIN_FILE_SIZE:
        errors.append(f"❌ 文件过小: {os.path.getsize(path)}B < {MIN_FILE_SIZE}B")
    return errors


def check_done_marker(md_path: str) -> list[str]:
    errors = []
    done_path = f"{md_path}.done"
    if not os.path.exists(done_path):
        errors.append(f"⚠️  .done 标记缺失: {done_path} — 上游 Agent 可能未完成写入")
    return errors


def check_yaml_frontmatter(content: str, path: str) -> list[str]:
    errors = []
    parts = content.split("---")
    if len(parts) < 3 or not content.startswith("---"):
        errors.append("❌ 缺少 YAML frontmatter（文件不以 '---' 开头）")
        return errors

    # 尝试简单解析 YAML（不依赖 pyyaml）
    frontmatter_text = parts[1]
    for field in REQUIRED_FRONTMATTER_FIELDS:
        if not re.search(rf"^{field}:\s*\S", frontmatter_text, re.MULTILINE):
            errors.append(f"❌ frontmatter 缺少必填字段: {field}")

    # 校验 status 枚举
    status_match = re.search(r"^status:\s*\"?(\w+)\"?", frontmatter_text, re.MULTILINE)
    if status_match:
        status_val = status_match.group(1)
        if status_val not in VALID_STATUSES:
            errors.append(f"❌ status 值无效: '{status_val}' (允许: {', '.join(VALID_STATUSES)})")
        if status_val != "written":
            errors.append(f"⚠️  status 不是 'written': 当前为 '{status_val}'")

    # 校验 handoff_type 枚举
    type_match = re.search(r"^handoff_type:\s*\"?(\w+)\"?", frontmatter_text, re.MULTILINE)
    if type_match:
        type_val = type_match.group(1)
        if type_val not in VALID_HANDOFF_TYPES:
            errors.append(f"❌ handoff_type 值无效: '{type_val}' (允许: {', '.join(VALID_HANDOFF_TYPES)})")

    # 校验 created 日期格式 (ISO 8601)
    date_match = re.search(r"^created:\s*\"?([\d\-T:+]+)\"?", frontmatter_text, re.MULTILINE)
    if date_match:
        try:
            datetime.fromisoformat(date_match.group(1))
        except ValueError:
            errors.append(f"⚠️  created 日期格式不是 ISO 8601: '{date_match.group(1)}'")

    return errors


def check_sections(content: str) -> list[str]:
    errors = []
    for i, section in enumerate(REQUIRED_SECTIONS, 1):
        pattern = rf"^##\s+{i}\.\s+{section}"
        if not re.search(pattern, content, re.MULTILINE):
            errors.append(f"❌ 缺少 Section {i}: '## {i}. {section}'")
    return errors


def check_handoff_end(content: str) -> list[str]:
    if HANDOFF_END_MARKER not in content:
        return ["❌ 缺少完整性标记: '<!-- handoff-end -->' — 文件可能未写完"]
    return []


def check_section_content(content: str) -> list[str]:
    """检查所有 5 个 Section 是否有实质内容（非占位）"""
    errors = []

    # 各 Section 最小字符数
    MIN_SECTION_CHARS = {
        1: 200,   # What Was Done — 核心交付物
        2: 30,    # Output Artifacts
        3: 50,    # Decisions and Trade-offs
        4: 30,    # Concerns and Caveats
        5: 50,    # Next Agent Actions
    }

    # 中英文占位文本
    placeholder_patterns = [
        # 中文
        r"^\s*\[.*?任务.*?\]\s*$",
        r"^\s*\[.*?内容.*?\]\s*$",
        r"^\s*\[.*?TODO.*?\]\s*$",
        r"^\s*\[.*?待.*?写.*?\]\s*$",
        # 英文
        r"^\s*N/?A\s*$",
        r"^\s*TBD\s*$",
        r"^\s*None\.?\s*$",
        r"^\s*TODO\s*$",
        r"^\s*WIP\s*$",
        r"^\s*Nothing\.?\s*$",
        r"^\s*Not applicable\.?\s*$",
    ]

    for section_num in range(1, 6):
        section_name = REQUIRED_SECTIONS[section_num - 1]
        pattern = rf"## {section_num}\.\s+{section_name}\n\n(.*?)(?=\n## {section_num + 1}\.|$)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            section_text = match.group(1).strip()
            # 长度检查
            min_chars = MIN_SECTION_CHARS.get(section_num, 50)
            if len(section_text) < min_chars:
                errors.append(f"⚠️  Section {section_num} 内容过短: {len(section_text)} 字符 (需 ≥{min_chars})")
            # 占位检测
            for pp in placeholder_patterns:
                if re.search(pp, section_text, re.MULTILINE):
                    errors.append(f"❌ Section {section_num} 包含占位文本: 匹配 '{pp}'")
                    break

    # Section 5 特殊检查：是否包含至少一个动作动词
    pattern5 = r"## 5\.\s+Next Agent Action.*?\n\n(.*?)(?=\n##|\Z)"
    match5 = re.search(pattern5, content, re.DOTALL)
    if match5:
        sec5 = match5.group(1).strip().lower()
        action_verbs = ["read", "verify", "check", "write", "review", "fix", "run", "test", "validate", "更新", "检查", "验证", "读取", "修复", "运行"]
        has_action = any(verb in sec5 for verb in action_verbs)
        if not has_action:
            errors.append("⚠️  Section 5 缺少可执行指令（建议包含 read/verify/check/write 等动词）")

    return errors


# ── 主入口 ─────────────────────────────────────────

def validate_file(path: str, check_done: bool = True, log_failures: bool = False) -> tuple[int, list[str]]:
    """校验单个 handoff 文件。返回 (exit_code, errors)。"""
    all_errors = []

    # 基础检查
    all_errors.extend(check_file_exists(path))
    if any(e.startswith("❌ 文件") for e in all_errors):
        if log_failures:
            _log_failure(path, "file_missing", all_errors)
        return 2, all_errors

    if check_done:
        all_errors.extend(check_done_marker(path))

    # 读取并校验内容
    with open(path, "r") as f:
        content = f.read()

    all_errors.extend(check_yaml_frontmatter(content, path))
    all_errors.extend(check_sections(content))
    all_errors.extend(check_handoff_end(content))
    all_errors.extend(check_section_content(content))

    # 判断严重程度
    has_critical = any(e.startswith("❌") for e in all_errors)
    has_warnings = any(e.startswith("⚠️") for e in all_errors)

    exit_code = 2 if has_critical else 1 if has_warnings else 0

    if log_failures and exit_code != 0:
        # 分类错误类型
        error_types = []
        if has_critical:
            for e in all_errors:
                if "文件不存在" in e: error_types.append("file_missing")
                elif "frontmatter" in e.lower() or "缺少 YAML" in e: error_types.append("frontmatter_missing")
                elif "必填字段" in e: error_types.append("frontmatter_field_missing")
                elif "status 值无效" in e or "status 不是" in e: error_types.append("status_invalid")
                elif "handoff_type" in e: error_types.append("handoff_type_invalid")
                elif "缺少 Section" in e: error_types.append("section_missing")
                elif "完整性标记" in e: error_types.append("handoff_end_missing")
                elif "占位文本" in e: error_types.append("placeholder_content")
        if has_warnings:
            for e in all_errors:
                if "内容过短" in e: error_types.append("content_too_short")
                elif "可执行指令" in e: error_types.append("no_actionable_steps")
                elif "日期格式" in e: error_types.append("date_format")
        _log_failure(path, list(set(error_types)), all_errors)

    return exit_code, all_errors


def _log_failure(path: str, error_types: list[str], errors: list[str]):
    """将校验失败记录写入日志（JSONL 格式）"""
    try:
        log_dir = os.path.dirname(FAILURE_LOG)
        os.makedirs(log_dir, exist_ok=True)

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "file": path,
            "error_types": error_types,
            "error_count": len(errors),
            "errors": errors,
        }
        with open(FAILURE_LOG, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 日志写入失败不应阻塞校验


def validate_dir(dirpath: str) -> tuple[int, list[str]]:
    """校验目录下所有 .md 文件（排除 .done 文件）"""
    all_files = sorted(Path(dirpath).glob("*.md"))
    md_files = [f for f in all_files if not f.name.endswith(".done")]
    if not md_files:
        return 1, [f"⚠️  目录下无 .md 文件: {dirpath}"]

    total_ok = 0
    total_warn = 0
    total_fail = 0

    for md_file in md_files:
        path = str(md_file)
        code, errors = validate_file(path, check_done=True)
        status = "✅" if code == 0 else "⚠️" if code == 1 else "❌"
        print(f"{status} {md_file.name}")
        for e in errors:
            print(f"   {e}")
        if code == 0:
            total_ok += 1
        elif code == 1:
            total_warn += 1
        else:
            total_fail += 1

    print(f"\n总计: {total_ok} 通过 / {total_warn} 警告 / {total_fail} 失败")
    return (2 if total_fail > 0 else 1 if total_warn > 0 else 0, [])


# ── CLI ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Agent Handoff 文件格式校验器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s .claude/agent-handoffs/abc123/01-implementer-report.md
  %(prog)s --dir .claude/agent-handoffs/abc123/
  %(prog)s --check-done .claude/agent-handoffs/abc123/01-implementer-report.md
  %(prog)s --recent-failures        # 查看最近 20 条失败记录
  %(prog)s --recent-failures -n 50  # 查看最近 50 条
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("file", nargs="?", help="Handoff 文件路径")
    group.add_argument("--dir", help="校验整个目录")
    group.add_argument("--recent-failures", action="store_true", help="查看最近失败记录")
    parser.add_argument("--check-done", action="store_true", help="只做轻量检查（存在性 + .done）")
    parser.add_argument("--log-failures", action="store_true", help="校验失败时写入日志")
    parser.add_argument("-n", "--num", type=int, default=20, help="失败记录条数 (配合 --recent-failures)")

    args = parser.parse_args()

    if args.recent_failures:
        _show_recent_failures(args.num)
        return
    elif args.dir:
        code, _ = validate_dir(args.dir)
    elif args.check_done:
        errors = []
        errors.extend(check_file_exists(args.file))
        errors.extend(check_done_marker(args.file))
        code = 2 if any(e.startswith("❌") for e in errors) else 1 if errors else 0
        for e in errors:
            print(e)
        if code == 0:
            print(f"✅ {args.file} 基础检查通过")
    else:
        code, errors = validate_file(args.file, log_failures=args.log_failures)
        for e in errors:
            print(e)
        if code == 0:
            print(f"✅ {args.file} 全部校验通过")

    sys.exit(code)


def _show_recent_failures(n: int):
    """显示最近 N 条失败记录，按错误类型分组"""
    if not os.path.exists(FAILURE_LOG):
        print("📭 暂无失败记录")
        return

    failures = []
    with open(FAILURE_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    failures.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not failures:
        print("📭 暂无失败记录")
        return

    failures = failures[-n:]  # 最近 N 条

    # 按错误类型分组统计
    type_counts = {}
    for f_entry in failures:
        for et in f_entry.get("error_types", ["unknown"]):
            type_counts[et] = type_counts.get(et, 0) + 1

    print(f"\n📊 最近 {len(failures)} 条失败记录")
    print(f"   日志位置: {FAILURE_LOG}\n")
    print("   错误类型分布:")
    for etype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        label = {
            "file_missing": "文件缺失",
            "frontmatter_missing": "缺少 YAML frontmatter",
            "frontmatter_field_missing": "frontmatter 字段缺失",
            "status_invalid": "status 值无效",
            "handoff_type_invalid": "handoff_type 无效",
            "section_missing": "Section 缺失",
            "handoff_end_missing": "缺少 handoff-end 标记",
            "placeholder_content": "占位文本",
            "content_too_short": "内容过短",
            "no_actionable_steps": "Section 5 无可执行指令",
            "date_format": "日期格式错误",
        }.get(etype, etype)
        bar = "█" * min(count, 20)
        print(f"   {label:30s} {bar} {count}")

    print(f"\n   最近 5 条详情:")
    for f_entry in failures[-5:]:
        ts = f_entry["timestamp"][:19].replace("T", " ")
        fname = os.path.basename(f_entry["file"])
        types_str = ", ".join(f_entry["error_types"])
        print(f"   [{ts}] {fname}")
        print(f"         类型: {types_str}")


if __name__ == "__main__":
    main()
