# Agent Handoff Protocol (AHP)

Claude Code's multi-Agent architecture is Hub-and-Spoke: Coordinator dispatches sub-agents → agents work independently → results return to Coordinator → Coordinator passes to the next agent. The problem is in the middle — when Coordinator's context gets compressed, information passed downstream can lose up to 80%.

AHP solves this: instead of the Coordinator "remembering" and "relaying" upstream results, agents write complete outputs to files, and downstream agents read them directly.

**Core principle**: Agent writes full output to file → downstream agent reads the original → Coordinator only passes file paths (~50 bytes), never paraphrases content

## Why AHP

Claude Code's Coordinator context gets compressed after receiving sub-agent returns. When that compressed information reaches the next agent, text-intensive tasks (research, analysis, writing) can lose up to 80% of data points (see [verification report](docs/verification.md)). AHP routes agent handoffs through the filesystem, bypassing the compression layer.

## Documentation

| Document | Contents |
|----------|----------|
| [docs/protocol.md](docs/protocol.md) | Full protocol spec — roles, file conventions, atomicity, checklists |
| [docs/architecture.md](docs/architecture.md) | System architecture — component relationships, deployment, data flow |
| [docs/template.md](docs/template.md) | Handoff file template — YAML frontmatter + five-section body |
| [docs/scripts.md](docs/scripts.md) | Script reference — validate-handoff.py, hook-validate-handoff.sh |
| [docs/verification.md](docs/verification.md) | Verification report — 31/31 tests passed, fidelity comparison |
| [docs/evolution.md](docs/evolution.md) | Self-evolution mechanism — failure logs + META rules + human gating |

## Quick Start

### 1. Install

```bash
# Copy scripts to your global Claude config
cp scripts/* ~/.claude/scripts/

# Copy the handoff template
cp templates/agent-handoff-template.md ~/.claude/templates/

# Copy the rules file
cp rules/agent-handoff.md ~/.claude/rules/
```

### 2. Configure hooks

Add the hooks from [examples/settings-hooks.json](examples/settings-hooks.json) to your `~/.claude/settings.json`. These hooks:
- **PreToolUse**: validates Agent prompts include handoff instructions before dispatch
- **PostToolUse**: validates handoff files after Write/Bash operations

### 3. Run a multi-agent task

```bash
# Generate session-id
SESSION_ID="$(date +%Y%m%d-%H%M%S)-$(uuidgen | head -c8)"
mkdir -p .claude/agent-handoffs/$SESSION_ID
```

In your Agent prompt, include:

```
## Handoff Files
### Output
- .claude/agent-handoffs/{session-id}/01-{role}-report.md

After writing: touch {path}.done
Return only: ✅ Handoff written to `{path}`. Summary: {one sentence}
```

### 4. Validate

```bash
python3 scripts/validate-handoff.py --log-failures <handoff-file>
python3 scripts/validate-handoff.py --recent-failures
```

### 5. Trigger protocol evolution

> "Analyze recent handoff failure records, identify repeating patterns, propose improvements to the protocol."

## Three-Layer Coverage

| Layer | Location | Scope |
|-------|----------|-------|
| Rules | `~/.claude/CLAUDE.md` + `~/.claude/rules/agent-handoff.md` | All projects |
| Templates | `~/.claude/templates/agent-handoff-template.md` | All projects |
| Execution | `~/.claude/scripts/` + `~/.claude/settings.json` (PostToolUse Hook) | All projects |

## Integrated Skills

- **subagent-driven-development** — implementer → spec-reviewer → code-quality-reviewer
- **write-draft** — 12-agent three-layer pipeline (research → outline → draft)

## License

MIT — see [LICENSE](LICENSE)

---

> Last updated: 2026-06-01
