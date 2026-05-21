# claude-folder-handler

Scaffold, upgrade, and audit `.claude/` folders for any coding repo. Ships as
a **Claude Code MCP server** plus a CLI — install once, use everywhere.

Tuned for LLM-scientist work: data-science, visualization, LLM app dev, and
LLM extraction packs ship in the default install.

---

## Install

Prerequisite: [`uv`](https://docs.astral.sh/uv/getting-started/installation/). One-liner: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

Pick the path that matches what you're trying to do (expand the one you want):

<details>
<summary><b>A. Have Claude do it for you</b> — one line you copy and send to Claude</summary>

<br>

Paste this into Claude Code and hit enter:

> Install the `claude-folder-handler` MCP server by running `claude mcp add claude-folder-handler --scope user -- uvx --from git+https://github.com/Sdamirsa/claude-folder-handler-SKILL claude-folder-handler` in my terminal, then tell me to restart Claude Code.

Claude will run the `claude mcp add` command, which edits `~/.claude/settings.json` for you. Restart Claude Code, then say *"set up .claude here"* in any repo.

> **After v0.1.0 lands on PyPI**, the inner command shortens to `uvx claude-folder-handler@latest` — same effect.

</details>

<details open>
<summary><b>B. Persistent install in Claude Code</b> — recommended for daily use</summary>

<br>

Add this block to `~/.claude/settings.json` (create the file if absent):

```json
{
  "mcpServers": {
    "claude-folder-handler": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Sdamirsa/claude-folder-handler-SKILL",
        "claude-folder-handler"
      ]
    }
  }
}
```

After PyPI publication, this simplifies to:

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

Restart Claude Code. Open any repo, say *"set up .claude here"*. The `setup_claude_folder` tool fires, detects your stack, scaffolds the lean baseline, installs the LLM-scientist pack defaults.

Pin a version: `"args": ["claude-folder-handler@0.1.0"]` (or replace `git+...` with `git+...@v0.1.0`).

</details>

<details>
<summary><b>C. One-shot try</b> — no install, no MCP wiring</summary>

<br>

Run the CLI directly against a repo:

```bash
cd <your-repo>
uvx --from git+https://github.com/Sdamirsa/claude-folder-handler-SKILL claude-folder-handler setup
```

(Post-PyPI: `uvx claude-folder-handler setup`.) Same scaffold result, no Claude Code integration. Good for "let me see what this does" or for CI.

</details>

<details>
<summary><b>D. CLI tool on PATH</b> — power users, scripts</summary>

<br>

Install persistently so the `claude-folder-handler` command is on your PATH:

```bash
uv tool install --from git+https://github.com/Sdamirsa/claude-folder-handler-SKILL claude-folder-handler
claude-folder-handler --version
claude-folder-handler setup
claude-folder-handler install-pack llm-extraction
claude-folder-handler audit
```

(Post-PyPI: `uv tool install claude-folder-handler`.) Upgrade with `uv tool upgrade claude-folder-handler`.

</details>

<details>
<summary><b>E. CI / scripted setup</b> — workflow steps</summary>

<br>

Use the CLI in a workflow step — no Claude session required:

```yaml
- name: Scaffold .claude/
  run: |
    uvx --from git+https://github.com/Sdamirsa/claude-folder-handler-SKILL \
      claude-folder-handler setup --packs data-science llm-extraction security-hardening
    uvx --from git+https://github.com/Sdamirsa/claude-folder-handler-SKILL \
      claude-folder-handler audit
```

</details>

<details>
<summary><b>F. Develop on this repo</b> — contributors</summary>

<br>

```bash
git clone https://github.com/Sdamirsa/claude-folder-handler-SKILL
cd claude-folder-handler-SKILL
uv venv && uv pip install -e ".[dev]"
uv run pytest                                  # 103 tests
uv build                                       # wheel + sdist under dist/
uv run python scripts/build_skill_zip.py       # Claude.ai Skill zip under dist/
```

See [`docs/release.md`](docs/release.md) for cutting a release.

</details>

<details>
<summary><b>G. Claude.ai web/desktop (no Claude Code)</b> — Skill upload</summary>

<br>

If you're using Claude.ai in a browser or desktop app rather than Claude Code, install the **Skill zip** instead:

1. Download `claude-folder-handler-skill-<version>.zip` from the [Releases page](https://github.com/Sdamirsa/claude-folder-handler-SKILL/releases) (or build it locally — see option F).
2. In Claude.ai → **Settings → Skills → Add skill**, upload the zip.
3. In any conversation, say *"set up .claude for my project"*.

The skill runs in Claude.ai's sandbox, asks about your stack and pack preferences (or reads an uploaded `pyproject.toml` / `package.json`), scaffolds a `.claude/` directory tree, and returns a zip you extract at your repo root.

For ongoing audit/upgrade tooling, use the MCP install instead (paths A or B above).

</details>

> ⚠ **MCP server doesn't show up after install?** See [`docs/mcp-setup.md`](docs/mcp-setup.md) for troubleshooting (uvx PATH, JSON validity, `uvx --refresh` to bust stale caches).

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
- [`roadmap.md`](docs/roadmap.md) — planned features grouped by intention

## Status

Alpha (v0.1.0). PyPI publication pending; use the git bootstrap until then.

## License

MIT. See [`LICENSE`](LICENSE).
