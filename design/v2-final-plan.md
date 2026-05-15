# `.claude/` System — v2 Final Plan

> Status: **Awaiting user review.** Do NOT implement until approved.
>
> Carries forward v0 principles + v1 reframe + user preferences:
> - Lean baseline + opt-in packs, with packs tilted toward LLM scientist work (data science, viz, LLM app dev, LLM extraction).
> - All runtime code is Python with UV inline-deps. No bash.
> - Meta-skill installed as a global skill via `curl|sh`; plugin path deferred.

---

## 1. Repository = Two Layers

This repo (`claude-folder-handler-SKILL`) ships **two distinct artifacts**:

1. **The meta-skill** — a global skill that lives at `~/.claude/skills/claude-folder-handler/` after install. Triggers in any repo.
2. **The template + packs** — the actual `.claude/` content that gets scaffolded into target repos.

These live side-by-side in this repo (`skill/` and `template/` + `packs/`). The install script copies `skill/` to `~/.claude/skills/claude-folder-handler/` and bundles `template/` and `packs/` inside it.

```
claude-folder-handler-SKILL/                  # this repo
├── README.md                                 # human-facing: what this is, install, usage
├── install.sh                                # the curl|sh one-liner; uv-installs deps, copies skill
├── skill/                                    # the meta-skill (lands in ~/.claude/skills/)
│   ├── SKILL.md                              # the meta-skill itself (triggers /setup, /upgrade, /install-pack)
│   ├── commands/
│   │   ├── setup.md                          # /setup
│   │   ├── upgrade.md                        # /upgrade
│   │   ├── install-pack.md                   # /install-pack <name>
│   │   └── audit.md                          # /audit
│   ├── scripts/                              # Python UV scripts the skill calls via Bash tool
│   │   ├── setup.py                          # detect stack, scaffold .claude/
│   │   ├── upgrade.py                        # three-way merge
│   │   ├── install_pack.py                   # copy pack content
│   │   ├── audit.py                          # drift + lint checks
│   │   └── lib/                              # shared: detect_stack, managed_blocks, hooks_lock
│   ├── template/                             # the lean baseline (what /setup copies as v1)
│   │   ├── CLAUDE.md.tmpl                    # ≤40 lines, {{stack}}/{{commands}} substitutions
│   │   ├── .mcp.json.example                 # gitignored target; example shipped
│   │   ├── .gitignore.snippet                # appended inside <!-- managed:* --> block
│   │   └── .claude/
│   │       ├── README.md                     # navigation index
│   │       ├── ROUTER.md.tmpl                # the SessionStart-injected router
│   │       ├── settings.json.tmpl            # permissions + hooks wiring
│   │       ├── .meta/
│   │       │   ├── version                   # filled with template version at /setup
│   │       │   ├── hooks.lock                # sha256 of each hook, generated
│   │       │   └── packs.json                # which packs installed
│   │       ├── rules/
│   │       │   └── 00-global.md
│   │       ├── skills/
│   │       │   └── commit/SKILL.md           # the one baseline skill
│   │       └── hooks/
│   │           ├── 00-session-start.py
│   │           ├── 10-pre-deny-secrets.py
│   │           ├── 20-pre-deny-destructive.py
│   │           └── lib/                      # Python helpers
│   └── packs/                                # opt-in packs (see §3)
│       ├── pr-flow/
│       ├── test-tooling/
│       ├── data-science/
│       ├── visualization/
│       ├── llm-app/
│       ├── llm-extraction/
│       ├── monorepo/
│       ├── security-hardening/
│       └── telemetry/
└── design/                                   # already exists: v0, v1, critiques, this file
```

---

## 2. Install Flow

```bash
curl -fsSL https://raw.githubusercontent.com/Sdamirsa/claude-folder-handler-SKILL/main/install.sh | sh
```

`install.sh` does (in pure POSIX shell, the only non-Python file):
1. Check `uv` is on PATH. If missing, install via `curl -LsSf https://astral.sh/uv/install.sh | sh`.
2. `git clone --depth 1 ...` into `~/.claude/skills/claude-folder-handler/`.
3. Run `uv run python ~/.claude/skills/claude-folder-handler/scripts/self_test.py` — verifies hooks parse, scripts importable, templates render.
4. Print: "Installed. Open Claude Code in any repo and say *set up .claude here*."

