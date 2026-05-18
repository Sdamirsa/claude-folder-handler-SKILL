# `.claude/` System — v3 Locked Spec

> **Status: awaiting one final review.** All design decisions are now answered.
> Once you say "go," I implement phase-by-phase per §11.

---

## 0. Locked Decisions (changes from v2)

| Decision | Resolution |
|---|---|
| Baseline size | Lean — 1 skill, 3 hooks, 1 router, no agents |
| Install model | Global skill via `~/.claude/skills/claude-folder-handler/` |
| Hook language | Python with UV inline-deps, no bash |
| Reference folder | Baseline ships `reference/INDEX.md` + `README.md` only; subdirs materialize as packs install or user creates |
| install.sh hosting | Both — `raw.githubusercontent.com/Sdamirsa/...` (latest) AND tagged GitHub Releases (pinned) |
| Default packs at `/setup` | Pre-checked: `+data-science +visualization +llm-app +llm-extraction +security-hardening +telemetry` |
| README tone | Hybrid — short top README + `docs/` deeper material |
| Telemetry | ON in baseline (local-only logging, /audit consumer) |
| Description lint | Advisory in `/audit`; non-zero exit on warnings; no CI block by default |
| Push-force policy | Hard-deny on protected branches (`main, master, develop, release/*`); `ask` elsewhere |
| `.mcp.json` | Always gitignored; `.mcp.json.example` committed; first-run instructions in README |

---

## 1. Repository Layout (this repo)

```
claude-folder-handler-SKILL/
├── README.md                      # short hybrid README; points at docs/
├── install.sh                     # POSIX shell; bootstraps uv; clones into ~/.claude/skills/
├── docs/                          # deeper material (architecture, pack catalog, FAQ)
│   ├── architecture.md
│   ├── packs.md
│   ├── triggering-convention.md
│   ├── upgrade-flow.md
│   └── security-model.md
├── design/                        # already exists: v0, v1, v2, critiques, this file
└── skill/                         # what lands at ~/.claude/skills/claude-folder-handler/
    ├── SKILL.md                   # the meta-skill (triggers /setup, /upgrade, /install-pack, /audit)
    ├── VERSION                    # semver tag; written by release process
    ├── commands/
    │   ├── setup.md               # /setup
    │   ├── upgrade.md             # /upgrade
    │   ├── install-pack.md        # /install-pack <name>
    │   ├── audit.md               # /audit
    │   └── approve-hooks.md       # /approve-hooks
    ├── scripts/
    │   ├── setup.py               # UV inline-dep script
    │   ├── upgrade.py
    │   ├── install_pack.py
    │   ├── audit.py
    │   ├── self_test.py
    │   └── lib/
    │       ├── detect_stack.py
    │       ├── managed_blocks.py
    │       ├── hooks_lock.py
    │       ├── pack_loader.py
    │       └── description_lint.py
    ├── template/                  # the lean baseline (copied by /setup)
    │   ├── CLAUDE.md.tmpl
    │   ├── .mcp.json.example
    │   ├── .gitignore.snippet
    │   └── .claude/
    │       ├── README.md
    │       ├── ROUTER.md.tmpl
    │       ├── settings.json.tmpl
    │       ├── .meta/
    │       │   ├── version.tmpl
    │       │   ├── hooks.lock.tmpl
    │       │   └── packs.json.tmpl
    │       ├── rules/
    │       │   └── 00-global.md
    │       ├── skills/
    │       │   └── commit/SKILL.md
    │       ├── hooks/
    │       │   ├── 00-session-start.py
    │       │   ├── 10-pre-deny-secrets.py
    │       │   ├── 20-pre-deny-destructive.py
    │       │   ├── 90-stop-log-invocation.py    # ships in baseline because telemetry is ON
    │       │   └── lib/
    │       │       ├── __init__.py
    │       │       ├── payload.py               # stdin JSON parsing
    │       │       ├── paths.py                 # canonicalize + glob match
    │       │       └── bash_parse.py            # shlex + flag normalization
    │       └── reference/
    │           ├── INDEX.md                     # the discovery doc
    │           └── README.md                    # editing conventions; "last-reviewed" header rule
    └── packs/
        ├── pr-flow/
        ├── test-tooling/
        ├── data-science/
        ├── visualization/
        ├── llm-app/
        ├── llm-extraction/
        ├── monorepo/
        ├── security-hardening/
        └── telemetry/                            # exists for re-install / explicit; baseline already ships it
```

