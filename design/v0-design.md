# `.claude/` System Design — v0 (Draft for Critique)

> A repo-bootstrappable system for managing `.claude/` in any coding project.
> Optimized for: agent comprehension, smart triggering, low context cost, defense-in-depth.

---

## 1. Design Philosophy

Five principles, in priority order:

1. **Triggering-first.** Every artifact has a sharp, third-person, keyword-loaded `description`. If Claude can't reliably decide *when* to use it, it doesn't ship.
2. **Layered enforcement.**
   - **Hooks** = deterministic (security + context injection that *must* happen)
   - **Skills/Subagents** = probabilistic (workflows Claude should *usually* reach for)
   - **CLAUDE.md / rules** = advisory (conventions Claude should *prefer*)
3. **Minimum-default context.** Startup loads tiny CLAUDE.md + descriptions only. Everything heavy loads lazily on demand.
4. **One concern, one home.** No content lives in two places (no rule-duplication between CLAUDE.md and a skill).
5. **Discoverable by agents and humans.** A manifest + consistent layout means a Claude agent dropped into the repo can navigate the system without external context.

---

## 2. Canonical Folder Layout

```
<repo-root>/
├── CLAUDE.md                          # ≤80 lines. Points to .claude/ index. NOT a kitchen sink.
├── .mcp.json                          # MCP servers (committed). Root, not .claude/.
├── .gitignore                         # excludes .claude/settings.local.json, CLAUDE.local.md
└── .claude/
    ├── README.md                      # Human/agent index. "What lives where + how to extend."
    ├── MANIFEST.json                  # Machine-readable inventory of skills/agents/hooks
    ├── settings.json                  # Permissions, hooks wiring, env (committed)
    ├── settings.local.json            # Personal overrides (gitignored)
    │
    ├── agents/                        # Subagents — auto-delegated by description
    │   ├── explorer.md                #   read-only, fast, codebase search
    │   ├── reviewer.md                #   critical review of pending changes
    │   └── planner.md                 #   architectural planning, no edits
    │
    ├── skills/                        # Skills — auto-trigger OR /name invoked
    │   ├── commit/SKILL.md            #   smart commit: stage → diff → message → commit
    │   ├── open-pr/SKILL.md           #   open PR with summary + test-plan
    │   ├── debug-failure/SKILL.md     #   reproduce + diagnose failing test or bug
    │   └── refactor-safely/SKILL.md   #   rename/move with type-check + test gate
    │
    ├── commands/                      # Slash commands — explicit-only, no triggering
    │   ├── setup.md                   #   /setup    — first-time repo bootstrap
    │   └── audit.md                   #   /audit    — lint .claude/ for anti-patterns
    │
    ├── rules/                         # Path-scoped instructions (frontmatter `paths:`)
    │   ├── 00-global.md               #   no paths → always loaded
    │   ├── tests.md                   #   paths: tests/**, **/*.test.*, **/*_test.*
    │   ├── api.md                     #   paths: src/api/**, src/routes/**
    │   └── frontend.md                #   paths: src/components/**, **/*.tsx
    │
    ├── hooks/                         # Hook scripts referenced from settings.json
    │   ├── lib/                       #   shared helpers (logging, jq wrappers)
    │   ├── session-start.sh           #   inject git/branch/recent-PR context
    │   ├── pre-tool-deny-secrets.sh   #   PreToolUse: block .env, credentials reads
    │   ├── pre-tool-deny-destructive.sh #  PreToolUse: block rm -rf /, git push --force
    │   └── post-edit-format.sh        #   PostToolUse: auto-format Edit/Write output
    │
    └── output-styles/                 # (optional, off by default)
        └── pair-programmer.md
```

**Gitignore additions:**
```
.claude/settings.local.json
.claude/CLAUDE.local.md
CLAUDE.local.md
.claude/.cache/
```

---

## 3. CLAUDE.md Strategy

**Root `CLAUDE.md`** (≤80 lines, the only thing always in context):

