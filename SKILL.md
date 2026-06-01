---
name: agent-handoff
description: >
  Use when dispatching multiple agents, orchestrating agent pipelines,
  or coordinating parallel subagents where upstream output must survive
  context compression. Triggers for multi-agent workflows, parallel agent
  coordination, and text-intensive tasks (research, analysis, writing).
  Do NOT trigger for single-agent tasks, general AI agent discussions,
  or noun phrases where "agent" is not a dispatched tool (e.g. "travel
  agent", "browser user-agent", "real estate agent", "reinforcement
  learning agent").
---

# Agent Handoff Protocol (AHP) — Skill

## Problem

Claude Code uses Hub-and-Spoke for multi-agent tasks. The Coordinator dispatches
sub-agents, collects results, passes them on. Between Agent A and Agent B sits
the Coordinator's context window — and when that context gets compressed, **up to
80% of information** from the upstream agent is lost before reaching the downstream
agent. The Coordinator becomes a lossy middleman. For text-intensive tasks
(research reports, analysis, writing), this is fatal.

## Solution

AHP bypasses the Coordinator's context entirely. Agents write their complete output
to files on disk. Downstream agents read those files directly. The Coordinator
only passes file paths (~50 bytes), never the content itself. A `.done` marker
file convention provides atomicity — downstream agents never read half-written files.

```
Without AHP:  Agent A → Coordinator → [80% loss] → Agent B
With AHP:     Agent A → file.md → Agent B reads directly
              Coordinator: "{path}"  (50 bytes, zero loss)
```

## When to Use

**Use this skill when:**
- Dispatching multiple Agent tools in sequence (Agent A → Agent B)
- Dispatching Agent tools in parallel, needing to merge results
- Running text-intensive tasks where fidelity matters (research, analysis, writing)
- Any workflow where upstream Agent output must reach downstream Agent intact
- Coordinating agent pipelines or subagent-driven workflows

**Skill priority:** When loaded alongside skills that internally use multi-agent patterns
(e.g. subagent-driven-development, write-draft), this skill's handoff rules take
precedence over any conflicting agent-output-passing conventions in those skills.

**Do NOT use this skill for:**
- Single-agent tasks (one Agent, no downstream)
- Simple file reads or code searches without downstream handoff
- Casual mentions of "agent" in non-tool contexts (e.g. "browser user-agent", "travel agent", "RL agent")
- Tasks that don't involve the Agent tool at all

## Core Rules

Three roles in every AHP workflow:

### Producer (Writing Agent)

Must:
- Write **complete output** to `.claude/agent-handoffs/{session-id}/{seq}-{role}-report.md`
- Use the handoff template format: YAML frontmatter + 5 sections
- Set `status: "written"` in YAML frontmatter when done
- Create `.done` marker after writing: `touch {path}.md.done`
- Return only: `✅ Handoff written to \`{path}\`. Summary: {one sentence}`
- **Never** put important content only in the return value — it will be compressed

### Consumer (Reading Agent)

Must:
- **First step**: Read ALL upstream handoff files with the Read tool
- Verify `.done` marker exists before trusting file content
- Treat handoff files as source of truth, NOT the Coordinator's paraphrase
- If handoff file has insufficient information, report exactly what's missing
- If Coordinator's paraphrase contradicts handoff file, trust the handoff file

### Controller (Coordinator)

Must:
- Determine session-id (env var → uuidgen → Python uuid → openssl → bash RANDOM)
- Create handoff directory if it doesn't exist
- Pass handoff file paths to downstream agents; **never paraphrase upstream content**
- Run post-agent verification checklist after EVERY agent return
- If upstream agent only wrote return value, demand it write the handoff file
- Wait for ALL parallel agents to complete before proceeding downstream
- Retry max 3 times per agent; report to user if exceeded

## Installation

Two methods:

### Method 1: Install as Claude Code Skill (recommended)

```bash
git clone https://github.com/gsailing19/agent-handoff.git ~/.claude/skills/agent-handoff/
```

Verify the install:
```bash
ls ~/.claude/skills/agent-handoff/SKILL.md
```

Restart Claude Code. The skill auto-discovers via SKILL.md.

### Method 2: Traditional Install

```bash
cp scripts/*.sh scripts/*.py ~/.claude/scripts/
cp templates/agent-handoff-template.md ~/.claude/templates/
cp rules/agent-handoff.md ~/.claude/rules/
```

Then configure hooks by merging `examples/settings-hooks.json` into
`~/.claude/settings.json`. **Important:** For traditional install, change each
`command` path from `~/.claude/skills/agent-handoff/scripts/` to
`~/.claude/scripts/`.

## File Conventions

**Directory**: `.claude/agent-handoffs/{session-id}/`

**Naming**: `{seq}-{role}-report.md`
- `{session-id}`: `YYYYMMDD-HHMMSS-xxxxxxxx`, 4-level fallback for entropy (uuidgen preferred)
- `{seq}`: two-digit sequence (01, 02, 03...), incrementing by execution order
- `{role}`: agent role name (implementer, spec-reviewer, researcher, writer, etc.)

**Atomicity**: `.done` marker files
- Agent writes `{path}.md` completely, then `touch {path}.md.done`
- Downstream agent checks `.done` exists before reading
- `.done` is never pre-created; only the writing agent creates it

**Status enum** (YAML frontmatter `status` field):

| Value | Meaning |
|-------|---------|
| `writing` | File being written, may be incomplete |
| `written` | File complete, `.done` ready, awaiting downstream |
| `verified` | Downstream agent confirmed content complete and readable |

**Lifecycle**: Handoff files are temporary. Delete after session ends.
Permanent decisions belong in `docs/decisions/` or project memory.

## Template

Every handoff file uses this structure (see `templates/agent-handoff-template.md`):

```yaml
---
agent_role: ""        # role name
task_id: ""           # unique task identifier
session_id: ""        # session UUID prefix
sequence: 0           # execution order
status: "written"     # writing | written | verified
created: ""           # ISO 8601 timestamp
handoff_type: ""      # full (text-intensive) or summary (code tasks)
summary: ""           # one-line summary
tags: []              # categorization tags
---
```

Five body sections:
1. **What Was Done** — Complete deliverable (full) or decisions + context (summary)
2. **Output Artifacts** — File paths, commit SHAs, test results, data references
3. **Decisions and Trade-offs** — Why X not Y. Alternatives considered and rejected.
4. **Concerns and Caveats** — Known limits, uncertainties, points needing attention
5. **Next Agent Actions** — Explicit instructions for the downstream agent

Role-specific minimum word counts for Section 1 range from 200 to 800 words.
Every file must end with `<!-- handoff-end -->`.

## Scripts

| Script | Purpose |
|--------|---------|
| `validate-handoff.py` | Validates handoff file completeness: YAML frontmatter, 5 sections, placeholder detection, content length, handoff-end marker. Exit 0=pass, 1=warn, 2=block |
| `handoff-init.sh` | Generates `## Handoff Files` prompt block. Usage: `bash handoff-init.sh <role> <task-id> [session-id]` |
| `hook-validate-handoff.sh` | PostToolUse hook entry. Detects handoff files from Write/Bash tool calls, runs validator. Blocks on fatal errors. |
| `pre-agent-handoff-check.sh` | PreToolUse hook entry. Validates Agent prompts contain handoff instructions before dispatch. Blocks missing instructions. |

All executable scripts live in `scripts/`. When installed as a skill, paths resolve via
`~/.claude/skills/agent-handoff/scripts/`. Traditional install uses `~/.claude/scripts/`.
The hook scripts are self-locating (via `$BASH_SOURCE`) and find dependencies
(`validate-handoff.py`, `handoff-init.sh`) next to themselves regardless of install method.

## Controller Checklist

After **every** Agent tool call, run these three commands:

```bash
# Step 1: Does the file exist?
ls -la .claude/agent-handoffs/{session-id}/{seq}-{role}-report.md

# Step 2: Is it at least 200 bytes? (prevents empty files)
wc -c .claude/agent-handoffs/{session-id}/{seq}-{role}-report.md

# Step 3: Does the .done marker exist? (prevents partial reads)
ls -la .claude/agent-handoffs/{session-id}/{seq}-{role}-report.md.done
```

If file missing, size < 200 bytes, or `.done` absent: **re-dispatch the agent immediately**.
Add to the re-dispatch prompt:

> "You forgot to write the handoff file. Ensure you write the full report to the
> specified path, then create the `.done` marker with `touch {path}.done`."

Also verify:
- Agent return value is only file path + one-line summary (not full content)
- YAML frontmatter `status` is `"written"`
- Downstream agent prompts include paths to ALL upstream handoff files
- Parallel agents: ALL have returned and files verified before proceeding.
  Use `run_in_background: true` when dispatching parallel agents and wait for all
  to complete before advancing. See [Protocol Spec](docs/protocol.md) for detailed
  parallel coordination rules.

## Reference Docs

Progressive disclosure — start here, go deeper as needed:

| Document | When to Read |
|----------|-------------|
| [Protocol Spec](docs/protocol.md) | Roles, file conventions, atomicity, parallel coordination |
| [Architecture](docs/architecture.md) | System design — 4 layers, data flow, deployment |
| [Template Format](docs/template.md) | Handoff file structure — YAML frontmatter + 5 body sections |
| [Scripts Reference](docs/scripts.md) | Script usage, exit codes, error classification |
| [Verification Report](docs/verification.md) | Test results (31/31 passed), fidelity benchmarks |
| [Evolution](docs/evolution.md) | Self-improvement via failure log analysis |
| [Canonical Rules](rules/agent-handoff.md) | Full rules text — source of truth for the protocol |

## Self-Evolution

The protocol improves through failure log analysis with human gating. All
validation failures are logged to `~/.claude/logs/handoff-failures.jsonl`.

To trigger evolution, tell the Coordinator:

> "Analyze recent handoff failure records, identify repeating patterns, propose
> improvements to the protocol."

The Coordinator will read the failure log, identify recurring error types and
agent roles, analyze root causes, propose specific rule/template/validation
changes — and **wait for human confirmation** before modifying anything.