---

## 2. install.sh (the only non-Python runtime file)

```sh
#!/usr/bin/env sh
set -eu
INSTALL_DIR="${HOME}/.claude/skills/claude-folder-handler"
REPO_URL="https://github.com/Sdamirsa/claude-folder-handler-SKILL"

# 1. Ensure uv
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# 2. Clone or update
if [ -d "${INSTALL_DIR}/.git" ]; then
  echo "Updating existing install..."
  git -C "${INSTALL_DIR}" pull --ff-only
else
  echo "Installing to ${INSTALL_DIR}..."
  mkdir -p "$(dirname "${INSTALL_DIR}")"
  git clone --depth 1 "${REPO_URL}" "${INSTALL_DIR}"
fi

# 3. Move into the actual skill subtree
# (the skill/ dir inside the repo becomes the visible skill;
# .git lives one level up so we can git pull on updates)

# 4. Self-test
uv run --script "${INSTALL_DIR}/skill/scripts/self_test.py" \
  || { echo "Self-test failed — see error above."; exit 1; }

echo
echo "✓ Installed claude-folder-handler skill."
echo "  Open Claude Code in any repo and say 'set up .claude here'."
```

Tagged-release URL form (for pinning):
```sh
curl -fsSL https://github.com/Sdamirsa/claude-folder-handler-SKILL/releases/download/v0.1.0/install.sh | sh
```

Latest-on-main URL form (for staying current):
```sh
curl -fsSL https://raw.githubusercontent.com/Sdamirsa/claude-folder-handler-SKILL/main/install.sh | sh
```

Both documented in README.

---

## 3. The Meta-Skill SKILL.md (description)

```yaml
---
name: claude-folder-handler
description: |
  Scaffolds, upgrades, and audits the `.claude/` configuration for a coding repository.
  Manages a lean baseline plus opt-in packs (pr-flow, test-tooling, data-science,
  visualization, llm-app, llm-extraction, monorepo, security-hardening, telemetry).
  Use when the user says "set up .claude", "init claude code in this repo",
  "scaffold claude config", "audit my claude folder", "upgrade my claude setup",
  "install a claude pack", "add the data-science pack", or "what's wrong with my
  .claude directory". Detects repo stack (python, node, rust, go) and customizes
  the generated CLAUDE.md, settings.json, ROUTER.md with stack-specific commands.
  NOT for: general project scaffolding (use `create-next-app`/equivalents), running
  `git init`, `npm init`, framework setup, editing existing skill bodies (edit
  the SKILL.md files directly), or doing the work that an installed pack's skill
  itself handles (e.g. committing, opening PRs, reviewing code).
allowed-tools: Read, Write, Edit, Bash(git:*), Bash(mkdir:*), Bash(diff:*), Bash(uv:*), Bash(cat:*), Bash(ls:*)
---
```

---

## 4. Baseline Content (always created by `/setup`)

| Path | Purpose |
|---|---|
| `CLAUDE.md` | ≤40 lines, stack/commands/2-3 conventions, points to `.claude/` |
| `.mcp.json.example` | Template; real `.mcp.json` is gitignored |
| `.gitignore` (appended inside managed block) | `.claude/settings.local.json`, `CLAUDE.local.md`, `.mcp.json`, `.claude/.cache/` |
| `.claude/README.md` | Navigation index, ≤80 lines |
| `.claude/ROUTER.md` | The triggering doc, SessionStart-injected |
| `.claude/settings.json` | Permissions, hook wiring (baseline only; packs append) |
| `.claude/.meta/version` | Template version installed |
| `.claude/.meta/hooks.lock` | sha256 of every hook |
| `.claude/.meta/packs.json` | Which packs are installed |
| `.claude/rules/00-global.md` | Always-loaded conventions |
| `.claude/skills/commit/SKILL.md` | The one baseline skill |
| `.claude/hooks/00-session-start.py` | Inject ROUTER + git context + drift warnings |
| `.claude/hooks/10-pre-deny-secrets.py` | Canonical-path-aware credential deny |
| `.claude/hooks/20-pre-deny-destructive.py` | shlex-parsed destructive-command deny |
| `.claude/hooks/90-stop-log-invocation.py` | Telemetry (ON in baseline) |
| `.claude/hooks/lib/*` | Shared Python helpers |
| `.claude/reference/INDEX.md` | Catalog of reference docs (empty until packs/user populate) |
| `.claude/reference/README.md` | Editing conventions: `<!-- last-reviewed: YYYY-MM-DD -->` header rule |

