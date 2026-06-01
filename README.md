<p align="center">
  <img src="logo/agent-handoff-logo-256.png" alt="Agent Handoff Logo" width="128" height="128">
</p>

# Agent Handoff Protocol (AHP)

<p align="center">
  <strong>File-based inter-agent communication for Claude Code multi-agent collaboration.</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="docs/verification.md"><img src="https://img.shields.io/badge/tests-31%2F31%20passed-green" alt="Tests"></a>
  <a href="SKILL.md"><img src="https://img.shields.io/badge/Claude%20Code-Skill-blueviolet" alt="Claude Code Skill"></a>
</p>
<p align="center">
  <a href="README.zh-CN.md">
    <img src="logo/lang-zh.svg" alt="中文版" height="48">
  </a>
</p>

## Install as Skill (recommended)

```bash
git clone https://github.com/gsailing19/agent-handoff.git ~/.claude/skills/agent-handoff/
```

Verify the install:
```bash
ls ~/.claude/skills/agent-handoff/SKILL.md
```

Restart Claude Code. The skill auto-discovers via SKILL.md.

---

**Alternatively, [traditional install](#traditional-install) is available below.** Choose ONE method.

## Problem

Claude Code uses a Hub-and-Spoke architecture for multi-agent tasks: the Coordinator dispatches sub-agents, collects their results, then passes them on. Between Agent A and Agent B sits the Coordinator's context window — and when that context gets compressed, **up to 80% of the information** from the upstream agent can be lost before reaching the downstream agent.

This is fatal for text-intensive tasks: research reports lose data points, analysis loses nuance, outlines lose structure. The Coordinator becomes a lossy middleman.

## Solution

AHP bypasses the Coordinator's context entirely. Instead of the Coordinator paraphrasing upstream results, agents write their complete output to files on disk. Downstream agents read those files directly. The Coordinator only passes file paths (~50 bytes), never the content itself.

```
Without AHP:   Agent A → Coordinator → [80% loss] → Agent B
With AHP:      Agent A → file.md → Agent B reads it directly
                                  Coordinator: "{path}"  (50 bytes, zero loss)
```

## How It Works

1. **Agent writes** full output to `.claude/agent-handoffs/{session-id}/{seq}-{role}-report.md`
2. **Agent signals completion** by creating a `.done` marker file
3. **Coordinator passes** only the file path to the next agent
4. **Downstream agent reads** the original file directly — no compression, no paraphrasing

The system is enforced by hooks (PreToolUse validates prompts, PostToolUse validates output files) and a Python validator that checks file completeness, YAML frontmatter, section structure, and content quality.

## Documentation

| Document | What's Inside |
|----------|---------------|
| [Protocol Spec](docs/protocol.md) | Roles, file conventions, atomicity (`.done`), checklists |
| [Architecture](docs/architecture.md) | System design — 4 layers, data flow, deployment |
| [Template](docs/template.md) | Handoff file format — YAML frontmatter + 5 sections |
| [Scripts Reference](docs/scripts.md) | All 4 scripts explained — usage, exit codes, errors |
| [Verification Report](docs/verification.md) | 31/31 tests passed, fidelity benchmarks |
| [Evolution](docs/evolution.md) | Self-improvement — failure logs, META rules, human gating |
| [Canonical Rules](rules/agent-handoff.md) | Full rules text — source of truth for the protocol |

## Traditional Install

### 1. Install

```bash
cp scripts/*.sh scripts/*.py ~/.claude/scripts/
cp templates/agent-handoff-template.md ~/.claude/templates/
cp rules/agent-handoff.md ~/.claude/rules/
```

### 2. Configure hooks

Merge the hooks from [examples/settings-hooks.json](examples/settings-hooks.json) into
`~/.claude/settings.json`. **Important:** The JSON uses skill paths by default. For
traditional install, change each `command` from
`~/.claude/skills/agent-handoff/scripts/` to `~/.claude/scripts/`.

### 3. Generate session and handoff block

```bash
SESSION_ID="$(date +%Y%m%d-%H%M%S)-$(uuidgen | head -c8)"
mkdir -p .claude/agent-handoffs/$SESSION_ID
```

Add to your Agent prompt:

```
## Handoff Files
### Output
- .claude/agent-handoffs/{session-id}/01-{role}-report.md

After writing: touch {path}.done
Return only: ✅ Handoff written to `{path}`. Summary: {one sentence}
```

### 4. Validate

```bash
python3 scripts/validate-handoff.py <handoff-file>
python3 scripts/validate-handoff.py --recent-failures
```

### 5. Evolve the protocol

> "Analyze recent handoff failure records. Identify repeating patterns. Propose improvements."

## Architecture at a Glance

| Layer | What | Where (Skill) | Where (Traditional) |
|-------|------|---------------|---------------------|
| Rules | Protocol spec + core principle | `~/.claude/skills/agent-handoff/rules/` | `~/.claude/rules/` |
| Templates | Handoff file template | `~/.claude/skills/agent-handoff/templates/` | `~/.claude/templates/` |
| Execution | Scripts, hooks, validator | `~/.claude/skills/agent-handoff/scripts/` | `~/.claude/scripts/` |

## Skills Using AHP

- **subagent-driven-development** — implementer → spec-reviewer → code-quality-reviewer
- **write-draft** — 12-agent pipeline: research → outline → draft

## License

MIT — see [LICENSE](LICENSE)