```markdown
# <Project name>

## Stack
- Language: <e.g. TypeScript 5.x, Python 3.12>
- Framework: <e.g. Next.js 14 / Django 5>
- Test runner: <e.g. vitest / pytest>

## How to run
- Install: `<cmd>`
- Test:    `<cmd>`
- Lint:    `<cmd>`
- Build:   `<cmd>`

## Conventions (the load-bearing rules)
- 3-5 bullet points MAX. Things you'd say in code review every time.
- Anything longer goes in .claude/rules/<topic>.md with path scoping.

## Extensions
- Path-scoped rules:   .claude/rules/
- Workflows (skills):  .claude/skills/   (auto-triggered)
- Subagents:           .claude/agents/   (auto-delegated)
- Slash commands:      .claude/commands/ (manual /name)
- See `.claude/README.md` for the full map.
```

**Why this is small:** CLAUDE.md ships as a user message *every turn*. Every line costs tokens forever. Path-scoped rules ship only when relevant files are touched.

---

## 4. Triggering Convention (the load-bearing decision)

Every skill/subagent description follows this exact template:

```
<3rd-person verb-phrase capability, 1 sentence>.
Use when <user-intent keyword 1>, <user-intent keyword 2>,
or when the user says "<verbatim phrase>" or "<verbatim phrase>".
<Optional: explicitly NOT for X, to prevent over-trigger>.
```

**Hard rules:**
- Third person only. No "I", no "you".
- ≤1200 chars (buffer below the 1536 cap so it survives truncation).
- 3-5 trigger keywords minimum, drawn from how users actually talk.
- Include at least one *verbatim user phrase* in quotes.
- If two skills could plausibly fire on the same request, add a negative scope: "Not for X — use Y instead."

**Lint rule** (enforced by `/audit` slash command): regex-check every `SKILL.md` and `agents/*.md` for: third-person voice, char length, presence of "Use when", presence of quoted phrase.

---

## 5. Hook System (the deterministic layer)

**SessionStart** (matchers: `startup`, `resume`) →
`.claude/hooks/session-start.sh` injects `additionalContext`:
- Current branch + how it diverges from main
- Last 5 commits on this branch
- Open PRs/issues authored by current user
- Reminder text: "Run `/audit` if any `.claude/` files were recently edited."

**PreToolUse** (matcher: `Read|Edit|Write|Bash`) →
- `pre-tool-deny-secrets.sh`: regex against `tool_input.file_path` or `tool_input.command` for `.env`, `.aws/`, `id_rsa`, `*.pem`, `.npmrc`, `.netrc`. Exit 2 with reason.
- `pre-tool-deny-destructive.sh`: regex against `tool_input.command` for `rm -rf /`, `rm -rf ~`, `git push --force` to `main|master`, `git reset --hard origin/main`. Exit 2.

**PostToolUse** (matcher: `Edit|Write`) →
- `post-edit-format.sh`: detects file extension, runs project formatter (prettier / ruff / gofmt / rustfmt) on changed file. Failure non-blocking (exit 0 with stderr).

**Stop** → not used by default (avoid surprise loop extensions).

**Why these and no others:** every hook costs latency. Default to the 3 with highest ROI (security, security, ergonomics). Project owners add more.

---

## 6. settings.json (committed baseline)

```jsonc
{
  "permissions": {
    "deny": [
      "Read(./.env)", "Read(./.env.*)",
      "Read(~/.ssh/**)", "Read(~/.aws/**)",
      "Bash(rm -rf /*)", "Bash(rm -rf ~*)",
      "Bash(git push --force origin main)",
      "Bash(git push --force origin master)"
    ],
    "ask": [
      "Bash(git push:*)",
      "WebFetch"
    ],
    "additionalDirectories": [],
    "defaultMode": "default"
  },
  "hooks": {
    "SessionStart": [
      { "matcher": "startup|resume",
        "hooks": [{ "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/session-start.sh", "timeout": 10 }] }
    ],
    "PreToolUse": [
      { "matcher": "Read|Edit|Write",
        "hooks": [{ "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/pre-tool-deny-secrets.sh", "timeout": 5 }] },
      { "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/pre-tool-deny-destructive.sh", "timeout": 5 }] }
    ],
    "PostToolUse": [
      { "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/post-edit-format.sh", "timeout": 30 }] }
    ]
  },
  "includeCoAuthoredBy": false
}
```