Total baseline: ~16 files. Lean enough to grok in 10 minutes.

---

## 5. Pack Contents

Each pack has `pack.toml` with the manifest of files to copy, ROUTER rows to insert, and `settings.json` overlays. Pack installation:
1. Conflict check against existing files
2. Copy files
3. Insert ROUTER rows into `<!-- managed:pack-<name> -->` block
4. Merge settings overlay into `<!-- managed:pack-<name> -->` block within settings.json
5. Append entry to `.claude/.meta/packs.json`
6. Regenerate `.claude/.meta/hooks.lock`

### `+pr-flow`
- `skills/open-pr/` — "open a PR", "ship this"; depends on `gh` CLI presence
- `skills/rebase-clean/` — "rebase on main", "clean up history"
- `agents/reviewer.md` — read-only critical review (Read, Grep, Glob, Bash)

### `+test-tooling`
- `skills/debug-failing-test/` — "test is red", "X is broken"
- `agents/test-writer.md` — "write a test for X"

### `+data-science` *(your default)*
- `skills/inspect-df/` — "what's in this dataframe", triggers on read_csv/read_parquet contexts
- `skills/clean-data/` — "clean this", "preprocess", "handle missing"
- `agents/data-explorer.md` — opens csv/parquet, profiles, returns summary
- `rules/pandas.md` — paths matching pandas-importing files
- `rules/notebooks.md` — paths matching `**/*.ipynb`
- `reference/datasets/` directory + `_template.md` (dataset card template)
- ROUTER row pointing at `reference/datasets/`

### `+visualization` *(your default)*
- `skills/quick-chart/` — "plot X", "make a chart of Y"
- `skills/chart-review/` — "is this chart good"
- `rules/plotting.md` — paths matching matplotlib/plotly/altair imports
- `reference/charts/_examples.md` — gallery of approved patterns

### `+llm-app` *(your default)*
- `skills/anthropic-sdk-bootstrap/` — "set up anthropic client"; scaffolds with prompt caching + .env
- `skills/migrate-model-version/` — "upgrade to claude X.Y"
- `rules/anthropic-sdk.md` — paths matching `import anthropic` / `@anthropic-ai/sdk`
- `hooks/15-warn-stale-model.py` — PostToolUse warning on deprecated model IDs
- `reference/apis/anthropic-sdk.md` — quick-reference for current model IDs, prompt caching, streaming patterns

### `+llm-extraction` *(your default)*
- `skills/extract-structured/` — "extract X from these documents"
- `skills/build-extractor-eval/` — eval harness scaffolding
- `skills/batch-extract/` — batch/async fan-out with checkpoints
- `agents/schema-designer.md` — "design a JSON schema for X"
- `rules/extraction.md` — paths matching `extractors/**`, `pipelines/**`
- `reference/schemas/_template.md` — schema doc template
- `reference/prompts/_template.md` — prompt template format
- `reference/extraction-checklist.md` — schema-first design checklist

### `+monorepo`
- `scripts/scaffold_packages.py` — walks `apps/*` and `packages/*`, generates per-package CLAUDE.md
- `rules/per-package.md` template
- ROUTER row explaining monorepo conventions

### `+security-hardening`
- `hooks/05-verify-hooks-lock.py` — runs first; refuses if hooks.lock mismatches
- `hooks/06-sanitize-injected-context.py` — strips control chars from SessionStart injections
- settings overlay: tighter denies, WebFetch domain allowlist
- `scripts/lint_descriptions.py` — runs in `/audit`
- `scripts/lint_claude_md.py` — flags `CLAUDE.md` > 80 lines in `/audit`

### `+telemetry` *(your default; also installed by baseline)*
- `hooks/90-stop-log-invocation.py` (also in baseline)
- `scripts/analyze_invocations.py` — produces dead-skill report read by `/audit`

