# `.claude/` System — v4 (MCP / uvx distribution)

> **Reframe of v3.** All v3 decisions stand; distribution channel changes from
> `curl|sh + ~/.claude/skills/` to a PyPI package run via `uvx`, exposing both
> an MCP server (for Claude) and a CLI (for power users).

---

## 0. Why this changes

User wants install ergonomics like an MCP server config:

```json
{
  "mcpServers": {
    "claude-folder-handler": {
      "command": "uvx",
      "args": ["claude-folder-handler@latest"]
    }
  }
}
```

Strictly better than v3's `install.sh + git clone + ~/.claude/skills/` because:

- Cross-platform out of the box (uvx handles install + sandboxing)
- Native version pinning (`@0.1.0`, `@latest`, semver)
- Auto-update on `uvx --refresh` (no manual `git pull`)
- No filesystem install state to track or clean up
- Same pattern user already uses for `zotero`, etc. — zero new mental model

Trade-off accepted: the package must be published to PyPI to make `uvx` work end-to-end. Until first publish, users can `uvx --from git+https://github.com/Sdamirsa/claude-folder-handler-SKILL claude-folder-handler` as a fallback.

---

## 1. Repo Layout (revised)

```
claude-folder-handler-SKILL/
├── README.md                              # hybrid: short top + docs/
├── pyproject.toml                         # PyPI package metadata, console scripts
├── docs/                                  # public-facing deep docs
│   ├── architecture.md
│   ├── packs.md
│   ├── triggering-convention.md
│   ├── upgrade-flow.md
│   ├── security-model.md
│   └── mcp-setup.md                       # how to add the MCP block; troubleshooting
├── design/                                # v0..v4 + critiques
├── tests/                                 # pytest, run via uv run pytest
└── src/
    └── claude_folder_handler/
        ├── __init__.py
        ├── __main__.py                    # `python -m claude_folder_handler`
        ├── cli.py                         # argparse: setup, upgrade, install-pack, audit, etc.
        ├── mcp_server.py                  # registers 6 MCP tools (see §3)
        ├── core/
        │   ├── detect_stack.py
        │   ├── managed_blocks.py
        │   ├── hooks_lock.py
        │   ├── description_lint.py
        │   ├── pack_loader.py
        │   ├── scaffold.py                # write template + selected packs
        │   ├── upgrade.py                 # three-way merge
        │   └── audit.py                   # drift + lint + stale checks
        └── data/                          # bundled via importlib.resources
            ├── template/                  # the lean baseline (same content as v3)
            │   ├── CLAUDE.md.tmpl
            │   ├── _mcp.json.example      # leading underscore avoids package-data confusion
            │   ├── _gitignore.snippet
            │   └── claude/                # rendered into .claude/ at scaffold time
            │       ├── README.md
            │       ├── ROUTER.md.tmpl
            │       ├── settings.json.tmpl
            │       ├── meta/
            │       │   ├── version.tmpl
            │       │   ├── hooks.lock.tmpl
            │       │   └── packs.json.tmpl
            │       ├── rules/00-global.md
            │       ├── skills/commit/SKILL.md
            │       ├── hooks/
            │       │   ├── 00-session-start.py
            │       │   ├── 10-pre-deny-secrets.py
            │       │   ├── 20-pre-deny-destructive.py
            │       │   ├── 90-stop-log-invocation.py
            │       │   └── lib/{__init__,payload,paths,bash_parse}.py
            │       └── reference/
            │           ├── INDEX.md
            │           └── README.md
            └── packs/
                ├── pr-flow/                    # each pack: pack.toml + content
                ├── test-tooling/
                ├── data-science/
                ├── visualization/
                ├── llm-app/
                ├── llm-extraction/
                ├── monorepo/
                ├── security-hardening/
                └── telemetry/
```

Note: package-data files use `_mcp.json.example` / `_gitignore.snippet` names because tools like setuptools sometimes special-case dotfiles. They're renamed at scaffold time to `.mcp.json.example` / `.gitignore`.

---

## 2. pyproject.toml (the install contract)

