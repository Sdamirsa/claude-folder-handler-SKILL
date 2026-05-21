# claude-folder-handler

Scaffold, upgrade, and audit `.claude/` folders for any coding repo. Ships as
a **Claude Code MCP server** plus a CLI — install once, use everywhere.

Tuned for LLM-scientist work: data-science, visualization, LLM app dev, and
LLM extraction packs ship in the default install.

---

## Install

Pick the audience that matches you (expand the one you want):

<details>
<summary><b>1. For Claude.ai (web / desktop)</b> — drag-and-drop a zip, no terminal, no install</summary>

<br>

If you use Claude in a browser or the macOS/Windows desktop app (not the Claude Code CLI), this is the simplest path. You upload one zip file as a **Skill**, then ask Claude in a chat to scaffold `.claude/` for your project. Claude hands you back another zip you extract at your repo root. **No terminal, no Python, no install commands.**

> **What's a `.claude/` folder, in plain English?** A small directory you put in your code project that tells Claude how to behave there — what conventions to follow, what files to avoid, what skills to invoke for "commit this" or "debug this failing test", what to deny outright (like `rm -rf` or reading `.env`). The scaffold gives you a sensible default tree with security hooks, baseline skills, and routing tuned for LLM work.

**You'll need**

- A Claude.ai account (any plan — free, Pro, or Team)
- A code project on your computer (any language; a `pyproject.toml` or `package.json` is helpful but not required)

**Step 1 — Download the Skill zip**

Go to the [latest release](https://github.com/Sdamirsa/claude-folder-handler-SKILL/releases/latest) and download `claude-folder-handler-skill-<version>.zip`. **Don't unzip it** — Claude.ai wants the zip as-is.

**Step 2 — Upload it to Claude.ai as a Skill**

1. Open [claude.ai](https://claude.ai) in a browser, or launch the desktop app
2. Go to **Settings → Capabilities → Skills** *(if you don't see "Skills" right away, check Anthropic's [custom-skills guide](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills) — the location can move)*
3. Click **Add skill** (or **Upload skill**) and pick the zip you downloaded
4. You should see `your-folder-handler` appear in your Skills list (the Claude.ai-uploaded skill is named `your-folder-handler` because Claude.ai reserves the word "claude" in skill names; the Python package and MCP server keep the `claude-folder-handler` name)

**Step 3 — Use it in a chat**

Start a new conversation and say something like:

> *Set up .claude for my project*

or:

> *I want to start using Claude Code on my repo — can you scaffold the .claude folder for me?*

Tip: drag your `pyproject.toml` or `package.json` into the chat **before** asking, so Claude can detect your stack automatically.

Claude will:

1. Ask which **packs** you want (data-science, visualization, LLM extraction, security hardening, etc.). If you're not sure, say *"use the defaults"*.
2. Ask for a **project name** (or read it from the manifest you uploaded)
3. Produce a downloadable zip named `dot-claude-scaffold.zip` (or whatever name you asked for)

**Step 4 — Drop the result into your repo**

1. Download the `dot-claude-scaffold.zip` Claude gave you
2. Move it into your project folder
3. Extract it:
   - macOS / Linux: `unzip dot-claude-scaffold.zip`
   - Windows: right-click → **Extract All**
4. You'll now have a `.claude/` directory plus a `CLAUDE.md` file at your repo root

**Step 5 — Start using the scaffold**

The `.claude/` folder only *does* something when Claude reads it — which happens in Claude Code. If you don't have Claude Code yet, install it from the [official getting-started guide](https://docs.claude.com/en/docs/claude-code/getting-started) (a few seconds), open your repo, and you're done — Claude Code picks up the scaffold automatically.

**FAQ**

- *"Claude asks which packs but I don't recognize the names."* Say *"use the defaults"*. You'll get data-science, visualization, llm-app, llm-extraction, and security-hardening — a solid starting set.
- *"How do I upgrade later?"* Download the latest zip from the [Releases page](https://github.com/Sdamirsa/claude-folder-handler-SKILL/releases), re-upload as a Skill (it replaces the previous version), then re-run the skill in a new chat to regenerate the scaffold.
- *"What's the difference between this and the MCP install (option 2 below)?"* This is **one-shot** scaffolding via drag-and-drop. The MCP install gives you **ongoing** tools — `audit`, `upgrade`, `install-pack` — that Claude Code can call as actual MCP tool calls throughout the life of your project. If you don't use Claude Code, the Skill is all you need.
- *"I changed my mind and want the more powerful technical install."* No problem — see option 2 below. The Skill and the MCP install don't conflict; you can have both.

</details>

<details open>
<summary><b>2. For Claude Code (MCP)</b> — terminal install; full ongoing toolkit (audit, upgrade, install-pack, CI, parallel sub-agent flows)</summary>

<br>

For technical users running [Claude Code](https://docs.claude.com/en/docs/claude-code) in a terminal. Installs an MCP server (and optional CLI) so Claude can call `setup_claude_folder`, `install_pack`, `audit_claude_folder`, `upgrade_claude_folder`, `approve_hooks`, and `list_packs` as real MCP tools — **over the lifetime of your project**, not just at scaffold time. Also unlocks Claude Code's richer execution environment: parallel sub-agents, background bash commands, hook integration, file-system tools.

Prerequisite: [`uv`](https://docs.astral.sh/uv/getting-started/installation/). One-liner: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

Pick the install variant that matches what you're trying to do (expand the one you want):

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
uv run pytest                                  # 121 tests
uv build                                       # wheel + sdist under dist/
uv run python scripts/build_skill_zip.py       # Claude.ai Skill zip under dist/
```

See [`docs/release.md`](docs/release.md) for cutting a release.

</details>

> ⚠ **MCP server doesn't show up after install?** See [`docs/mcp-setup.md`](docs/mcp-setup.md) for troubleshooting (uvx PATH, JSON validity, `uvx --refresh` to bust stale caches).

</details>

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