Update: re-run the same command (it does `git pull` if dir exists).
Uninstall: `rm -rf ~/.claude/skills/claude-folder-handler/`.

---

## 3. Packs (your profile: data science, viz, LLM)

Every pack has a uniform shape:

```
packs/<name>/
├── pack.toml                       # metadata: deps, files, manifest entries
├── description.md                  # what this pack does, when to install
├── skills/                         # SKILL.md files copied to .claude/skills/
├── agents/                         # subagent .md files (if any)
├── rules/                          # path-scoped rules
├── hooks/                          # additional hooks (numeric prefix for ordering)
├── router-rows.md                  # rows to append into ROUTER.md (inside <!-- managed:pack-name --> block)
└── settings-overlay.json           # additive merge into settings.json (inside managed block)
```

### Baseline (always installed)

| Artifact | Purpose |
|---|---|
| `skills/commit/SKILL.md` | "commit this", "save changes", "check in" → stage diff + msg + commit |
| `hooks/00-session-start.py` | Inject ROUTER.md + git context + drift warnings as `additionalContext` |
| `hooks/10-pre-deny-secrets.py` | Block reads/writes of credential files via canonicalized paths |
| `hooks/20-pre-deny-destructive.py` | Block rm -rf root/home, git push --force to protected, sudo, curl \| sh |
| `rules/00-global.md` | Always-loaded conventions (≤40 lines) |
| `ROUTER.md` | Triggering decision table; SessionStart-injected |

### Pack: `+pr-flow`

| Artifact | Purpose |
|---|---|
| `skills/open-pr/SKILL.md` | "open a PR", "ship this" → commit if needed, push, gh pr create with summary |
| `skills/rebase-clean/SKILL.md` | "rebase on main", "clean up history" → rebase + auto-resolve trivial conflicts |
| `agents/reviewer.md` | "review my changes critically" → read-only critique with priority categorization |

### Pack: `+test-tooling`

| Artifact | Purpose |
|---|---|
| `skills/debug-failing-test/SKILL.md` | "test is red", "this is broken", "why doesn't X work" → reproduce, diagnose, propose fix |
| `agents/test-writer.md` | "write a test for X" → reads X, generates test in project's conventions |

### Pack: `+data-science` ← **for you**

| Artifact | Purpose |
|---|---|
| `skills/inspect-df/SKILL.md` | "what's in this dataframe", "summarize the data", "what columns does X have" → dtypes, head, describe, null-counts, cardinality |
| `skills/clean-data/SKILL.md` | "clean this", "preprocess", "handle missing" → pandas pipeline with checkpoints |
| `agents/data-explorer.md` | "explore this dataset" → opens csv/parquet, profiles, returns summary |
| `rules/pandas.md` (paths: `**/*.ipynb`, `**/*.py` that import pandas) | Conventions: chained assignment, copy-on-write, no `inplace=True`, `pd.read_*` defaults |
| `rules/notebooks.md` (paths: `**/*.ipynb`) | Notebook hygiene: clear outputs before commit, kernel pinning, naming convention |

### Pack: `+visualization` ← **for you**

| Artifact | Purpose |
|---|---|
| `skills/quick-chart/SKILL.md` | "plot X", "make a chart of Y", "visualize this" → matplotlib/plotly/altair based on context; saves png |
| `skills/chart-review/SKILL.md` | "is this chart good", "critique this viz" → axes, encoding, color, accessibility |
| `rules/plotting.md` (paths: files that import matplotlib/plotly/altair) | Style: figure size, dpi, font sizing, color-blind safe palettes, save-format conventions |

### Pack: `+llm-app` ← **for you**

| Artifact | Purpose |
|---|---|
| `skills/anthropic-sdk-bootstrap/SKILL.md` | "set up anthropic client", "scaffold an agent" → installs anthropic, scaffolds client with prompt caching, .env handling, retries |
| `skills/migrate-model-version/SKILL.md` | "upgrade to claude X.Y" → finds model IDs, updates, runs eval if present |
| `rules/anthropic-sdk.md` (paths: files that `import anthropic`) | Prompt caching by default, model-ID style, streaming patterns, error handling, async usage |
| `hooks/15-warn-stale-model.py` (PostToolUse on Edit/Write) | Warn if a deprecated/retired model ID is written into a file |