```toml
[project]
name = "claude-folder-handler"
version = "0.1.0"
description = "Scaffold, upgrade, and audit .claude/ folders for coding repos. LLM-scientist friendly: data-science, visualization, LLM app, LLM extraction packs."
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0",            # the Anthropic Python MCP SDK
    "tomli; python_version < '3.11'",   # belt-and-suspenders; unused on 3.11+
]
authors = [{ name = "Sdamirsa" }]
readme = "README.md"
license = { file = "LICENSE" }
keywords = ["claude", "claude-code", "scaffolding", "mcp", "data-science", "llm"]

[project.scripts]
claude-folder-handler = "claude_folder_handler.cli:main"

# uvx will invoke this when no subcommand is given → defaults to MCP server mode
# When user runs `uvx claude-folder-handler setup`, CLI mode is used.
[project.entry-points."mcp.servers"]
default = "claude_folder_handler.mcp_server:run"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/claude_folder_handler"]

[tool.hatch.build.targets.wheel.force-include]
"src/claude_folder_handler/data" = "claude_folder_handler/data"
```

Console-script behavior:

| Invocation | What runs |
|---|---|
| `uvx claude-folder-handler` (no args) | MCP server on stdio — what the MCP config triggers |
| `uvx claude-folder-handler setup` | CLI subcommand: scaffold current repo |
| `uvx claude-folder-handler install-pack data-science` | CLI subcommand: install a pack |
| `uvx claude-folder-handler audit` | CLI subcommand: audit current repo |
| `uvx claude-folder-handler upgrade` | CLI subcommand: three-way merge against latest template |
| `uvx claude-folder-handler list-packs` | CLI subcommand: print pack catalog |
| `uvx claude-folder-handler --version` | Print version |
| `uv tool install claude-folder-handler` | Persistent install on PATH |

The CLI and MCP server share the same `core/` modules — same scaffold logic, two surfaces.

---

## 3. MCP Tools (the user-facing API for Claude)

The MCP server registers six tools. Each tool's description follows the v3 triggering convention (600–1200 chars, ≥5 keyword variants, ≥2 quoted phrases, NOT-for clause, third person).

### Tool 1: `setup_claude_folder`

**Schema:**
```python
{
  "name": "setup_claude_folder",
  "description": """Scaffolds the lean baseline `.claude/` configuration plus
selected packs in the current working repository. Detects stack from
package.json, pyproject.toml, Cargo.toml, or go.mod and substitutes
build/test/lint commands into the generated CLAUDE.md and ROUTER.md.
Pre-selects LLM-scientist defaults (+data-science, +visualization, +llm-app,
+llm-extraction, +security-hardening, +telemetry) unless overridden.
Use when the user says "set up .claude", "init claude code in this repo",
"scaffold claude config", "bootstrap claude for this project", "create a
.claude folder here", or asks how to "organize claude for a new project".
Refuses if `.claude/` already exists — direct the user to upgrade_claude_folder
instead. NOT for editing existing skill bodies (edit the SKILL.md files
directly), and NOT for general project scaffolding like `npm init`,
`create-next-app`, or framework setup.""",
  "inputSchema": {
    "type": "object",
    "properties": {
      "packs": {"type": "array", "items": {"type": "string"},
                "description": "Packs to install. Omit to use LLM-scientist defaults."},
      "cwd": {"type": "string", "description": "Target repo. Defaults to current working dir."},
      "dry_run": {"type": "boolean", "default": false}
    }
  }
}
```

**Behavior:** identical to v3's `/setup` flow. Returns a JSON summary of files written, packs installed, and next-step suggestions for Claude to surface.

### Tool 2: `install_pack`

```python
{
  "name": "install_pack",
  "description": """Installs a single named pack into an existing .claude/
configuration. Available packs: pr-flow, test-tooling, data-science,
visualization, llm-app, llm-extraction, monorepo, security-hardening,
telemetry. Refuses on file-level conflicts with already-installed packs.
Updates ROUTER.md managed blocks, settings.json overlay, and
.claude/.meta/packs.json. Regenerates hooks.lock. Use when the user says
"install the X pack", "add data-science", "I want the llm-extraction pack",
"add visualization tools", "bring in pr-flow", or names a pack by name. NOT
for first-time .claude/ setup — use setup_claude_folder. NOT for upgrading
existing pack content — use upgrade_claude_folder.""",
  "inputSchema": {"type":"object", "required":["name"],
                  "properties":{"name":{"type":"string"}}}
}
```

