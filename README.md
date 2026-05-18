# claude-folder-handler

Scaffold, upgrade, and audit `.claude/` folders for any coding repo. Ships as
a **Claude Code MCP server** plus a CLI — install once, use everywhere.

Tuned for LLM-scientist work: data-science, visualization, LLM app dev, and
LLM extraction packs ship in the default install.

---

## Install

Add this one block to `~/.claude/settings.json`:

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

Restart Claude Code. Open any repo and say *"set up .claude here"*. The
`setup_claude_folder` MCP tool fires, detects your stack, scaffolds a lean
baseline, and installs the LLM-scientist pack defaults.

### Pin a version

```json
"args": ["claude-folder-handler@0.1.0"]
```

### Bootstrap from git (before v0.1.0 lands on PyPI)

```json
"args": [
  "--from",
  "git+https://github.com/Sdamirsa/claude-folder-handler-SKILL@main",
  "claude-folder-handler"
]
```

### CLI use (no MCP)

```bash
uvx claude-folder-handler setup
uvx claude-folder-handler install-pack llm-extraction
uvx claude-folder-handler audit
uvx claude-folder-handler upgrade --apply
```

---

## What it gives you

A lean baseline (~20 files, all Python with UV inline-deps) plus opt-in packs:

| Pack | What it adds |
|---|---|
| **+pr-flow** | `open-pr`, `rebase-clean` skills; `reviewer` agent |
| **+test-tooling** | `debug-failing-test` skill; `test-writer` agent |
| **+data-science** | `inspect-df`, `clean-data` skills; pandas/notebook rules; dataset-card template |
| **+visualization** | `quick-chart`, `chart-review` skills; plotting style rule |
| **+llm-app** | `anthropic-sdk-bootstrap`, `migrate-model-version` skills; SDK rule; stale-model hook |
| **+llm-extraction** | `extract-structured`, `build-extractor-eval`, `batch-extract` skills; `schema-designer` agent |
| **+monorepo** | per-package CLAUDE.md generator |
| **+security-hardening** | tighter denies, WebFetch allowlist, hooks.lock enforcer, description lint |
| **+telemetry** | invocation logging (local-only JSONL) consumed by `audit` |

Default-checked at first `setup`: `+data-science +visualization +llm-app +llm-extraction +security-hardening +telemetry`.

## What you get per repo

```
<repo>/
├── CLAUDE.md              # ≤40 lines, stack-substituted
├── .mcp.json.example      # template (real .mcp.json is gitignored)
├── .gitignore             # managed block appended
└── .claude/
    ├── README.md          # navigation index
    ├── ROUTER.md          # triggering decision table (SessionStart-injected)
    ├── settings.json      # permissions, hook wiring
    ├── .meta/             # version, hooks.lock, packs.json, protected-branches
    ├── rules/             # path-scoped instructions
    ├── skills/commit/     # the baseline skill
    ├── hooks/             # session-start, deny-secrets, deny-destructive, telemetry
    └── reference/         # on-demand knowledge catalog (INDEX + README)
```

## Documentation

See [`docs/`](docs/):

- [`mcp-setup.md`](docs/mcp-setup.md) — full install / troubleshooting
- [`architecture.md`](docs/architecture.md) — layered design
- [`packs.md`](docs/packs.md) — pack catalog with manifests
- [`triggering-convention.md`](docs/triggering-convention.md) — how descriptions get written
- [`security-model.md`](docs/security-model.md) — what the deny hooks block + why
- [`upgrade-flow.md`](docs/upgrade-flow.md) — managed blocks & three-way merge

## Status

Alpha (v0.1.0). PyPI publication pending; use the git bootstrap until then.

## License

MIT. See [`LICENSE`](LICENSE).