### Pack: `+llm-extraction` ← **for you**

| Artifact | Purpose |
|---|---|
| `skills/extract-structured/SKILL.md` | "extract X from these documents", "parse this into JSON" → tool-use + JSON-schema validation pattern |
| `skills/build-extractor-eval/SKILL.md` | "evaluate the extractor", "score this extraction" → eval harness scaffold |
| `skills/batch-extract/SKILL.md` | "run this on all my files" → batch API or async fan-out with checkpointing |
| `agents/schema-designer.md` | "design a JSON schema for X" → returns schema + example + edge cases |
| `rules/extraction.md` (paths: `extractors/**`, `pipelines/**`) | Schema-first design, log raw input on validation fail, version schemas |

### Pack: `+monorepo`

| Artifact | Purpose |
|---|---|
| Generator that writes `apps/*/CLAUDE.md` and `packages/*/CLAUDE.md` stubs | Per-package, lazy-loaded |
| `rules/per-package.md` template | Path-scoped per-package conventions |

### Pack: `+security-hardening`

| Artifact | Purpose |
|---|---|
| Tighter `settings.json` overlay (WebFetch domain allowlist, broader denies) | Defense in depth |
| `hooks/05-verify-hooks-lock.py` (SessionStart, runs before others) | Refuses if `hooks.lock` mismatches |
| `scripts/lint_descriptions.py` (runs in `/audit`) | Checks every SKILL.md description meets the triggering convention |

### Pack: `+telemetry`

| Artifact | Purpose |
|---|---|
| `hooks/90-log-invocation.py` (Stop hook) | Append `{skill_invoked?, user_intent, success, duration}` to `.claude/.cache/invocations.jsonl` |
| `/audit` reads this log to surface "skills never invoked in 30 days" → candidate for removal |

---

## 4. UV Everywhere

| Surface | How UV is used |
|---|---|
| Hooks (`00-session-start.py`, etc.) | First line: `#!/usr/bin/env -S uv run --script`. Inline deps in `# /// script` header. |
| `/setup`, `/upgrade`, `/audit`, `/install-pack` scripts | Same UV-script pattern. Called via the Bash tool from the slash-command markdown. |
| `lib/` helpers | Python modules. Importable from the UV scripts. No deps where possible (stdlib only). |
| Tests | `uv run pytest` |
| `install.sh` itself | Pure POSIX shell (the only non-Python). Bootstraps `uv` if missing. |

Hooks dependency policy: stdlib-only when possible (so first-run is fast). The only place we'd reach for deps: `+llm-app`'s `15-warn-stale-model.py` may want `httpx` to query a model-list endpoint — opt-in only.

---

## 5. ROUTER.md (template form)

`ROUTER.md` ships with `<!-- managed:* -->` blocks per pack so `/upgrade` and `/install-pack` can append/remove rows without clobbering user edits.