### Tool 3: `upgrade_claude_folder`

```python
{
  "name": "upgrade_claude_folder",
  "description": """Three-way merges the existing `.claude/` configuration in
the current repo against the latest bundled template. Overwrites only content
inside `<!-- managed:* -->` blocks; user content outside managed blocks is
preserved untouched. Updates .claude/.meta/version and regenerates hooks.lock.
Use when the user says "upgrade my claude setup", "update claude code config",
"pull the latest .claude template", "my .claude is out of date", or after
the meta-tool itself is updated. NOT for installing new packs — use
install_pack. NOT for first-time setup — use setup_claude_folder.""",
  "inputSchema": {"type":"object",
                  "properties":{"dry_run":{"type":"boolean","default":true}}}
}
```

### Tool 4: `audit_claude_folder`

```python
{
  "name": "audit_claude_folder",
  "description": """Inspects the current repo's `.claude/` for drift, lint
violations, and staleness. Reports: hooks.lock mismatches, skills missing
from packs.json, descriptions failing the triggering convention, CLAUDE.md
over 80 lines, settings.json with >15 allow rules, stale reference docs
(last-reviewed > 180d), and dead skills (zero invocations in 30 days, if
+telemetry installed). Returns a structured warning list and exit code.
Use when the user says "audit my claude folder", "check my claude config",
"is my .claude healthy", "lint my claude setup", or "what's wrong with my
.claude directory". NOT for fixing issues — only reports them.""",
  "inputSchema": {"type":"object","properties":{}}
}
```

### Tool 5: `approve_hooks`

```python
{
  "name": "approve_hooks",
  "description": """Regenerates `.claude/.meta/hooks.lock` from the current
hook script contents. Required after legitimate hook edits or first checkout
of a branch with hook changes — the SessionStart hook refuses to proceed
otherwise (security-hardening pack). Use when the user says "approve hooks",
"trust the hook changes", "unblock hooks", "regenerate hooks lock", or after
git pull surfaces a hook-lock mismatch warning. NOT for first-time setup
(setup_claude_folder generates the lock automatically) and NOT for editing
hooks themselves.""",
  "inputSchema": {"type":"object","properties":{}}
}
```

### Tool 6: `list_packs`

```python
{
  "name": "list_packs",
  "description": """Returns the catalog of available packs with descriptions,
file counts, and dependencies. Read-only. Use when the user asks "what packs
are available", "show me the packs", "what can I install", "list packs", or
is browsing options before picking. NOT for inspecting installed packs in a
specific repo — use audit_claude_folder.""",
  "inputSchema": {"type":"object","properties":{}}
}
```

---

## 4. Install Instructions (final)

### Step 1 (one-time): Add MCP server to user settings

Open `~/.claude/settings.json` and add:

```json
{
  "mcpServers": {
    "claude-folder-handler": {
      "command": "uvx",
      "args": ["claude-folder-handler@latest"]
    }
  }
}
```

Pin to a specific version with `["claude-folder-handler@0.1.0"]` if you prefer stability over freshness.

### Step 2: Restart Claude Code

The MCP server starts on the next session; tools appear in Claude's tool list.

### Step 3: Use it

Open Claude in any repo and say one of:
- "set up .claude here"
- "install the data-science pack"
- "audit my claude config"
- "what packs are available"

Claude invokes the corresponding MCP tool.

### Alternative (no MCP): one-shot CLI

```bash
uvx claude-folder-handler setup
uvx claude-folder-handler install-pack llm-extraction
uvx claude-folder-handler audit
```

Useful for CI, scripted setups, or when you just want a single scaffold without MCP wiring.

### Pre-publish bootstrap (until v0.1.0 is on PyPI)

