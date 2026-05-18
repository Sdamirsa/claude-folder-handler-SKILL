# `.claude/` System Design — v1 (Post-Critique)

> Lean baseline + opt-in packs. Triggering via a single ROUTER doc.
> Python hooks. Gitignored MCP by default. Upgrade-aware.

---

## 1. Design Philosophy (unchanged)

1. **Triggering-first** — sharp descriptions; *and* a single router doc as the canonical decision aid.
2. **Layered enforcement** — hooks (deterministic) > skills/agents (probabilistic) > CLAUDE.md/rules (advisory).
3. **Minimum-default context** — startup loads ~30-line CLAUDE.md + 1 skill description + 1 router doc.
4. **One concern, one home** — no duplication; ROUTER.md is the *index*, not a re-statement.
5. **Discoverable** — humans, Claude, and CI can all read the system from the filesystem.

## 2. Lean Baseline (what `/setup` ships by default)

```
<repo-root>/
├── CLAUDE.md                          # ≤30 lines. Stack, commands, 2 conventions. Points to .claude/.
├── .mcp.json.example                  # Template; .mcp.json is gitignored.
├── .gitignore                         # excludes .claude/settings.local.json, CLAUDE.local.md, .mcp.json
└── .claude/
    ├── README.md                      # ~50 lines. What lives where. Plus: how to install packs.
    ├── ROUTER.md                      # THE triggering doc. Injected by SessionStart.
    ├── settings.json                  # Permissions + hook wiring + env (committed).
    ├── settings.local.json            # Personal overrides (gitignored).
    ├── .meta/
    │   ├── version                    # Template version installed.
    │   ├── hooks.lock                 # sha256 of every hook script.
    │   └── packs.json                 # Which packs installed.
    ├── rules/
    │   └── 00-global.md               # Global conventions (paths: empty / always load).
    ├── skills/
    │   └── commit/SKILL.md            # ONE starter skill. The most reliable trigger.
    └── hooks/
        ├── lib/                       # Python shared helpers (logging, jq, sanitize).
        ├── 00-session-start.py        # Injects ROUTER.md + git context + drift warnings.
        ├── 10-pre-deny-secrets.py     # PreToolUse on Read|Edit|Write|Bash.
        └── 20-pre-deny-destructive.py # PreToolUse on Bash.
```

**Total artifacts shipped by default: 11 files. (v0 had ~17 just for the skeleton.)**

## 3. Opt-in Packs

Each pack is a directory under the meta-skill: `<meta-skill>/packs/<name>/`. `/setup` (or `/install-pack <name>`) copies it into the target repo's `.claude/` with conflict detection.

| Pack | Adds | Triggered by |
|---|---|---|
| `+pr-flow` | skills: `open-pr`, `rebase-clean`; agent: `reviewer` | "open a PR", "ship this", "review my changes" |
| `+test-tooling` | skill: `debug-failing-test`; agent: `test-writer` | "test is red", "this is broken", "write a test for" |
| `+frontend` | rules: `react.md`, `tsx.md` (path-scoped); hook: `post-edit-eslint.py` | when editing `**/*.tsx` |
| `+backend-api` | rules: `api.md` (path-scoped); skill: `migrate-schema` | when editing `src/api/**`, `src/routes/**` |
| `+monorepo` | template for per-package `CLAUDE.md`; nested `.claude/rules/<pkg>.md` | always, in `apps/*` and `packages/*` |
| `+security-hardening` | tighter denies; WebFetch domain allowlist; hooks.lock enforcement | always |
| `+telemetry` | Stop-hook that logs `{skill_invoked, success}` to `.claude/.cache/invocations.jsonl` | always |

Packs are *additive*. They can append-only to `settings.json` (inside `<!-- managed:hook-block --> ... <!-- /managed -->` markers preserving user edits).

## 4. ROUTER.md (the load-bearing artifact)

A ~100-line markdown doc, injected into context at `SessionStart`. Replaces the failure-prone "N skill descriptions independently winning the trigger race" with a single decision table.