```markdown
# Claude Code router — {{project_name}}

The user's intent dictates which artifact handles a request. Consult this first.

## Workflows (skills auto-trigger; you can also explicitly invoke `/skill-name`)

<!-- managed:baseline -->
| User says... | Skill | Notes |
|---|---|---|
| "commit", "save changes", "check in" | skills/commit | Chains to open-pr if pr-flow pack installed |
<!-- /managed:baseline -->

<!-- managed:pack-pr-flow -->
| "open a PR", "ship this", "send for review" | skills/open-pr | Run after commit; auto-pushes |
| "rebase on main", "clean up history" | skills/rebase-clean | Aborts on non-trivial conflicts |
<!-- /managed:pack-pr-flow -->

<!-- managed:pack-data-science -->
| "what's in this dataframe", "summarize the data" | skills/inspect-df | Read-only |
| "clean this", "preprocess" | skills/clean-data | Generates pipeline; user reviews each step |
<!-- /managed:pack-data-science -->

(rows appended per installed pack)

## Delegations (subagents)

<!-- managed:baseline -->
(none in baseline)
<!-- /managed:baseline -->

<!-- managed:pack-pr-flow -->
| Intent | Agent |
|---|---|
| "review my changes critically" | agents/reviewer |
<!-- /managed:pack-pr-flow -->

## Hard constraints (enforced by hooks — cannot be bypassed)

- Reads of `**/.env*`, `**/credentials*`, `**/.ssh/**`, `**/.aws/**`, `**/.gnupg/**`, `~/.kube/config` → DENIED
- `git push --force` to protected branches → DENIED
- `rm -rf` of `/`, `~`, `$HOME` → DENIED
- `curl ... | sh`, `wget ... | bash` → DENIED
- Edits to `.git/**` or `.claude/hooks/**` require explicit confirm

## Local stack
- Language: {{language}}
- Build: `{{build}}` | Test: `{{test}}` | Lint: `{{lint}}`
- See `.claude/rules/*` for path-scoped conventions.

## Extension policy
- New workflow → add a skill, append a `managed:pack-*` row here.
- This file is REGENERATED by `/upgrade` and `/install-pack`. Edit outside managed blocks only.
```

---

## 6. Triggering Convention (final)

All `SKILL.md` and `agents/*.md` descriptions conform to:

```
<First sentence: leads with the keyword users say; states capability in third person.>
<Optional second sentence: edge cases or expected inputs.>
Use when the user says "<verbatim phrase 1>", "<phrase 2>", "<phrase 3>",
asks about <symptom 1>, <symptom 2>, or mentions <noun 1>, <noun 2>.
NOT for <negative scope referencing the most-similar other artifact>.
```

Hard rules (lint-checked by `+security-hardening`'s `lint_descriptions.py`):
- 600–1200 chars.
- ≥5 keyword variants from how users actually talk (symptom phrases, not internal names).
- ≥2 verbatim quoted phrases.
- One `NOT for ... use X instead` clause.
- Third person.

---

## 7. settings.json (baseline)

(Identical to v1 §7. WebFetch allowlist added by `+security-hardening`.)

Key denies:
```
Read(**/.env*), Read(**/credentials*), Read(**/id_rsa*), Read(**/*.pem), Read(**/*.key),
Read(~/.ssh/**), Read(~/.aws/**), Read(~/.gnupg/**), Read(~/.kube/config),
Edit(**/.env*), Write(**/.env*),
Edit(**/.git/**), Write(**/.git/**),
Edit(**/.claude/hooks/**), Write(**/.claude/hooks/**),
Bash(rm -rf /*), Bash(rm -rf ~*), Bash(rm -rf $HOME*), Bash(sudo *),
Bash(curl * | sh), Bash(curl * | bash), Bash(wget * | sh),
Bash(curl *169.254.169.254*), Bash(curl *metadata.google.internal*)
```

Asks:
```
Bash(git push:*), Bash(git push --force*), Bash(git reset --hard*),
WebFetch, Bash(pip install:*), Bash(npm install:*)
```

Hooks: numeric-prefix-ordered. SessionStart, PreToolUse (Read|Edit|Write|Bash), PreToolUse (Bash).

---

## 8. /setup Flow

```
user says "set up .claude in this repo"
  ↓ meta-skill auto-triggers
  ↓ runs scripts/setup.py
  1. Detect stack (package.json / pyproject.toml / Cargo.toml / go.mod / requirements.txt).
  2. Check for existing .claude/ → if present, switch to /upgrade.
  3. Dry-run: list files to create + show diffs.
  4. Prompt: which packs? (multi-select via numbered list in Claude's response)
  5. On confirm:
     - Render template files with {{stack}}, {{commands}} substituted.
     - Append .gitignore inside <!-- managed:claude-folder-handler --> block.
     - Generate .claude/.meta/version, packs.json, hooks.lock.
     - Render ROUTER.md with selected pack rows in their managed blocks.
     - Run hooks self-test.
  6. Print next steps: try saying "commit this" or "/setup --help".
```

## 9. /upgrade Flow

```
user says "upgrade my claude setup"
  ↓ meta-skill triggers
  ↓ runs scripts/upgrade.py
  1. Read .claude/.meta/version → vN
  2. Read meta-skill version → vM
  3. For each file in template:
     - Identify managed blocks via <!-- managed:* --> markers.
     - Replace managed-block content with vM template.
     - Leave non-managed content untouched.
  4. Run hooks.lock regeneration.
  5. Show diff; ask for confirm.
  6. Apply.
```

## 10. /install-pack Flow

```
user says "install the data-science pack" or "/install-pack data-science"
  ↓ runs scripts/install_pack.py data-science
  1. Read packs/data-science/pack.toml.
  2. Check conflicts: any file already in .claude/ from another pack? Refuse on conflict.
  3. Copy pack files into .claude/.
  4. Append router-rows.md into ROUTER.md inside <!-- managed:pack-data-science --> block.
  5. Merge settings-overlay.json into settings.json inside managed block.
  6. Update .claude/.meta/packs.json.
  7. Regenerate hooks.lock.
```

## 11. /audit Flow

```
user says "audit my claude folder"
  ↓ runs scripts/audit.py
  1. Drift check: hooks.lock matches actual sha256? Skills in MANIFEST exist?
  2. Description lint: every SKILL.md / agents/*.md meets the triggering convention.
  3. Size check: CLAUDE.md ≤ 80 lines? settings.json has < 15 allow rules?
  4. Stale-skill check (+telemetry): skills with zero invocations in last 30d.
  5. Print findings as a numbered list.
```

---

## 12. Implementation Order (when approved)

| Phase | Output | Effort |
|---|---|---|
| **P0** Bootstrap | `install.sh`, `skill/SKILL.md`, `scripts/self_test.py`, README.md | small |
| **P1** Baseline template | `skill/template/*` complete (CLAUDE.md, ROUTER.md, settings.json, baseline skill, 3 hooks, rules/00-global) | medium |
| **P2** Setup script | `scripts/setup.py` (stack detection, file rendering, managed-block writing) | medium |
| **P3** Audit + upgrade | `scripts/audit.py`, `scripts/upgrade.py`, hooks.lock generator | medium |
| **P4** Pack: +pr-flow, +test-tooling | most universal packs first | medium |
| **P5** Pack: +data-science, +visualization | your priority | medium |
| **P6** Pack: +llm-app, +llm-extraction | your priority | medium |
| **P7** Pack: +monorepo, +security-hardening, +telemetry | hardening & breadth | small each |
| **P8** End-to-end test in a real repo | dogfood; capture observations | small |

I would suggest committing after each phase. Total: ~8 commits.

---

## 13. Open Decisions Still Needing Your Input

1. **install.sh hosting:** Should the curl|sh fetch from `raw.githubusercontent.com/Sdamirsa/claude-folder-handler-SKILL/main/install.sh`, or do you want a stable redirect (e.g., your own domain)?
2. **Default packs at /setup for your repos:** Should `/setup` for *your* projects default-check `+data-science +visualization +llm-app +llm-extraction +security-hardening`? Or leave the multi-select fully manual every time?
3. **Telemetry default:** ON or OFF in the baseline `/setup`? It's per-machine local logging only — no network. Default ON means /audit gets useful data quickly. Default OFF means strict privacy.
4. **Description-lint enforcement:** Should `+security-hardening`'s lint be ADVISORY (just warns) or BLOCKING (fails `/audit`, fails CI)?
5. **Stop / Hard-blocks vs Ask:** I have `git push --force` in `ask` (user confirms). Some setups prefer hard-deny on protected branches only. Confirm `ask` is OK or you want hard-deny.
6. **README of this repo:** Should the top-level README be aimed at YOU (a personal toolkit) or at PUBLIC users (so others can adopt it)? Affects tone, doc depth, install instructions.

---

## 14. Risks I'm Tracking

- **uv as a hard prerequisite.** If `uv` install fails, the whole system fails. Mitigation: `install.sh` checks first and gives a clear error with the official install URL.
- **`hooks.lock` drift on legitimate edits.** Every legitimate hook edit requires regenerating the lockfile, which means another commit. Slight friction; acceptable.
- **ROUTER.md staleness.** If a user adds a skill manually without using `/install-pack`, the router won't know. `/audit` will flag it.
- **Description-lint false negatives.** Regex can't catch "the description is vague" — only "missing required clauses". Net positive, not a complete defense.
- **Pack conflicts.** Two packs touching the same skill name. Resolved by refusing to install on conflict — user must uninstall one first.