---

## 6. ROUTER.md Template

```markdown
# Claude Code router — {{project_name}}

The user's intent dictates which artifact handles a request. Consult this first.

## Local stack
- Language: {{language}}
- Build: `{{build}}`  •  Test: `{{test}}`  •  Lint: `{{lint}}`
- See `.claude/rules/*` for path-scoped conventions.

## Workflows (skills auto-trigger; also explicit /skill-name)

<!-- managed:baseline -->
| User says | Skill | Notes |
|---|---|---|
| "commit", "save", "check in" | `skills/commit` | Chains to open-pr if pr-flow installed |
<!-- /managed:baseline -->

<!-- managed:pack-pr-flow -->
<!-- /managed:pack-pr-flow -->

<!-- managed:pack-data-science -->
<!-- /managed:pack-data-science -->

<!-- managed:pack-llm-extraction -->
<!-- /managed:pack-llm-extraction -->

(etc. per pack)

## Delegations (subagents)

<!-- managed:pack-pr-flow -->
<!-- /managed:pack-pr-flow -->

## Reference (read on demand — Claude: don't load all of this; consult INDEX first)

`.claude/reference/INDEX.md` — catalog of reference docs in this repo.
Consult before designing schemas, prompts, or extractors.

<!-- managed:pack-llm-extraction -->
<!-- /managed:pack-llm-extraction -->

<!-- managed:pack-data-science -->
<!-- /managed:pack-data-science -->

## Hard constraints (hooks; cannot be bypassed without editing the hook)

- Reads of `**/.env*`, `**/credentials*`, `**/.ssh/**`, `**/.aws/**`, `**/.gnupg/**` → DENIED
- `git push --force/-f/--force-with-lease/+ref` to `{main, master, develop, release/*}` → DENIED
- `rm -rf /`, `rm -rf ~`, `rm -rf $HOME` → DENIED
- `curl ... | sh`, `wget ... | bash`, `sudo *` → DENIED
- Edits to `.git/**` or `.claude/hooks/**` → DENIED in baseline; allow via /approve-hooks

## Extension policy
- New workflow → add a skill; append row to the appropriate `managed:*` block above.
- New deny → edit `settings.json` AND the corresponding hook script.
- `/upgrade` regenerates managed-block content; user content outside managed blocks is preserved.
```

---

## 7. settings.json baseline (final)

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
      "Bash(git push:*)",
      "Bash(git reset --hard*)", "Bash(git rebase -i*)",
      "WebFetch", "Bash(pip install:*)", "Bash(npm install:*)", "Bash(uv add:*)"
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
    ],
    "Stop": [
      { "matcher": "",
        "hooks": [{ "type": "command",
                    "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/90-stop-log-invocation.py",
                    "timeout": 5 }] }
    ]
  },
  "includeCoAuthoredBy": false
}
```

Protected-branch list lives in `.claude/.meta/protected-branches.json` (`["main","master","develop","release/*"]`); `20-pre-deny-destructive.py` reads it.

---

## 8. Triggering Convention (final, with examples)

Template:
```
<First sentence: leads with keyword users say; states capability in third person.>
<Optional second sentence: edge cases or expected inputs.>
Use when the user says "<verbatim 1>", "<verbatim 2>", "<verbatim 3>",
asks about <symptom 1>, <symptom 2>, or mentions <noun 1>, <noun 2>.
NOT for <negative scope referencing the most-similar other artifact>.
```

Hard rules (lint-checked, advisory):
- 600–1200 chars
- ≥5 keyword/symptom variants (user-language, not internal names)
- ≥2 verbatim quoted user phrases
- One `NOT for ... use X instead` clause
- Third person

Good example (`commit` baseline skill):
```
Stages and commits the current changes after running the project's lint/test gate.
Inspects `git status` and `git diff`, drafts a concise commit message from the
diff (subject + 1-2-line body explaining the *why*), runs the local lint/test if
fast, and creates the commit. Use when the user says "commit", "commit this",
"save changes", "check in", "stage and commit", asks about wrapping up a piece
of work, or finishes a logical unit of change. NOT for opening a pull request —
use the `open-pr` skill from the +pr-flow pack instead.
```

Length: ~620 chars. 8 keyword variants. 5 quoted phrases. Negative scope. Third person.

---

## 9. /setup Flow (final)

1. Read working directory.
2. Detect stack: `package.json` → node; `pyproject.toml` → python; `Cargo.toml` → rust; `go.mod` → go; `requirements.txt` → python. Multi-detection allowed.
3. If `.claude/` exists → switch to `/upgrade`.
4. Build dry-run plan: file list + diff.
5. Multi-select prompt (Claude renders as numbered list):
   - `[x] +data-science`
   - `[x] +visualization`
   - `[x] +llm-app`
   - `[x] +llm-extraction`
   - `[x] +security-hardening`
   - `[x] +telemetry` (already in baseline)
   - `[ ] +pr-flow`
   - `[ ] +test-tooling`
   - `[ ] +monorepo`
6. Confirm.
7. Render templates with `{{stack}}`, `{{build}}`, `{{test}}`, `{{lint}}`, `{{project_name}}` substitutions.
8. Copy pack files; insert managed-block rows.
9. Append `.gitignore` lines inside `<!-- managed:claude-folder-handler -->` block.
10. Regenerate `hooks.lock`.
11. Print next steps.

---

## 10. /audit Output Example

```
Audit of .claude/ — May 18 2026, claude-folder-handler v0.1.0

Drift
  • hooks.lock matches all 5 hook files                          ✓
  • All skills in packs.json present on disk                     ✓
  • CLAUDE.md is 38 lines (limit 80)                             ✓

Descriptions (advisory; +security-hardening lint)
  • skills/commit:           passes all checks                   ✓
  • skills/inspect-df:       3 keyword variants (≥5 required)    ⚠
  • agents/data-explorer:    missing "NOT for" clause            ⚠

Telemetry (+telemetry pack)
  • skills/clean-data:       0 invocations in 30 days            ⚠ stale
  • agents/reviewer:         12 invocations, 100% success        ✓

Reference
  • reference/datasets/cohort-A.md last-reviewed 2025-10-12       ⚠ >180d
  • reference/schemas/ — 4 entries, all fresh                    ✓

Exit code: 2 (warnings present)
```

---

## 11. Implementation Phases

| Phase | Output | Files touched |
|---|---|---|
| P0 | `install.sh`, top-level README, hybrid `docs/` skeleton, `skill/SKILL.md`, `skill/VERSION`, `skill/scripts/self_test.py` | ~6 |
| P1 | Baseline template: `CLAUDE.md.tmpl`, `ROUTER.md.tmpl`, `settings.json.tmpl`, `.meta/*`, `rules/00-global.md`, `skills/commit/SKILL.md`, all 4 baseline hooks + `lib/` | ~14 |
| P2 | `/setup` slash command + `scripts/setup.py` + `scripts/lib/detect_stack.py`, `managed_blocks.py`, `hooks_lock.py` | ~5 |
| P3 | `/audit` + `/upgrade` + `/approve-hooks` + their scripts | ~6 |
| P4 | Packs: `+pr-flow`, `+test-tooling` | ~10 |
| P5 | Packs: `+data-science`, `+visualization` | ~12 |
| P6 | Packs: `+llm-app`, `+llm-extraction` | ~16 |
| P7 | Packs: `+monorepo`, `+security-hardening` | ~10 |
| P8 | End-to-end dogfood test in a throwaway repo; document findings; tag v0.1.0 release | ~3 |

Commits: one per phase (~9 total). Each phase tested in isolation before moving on.

---

## 12. What I will NOT do (out of scope for v0.1)

- Plugin marketplace packaging (deferred to v0.2)
- Windows-native support beyond what `uv` + `git` give us free
- Telemetry dashboard / web UI (data is local JSONL only)
- Auto-update notification (user re-runs `install.sh` manually)
- Skill marketplace / pack discovery (packs are bundled in this repo only)
- Multi-user workspace settings
- Internationalization

---

## 13. Approval Gate

If you say **"go"** (or "implement", "build it", "proceed"), I will start at Phase P0 and commit per phase to `claude/design-claude-folder-system-YmUMu`. I will NOT push to main or open a PR without explicit instruction.

If you want changes first, list them — I'll revise this doc and re-present.