```markdown
# Claude Code router for <repo-name>

When the user asks something, consult this router BEFORE deciding to write code.

## Workflows (skills)
| User says... | Skill | When NOT to use |
|---|---|---|
| "commit this", "save changes", "check in" | skills/commit/SKILL.md | When user wants to push or open a PR — chain after. |
| "open a PR", "ship this", "send for review" | skills/open-pr/SKILL.md (pr-flow pack) | Without committing first. |
| "this test is red", "X is broken", "why doesn't Y work" | skills/debug-failing-test/SKILL.md (test-tooling pack) | When the failure is obvious; just fix. |

## Delegations (subagents)
| Intent | Agent | Why delegate |
|---|---|---|
| "review my changes critically" | agents/reviewer.md (pr-flow pack) | Clean context window for honest critique. |
| "find where X is defined" | agents/explorer.md (built-in) | Parallel read-only search. |

## Hard constraints (enforced by hooks)
- Reads of `**/.env*`, `**/credentials*`, `**/.ssh/**`, `**/.aws/**`, `**/.gnupg/**` are DENIED.
- `git push --force` to protected branches is DENIED.
- `rm -rf` of `/`, `~`, `$HOME` is DENIED.

## Local conventions
- Build: `<cmd>`  Test: `<cmd>`  Lint: `<cmd>`
- See `.claude/rules/*` for path-scoped guidance.

## How to extend
- New workflow → add a skill, append a row to "Workflows" above.
- New deny → edit `settings.json` AND `hooks/10-pre-deny-secrets.py`.
- Anti-patterns: editing this router without updating the underlying skill/agent.
```

The router doc is what makes the system *legible*. Claude reads this once and knows everything. Humans read this and know everything.

## 5. Triggering Convention (sharpened)

Every skill/subagent description follows this template:

```
<verb-phrase capability starting with the keyword users say>. <Optional second sentence with edge cases.>
Use when the user says "<verbatim phrase 1>", "<phrase 2>", "<phrase 3>",
asks about <symptom 1> or <symptom 2>, or mentions <noun 1>/<noun 2>.
NOT for <negative scope> — use <other artifact> instead.
```

**Hard rules:**
- ≥600 chars, ≤1200 chars (buffer below 1536 truncation cap).
- ≥5 keyword variants drawn from how *users* actually talk (symptoms, not skill internals).
- ≥2 verbatim quoted user phrases.
- One explicit negative-scope clause referencing the next-most-similar artifact.
- Third person only.

**Lint** (in `+security-hardening` pack): regex over every `SKILL.md` / `agents/*.md` checks: char range, "Use when" present, ≥2 quoted phrases, ≥1 "NOT for" clause.

## 6. Hooks (Python, UV inline deps)

Every hook is a single Python file with UV header:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""PreToolUse hook: deny reads/writes of credential files."""
import json, sys, re, os
from pathlib import Path

DENY_GLOBS = ["**/.env*", "**/credentials*", "**/id_rsa*", "**/*.pem", "**/*.key",
              "**/.npmrc", "**/.netrc", "**/.git-credentials", "**/.gnupg/**",
              "**/.aws/**", "**/.ssh/**", "**/.kube/config", "**/.docker/config.json",
              "/proc/*/environ"]

def main():
    payload = json.load(sys.stdin)
    tool = payload["tool_name"]
    tinput = payload["tool_input"]
    # ... canonical-path expansion, shlex parsing for Bash, glob match ...
    # exit 2 with stderr message on deny

if __name__ == "__main__":
    main()