`settings.local.json` template (gitignored, generated by `/setup`):
```jsonc
{
  "permissions": { "allow": [], "additionalDirectories": [] },
  "env": {}
}
```

---

## 7. MANIFEST.json (the agent-discovery layer)

A small machine-readable index — exists so a Claude agent can ask "what's available here?" without grepping. Example:

```json
{
  "version": "0.1",
  "skills": [
    { "name": "commit", "path": "skills/commit/SKILL.md", "triggers": ["commit", "stage changes", "save changes"] },
    { "name": "open-pr", "path": "skills/open-pr/SKILL.md", "triggers": ["pr", "pull request", "ship this"] }
  ],
  "agents": [
    { "name": "explorer", "path": "agents/explorer.md", "purpose": "read-only code search" },
    { "name": "reviewer", "path": "agents/reviewer.md", "purpose": "critical change review" }
  ],
  "hooks": {
    "SessionStart": ["session-start.sh"],
    "PreToolUse":  ["pre-tool-deny-secrets.sh", "pre-tool-deny-destructive.sh"],
    "PostToolUse": ["post-edit-format.sh"]
  }
}
```

`/audit` regenerates this from filesystem contents.

---

## 8. The Meta-Skill (what this repo SHIPS)

This repo (`claude-folder-handler-SKILL`) is itself a Claude skill, installed as either:
- a global skill under `~/.claude/skills/claude-folder-handler/`, OR
- a `git clone` + symlink during onboarding.

It triggers on user phrases like:
- "set up .claude in this repo"
- "scaffold claude code for this project"
- "initialize claude folder"
- "audit my .claude folder"
- "what's wrong with my claude setup"

Its SKILL.md description (template):
> Scaffolds, audits, and upgrades the `.claude/` configuration in any coding repo. Use when the user says "set up claude code", "init .claude", "scaffold claude", "audit my claude config", or asks how to organize `.claude/` for a new project. Generates a baseline `.claude/` with hooks, path-scoped rules, and template skills. Not for editing existing skill bodies — use the skill's own files for that.

What it does, in order:
1. Detect repo type (read `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod`).
2. Copy the template `.claude/` tree, substituting stack-detected build/test/lint commands into root `CLAUDE.md` and `post-edit-format.sh`.
3. Generate a starter `MANIFEST.json`.
4. Append `.gitignore` entries.
5. Print a "next steps" summary: which hooks fire, which skills exist, what to customize.

---

## 9. Open Questions for the User

(Things I'd want answered before declaring v1.)

1. **Skill vs slash-command default?** Should `commit` / `open-pr` be skills (auto-trigger on natural language) or commands (explicit `/commit`)? Auto-trigger is slicker but riskier.
2. **Hook strictness:** should PreToolUse denies be hard-blocks (exit 2) or just `ask` permission rules (lets user override per-turn)?
3. **Subagent count:** 3 (explorer/reviewer/planner) is conservative. Should we ship more (debugger, test-writer, doc-writer) by default, or keep the baseline lean?
4. **Path-scoping granularity:** `.claude/rules/` topical (api/tests/frontend) vs by language (ts/py/go)? Topical is more re-usable.
5. **MANIFEST.json:** worth the maintenance cost, or trust Claude to read the filesystem? (Probably yes — it's the single artifact that makes the system *legible*.)

---

## 10. Anti-patterns this design rejects

- Bloated CLAUDE.md (>200 lines) — kills context budget.
- Duplicated rules in CLAUDE.md AND skills — drift over time.
- Skills with vague descriptions ("processes data") — under-trigger.
- PreToolUse hooks that block silently — frustrating; always emit a reason.
- Every team member with their own `settings.json` diff — use `settings.local.json`.
- Slash commands for things users describe in natural language — that's a skill's job.
- Subagents for tiny tasks — context-fork overhead isn't worth it under ~3 tool calls.