```json
{
  "mcpServers": {
    "claude-folder-handler": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Sdamirsa/claude-folder-handler-SKILL@main",
        "claude-folder-handler"
      ]
    }
  }
}
```

This is what you'll use until I publish to PyPI in P9.

---

## 5. What Stays Unchanged from v3

All design decisions, security posture, packs, ROUTER.md template, hooks (`00-session-start`, `10-pre-deny-secrets`, `20-pre-deny-destructive`, `90-stop-log-invocation`), `settings.json` baseline, triggering convention, reference-folder model, lint rules, /audit output, etc. — all carried forward intact. v3 §3–§10 are still authoritative for *content*; only §1, §2, §9 distribution mechanics are replaced by this v4.

---

## 6. Revised Implementation Phases

| Phase | Output |
|---|---|
| P0 | `pyproject.toml`, package skeleton (`src/claude_folder_handler/{__init__,__main__,cli,mcp_server}.py`), top-level hybrid README, `docs/` skeleton, `tests/test_smoke.py`, working `uvx --from git+... claude-folder-handler --version` |
| P1 | Baseline template as bundled `data/template/*` (CLAUDE.md.tmpl, ROUTER.md.tmpl, settings.json.tmpl, .meta/, rules/00-global, skills/commit, 4 baseline hooks + lib, reference/INDEX+README) |
| P2 | `core/scaffold.py` + `core/detect_stack.py` + `core/managed_blocks.py` + `cli.py setup` + MCP tool `setup_claude_folder` + tests |
| P3 | `core/audit.py` + `core/upgrade.py` + `core/hooks_lock.py` + `cli.py {audit,upgrade,approve-hooks}` + MCP tools 3, 4, 5 + tests |
| P4 | Packs: `pr-flow`, `test-tooling`; `core/pack_loader.py` + `cli.py install-pack` + MCP tool 2, 6; tests for pack install + conflict detection |
| P5 | Packs: `data-science`, `visualization` |
| P6 | Packs: `llm-app`, `llm-extraction` |
| P7 | Packs: `monorepo`, `security-hardening`, `telemetry` |
| P8 | End-to-end dogfood: scaffold a throwaway repo, install all packs, audit, upgrade; document findings in `docs/dogfood-run.md` |
| P9 | `pip install build twine`, `python -m build`, push tag `v0.1.0`, publish to PyPI via `twine`, GitHub Release with install snippet |

10 phases. Commit per phase.

---

## 7. Risks Specific to This Reframe

| Risk | Mitigation |
|---|---|
| PyPI not yet published → `uvx claude-folder-handler` fails | Document the `--from git+...` fallback in README §Install (until P9) |
| MCP SDK breaking changes | Pin `mcp>=1.0,<2.0` in pyproject; pin in CI |
| `uvx` cache stale → user sees old version | Document `uvx --refresh` and version-pin syntax in `docs/mcp-setup.md` |
| Bundled data files not found by importlib.resources | `hatch.build.targets.wheel.force-include` covers it; smoke test verifies in P0 |
| MCP tool descriptions hit token-budget limits | Each is ≤700 chars (well under 1024 limit); lint enforced in tests |
| User's `~/.claude/settings.json` has bad JSON | Document the exact merge block; provide `claude-folder-handler print-mcp-config` helper |
| Conflict with v3 install (if user already ran the old install.sh) | Provide `claude-folder-handler migrate-from-v3` helper that detects ~/.claude/skills/claude-folder-handler and offers to remove it. (Trivial since v3 never shipped.) |

---

## 8. Approval Gate

This supersedes v3 §11–§13. If you say **"go"** I start at P0:

1. Write `pyproject.toml`, the package skeleton (cli.py, mcp_server.py, core/ stubs), top-level README pointing at MCP install, `docs/mcp-setup.md`, `tests/test_smoke.py`.
2. Smoke-test: `uvx --from . claude-folder-handler --version` returns `0.1.0.dev0`.
3. Commit and push.

Then P1 (baseline template), P2 (setup tool), etc.

If anything in v4 needs to change first — list it.