```

**Why Python over bash:**
- `shlex.split()` handles quoted args, env-var indirection.
- `pathlib.Path.resolve()` canonicalizes `./../../.env` to absolute.
- Real regex with anchors, no `[[ ]]` portability traps.
- Testable: each hook ships with a `_test.py` of attack-vector inputs.

**hooks.lock** (in `.claude/.meta/hooks.lock`):
```
00-session-start.py    sha256:abc123...
10-pre-deny-secrets.py sha256:def456...
```
The `00-session-start.py` hook reads `hooks.lock` and refuses to run if any sibling's sha256 mismatches. On first launch after a `git pull` that touched hooks, it emits a warning and refuses to chain other hooks until the user runs `/approve-hooks`.

## 7. settings.json (committed baseline, tightened)

```jsonc
{
  "permissions": {
    "deny": [
      "Read(**/.env*)", "Read(**/credentials*)", "Read(**/.git-credentials)",
      "Read(**/id_rsa*)", "Read(**/*.pem)", "Read(**/*.key)",
      "Read(~/.ssh/**)", "Read(~/.aws/**)", "Read(~/.gnupg/**)",
      "Read(~/.kube/config)", "Read(~/.docker/config.json)",
      "Read(/proc/*/environ)",
      "Edit(**/.env*)", "Write(**/.env*)",
      "Edit(**/.git/**)", "Write(**/.git/**)",
      "Edit(**/.claude/hooks/**)", "Write(**/.claude/hooks/**)",
      "Bash(rm -rf /*)", "Bash(rm -rf ~*)", "Bash(rm -rf $HOME*)",
      "Bash(sudo *)",
      "Bash(curl *169.254.169.254*)", "Bash(curl *metadata.google.internal*)",
      "Bash(curl * | sh)", "Bash(curl * | bash)", "Bash(wget * | sh)"
    ],
    "ask": [
      "Bash(git push:*)", "Bash(git push -f:*)", "Bash(git push --force*)",
      "Bash(git reset --hard*)", "Bash(git rebase -i*)",
      "WebFetch", "Bash(npm install:*)", "Bash(pip install:*)"
    ],
    "defaultMode": "default"
  },
  "hooks": {
    "SessionStart": [
      { "matcher": "startup|resume",
        "hooks": [{ "type": "command",
                    "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/00-session-start.py",
                    "timeout": 10 }] }
    ],
    "PreToolUse": [
      { "matcher": "Read|Edit|Write|Bash",
        "hooks": [{ "type": "command",
                    "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/10-pre-deny-secrets.py",
                    "timeout": 5 }] },
      { "matcher": "Bash",
        "hooks": [{ "type": "command",
                    "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/20-pre-deny-destructive.py",
                    "timeout": 5 }] }
    ]
  },
  "includeCoAuthoredBy": false
}
```

Notes:
- The bash regex hooks back the permission rules (defense in depth).
- `Bash(curl * | sh)` and friends are pattern-blocked at the rule level.
- Hook ordering: numeric prefix (`00`, `10`, `20`) — multiple hooks under one matcher run in order.

## 8. Meta-skill (this repo) — sharpened description

```yaml
---
name: claude-folder-handler
description: |
  Scaffolds, upgrades, and audits the `.claude/` configuration for a coding repository.
  Use when the user says "set up .claude", "init claude code in this repo",
  "scaffold claude config", "audit my claude folder", "upgrade my claude setup",
  "install a claude pack", or "what's wrong with my .claude directory".
  Generates a lean `.claude/` baseline (one skill, two PreToolUse hooks, one ROUTER),
  with opt-in packs for pr-flow, test-tooling, frontend, backend, monorepo, security, telemetry.
  NOT for: general project scaffolding (use `create-next-app`/equivalents), `git init`,
  `npm init`, framework-specific bootstrapping, editing existing skill bodies (edit the
  skill files directly), or general code review (use the `reviewer` agent instead).
allowed-tools: Read, Write, Edit, Bash(git:*), Bash(mkdir:*), Bash(cat:*), Bash(diff:*)
---
```

Trigger keywords: `claude folder`, `.claude`, `CLAUDE.md`, `claude config`, `claude code setup`, `claude pack`, `claude audit`, `claude upgrade`. Generic terms (`setup`, `init`, `scaffold`, `bootstrap`) only trigger when paired with a `.claude` / `claude code` token in the same sentence.

## 9. /setup behavior (the meta-skill's main entry)

1. Detect repo type from `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod`.
2. Probe for existing `.claude/` — if present, run `/upgrade` flow instead.
3. Dry-run by default; print proposed file list + diff vs existing.
4. Ask: "Apply baseline? Which packs?" (multi-select).
5. On `--apply`: copy files, substitute stack-detected build/test/lint commands.
6. Write `.claude/.meta/version`, `.meta/packs.json`, `.meta/hooks.lock`.
7. Append `.gitignore` entries inside `<!-- managed:claude-folder-handler --> ... <!-- /managed -->` block.
8. Print next steps: "Run `/refresh-context` to load ROUTER.md, then try `/commit`."

## 10. /upgrade flow

1. Read `.claude/.meta/version` → current template version.
2. Read meta-skill's own version.
3. Compute three-way merge: `template-old → template-new` against `repo-current`.
4. Inside `<!-- managed:* -->` blocks: overwrite with new template.
5. Outside managed blocks: leave user edits alone; emit conflict markers if structural changes needed.
6. Show diff; ask to apply.
7. Update `.meta/version` + `.meta/hooks.lock`.

## 11. Anti-patterns rejected (carried forward + new)

From v0:
- Bloated CLAUDE.md (>80 lines).
- Duplicated rules.
- Vague skill descriptions.
- Silent PreToolUse blocks.
- Bespoke `settings.json` per dev.
- Slash commands for natural-language intents.

New (from critiques):
- Bash hooks for security-sensitive matching (regex is fragile).
- `.mcp.json` committed by default (supply-chain hole).
- Multiple competing `PostToolUse(Edit|Write)` hooks without ordering.
- Skill bodies drifting from descriptions (forcing function: `/audit` in `+telemetry` pack).
- Per-developer hook scripts (must be locked + reviewed).
- MANIFEST.json without an external consumer.
