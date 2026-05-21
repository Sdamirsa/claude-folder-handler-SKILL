"""Build a Claude.ai-uploadable Skill zip from this package.

Output: dist/claude-folder-handler-skill-<version>.zip

Contents:
  SKILL.md                                # frontmatter + workflow instructions
  README.md                               # for humans who unzip and peek
  pkg/claude_folder_handler/
    __init__.py
    core/*                                # the scaffold + audit + upgrade logic
    data/template/*                       # baseline template
    data/packs/*                          # all 8 packs

NOT included: cli.py, mcp_server.py, __main__.py (the skill drives via
direct imports — no MCP, no argparse needed in the Claude.ai sandbox).
This also lets the skill ship without the `mcp` dependency.
"""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PKG = ROOT / "src" / "claude_folder_handler"
DIST = ROOT / "dist"

# Read version from the package without importing it (avoids needing the
# package on the path).
def _read_version() -> str:
    init = (SRC_PKG / "__init__.py").read_text(encoding="utf-8")
    for line in init.splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("Could not determine __version__")


SKILL_MD = """---
name: claude-folder-handler
description: |
  Scaffolds a complete `.claude/` configuration directory for the user's coding project (CLAUDE.md, ROUTER.md, settings.json, deterministic deny hooks, baseline skills, path-scoped rules, on-demand reference catalog) bundled as a downloadable zip. Detects the user's stack (Python, Node, Rust, Go) from an uploaded pyproject.toml or package.json and picks LLM-scientist-friendly defaults (+data-science, +visualization, +llm-app, +llm-extraction, +security-hardening). Returns a zip the user can extract at their repo root. Use when the user says "set up .claude for my project", "scaffold claude code config", "generate a .claude folder", "I want to start using Claude Code in my repo", "create the .claude structure for me", "bootstrap claude for a new project", or asks how to organize a Claude Code configuration. NOT for editing an EXISTING `.claude/` folder — for that the user should install the `claude-folder-handler` MCP server inside Claude Code. NOT for installing Claude Code itself; this skill only generates the per-project config tree.
---

# claude-folder-handler

This skill produces a fresh, opinionated `.claude/` directory for the user's
coding project, as a downloadable zip.

## What you (Claude) do when invoked

1. **Locate the bundled package.** The skill ships its scaffold logic at
   `pkg/claude_folder_handler/` relative to this SKILL.md. Resolve the
   absolute path to that directory (call it `PKG_PATH`).

2. **Gather inputs from the user.** You need three things:
   - **Stack**: derive from an uploaded `pyproject.toml`, `package.json`,
     `Cargo.toml`, `go.mod`, or by asking. Pick a project name from the
     manifest or ask.
   - **Packs**: present the catalog (`list_packs()`) and propose the
     LLM-scientist defaults (`+data-science`, `+visualization`, `+llm-app`,
     `+llm-extraction`, `+security-hardening`). Let the user adjust.
   - **Output filename**: default `dot-claude-scaffold.zip`.

3. **Run the scaffold in a Python sandbox:**

   ```python
   import sys, os, shutil, tempfile, zipfile
   from pathlib import Path

   sys.path.insert(0, "<PKG_PATH parent>")  # so `import claude_folder_handler` works
   from claude_folder_handler.core.scaffold import setup_repo
   from claude_folder_handler.core.pack_loader import list_packs

   # Build a fake "target repo" with the user's manifest so detect_stack works.
   target = Path(tempfile.mkdtemp()) / "<project_name>"
   target.mkdir(parents=True)
   # If the user uploaded a manifest, copy it in:
   # (target / "pyproject.toml").write_text(<uploaded content>)

   result = setup_repo(
       target,
       packs=[<selected pack names>],  # e.g. ["data-science", "llm-extraction", ...]
       dry_run=False,
   )
   assert result["ok"], result

   # Zip the .claude/ folder + CLAUDE.md + .mcp.json.example + .gitignore.
   out_zip = Path(tempfile.mkdtemp()) / "<output_filename>"
   with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
       for p in target.rglob("*"):
           if p.is_file():
               z.write(p, arcname=p.relative_to(target))
   ```

4. **Present the zip to the user** as a downloadable file along with a
   short summary:
   - Stack detected
   - Packs installed
   - File count
   - How to extract: `cd <repo>; unzip <filename>` (or use the OS unzipper)
   - Suggestion: open the repo in Claude Code and say "audit my .claude folder"
     to verify everything's in place.

## What the scaffold produces

A lean baseline plus the chosen packs:

| Path | What it is |
|---|---|
| `CLAUDE.md` | ≤40 lines, stack-substituted always-loaded context |
| `.mcp.json.example` | Template (real `.mcp.json` is gitignored) |
| `.gitignore` (managed block) | Adds `.claude/settings.local.json`, `.mcp.json`, etc. |
| `.claude/README.md` | Navigation index |
| `.claude/ROUTER.md` | Triggering decision table (SessionStart-injected) |
| `.claude/settings.json` | Permissions, hook wiring |
| `.claude/.meta/{version,hooks.lock,packs.json,protected-branches.json}` | Metadata |
| `.claude/rules/00-global.md` | Always-loaded conventions |
| `.claude/skills/commit/SKILL.md` | The baseline workflow |
| `.claude/hooks/{00,10,20,90}-*.py` | SessionStart inject + deny-secrets + deny-destructive + telemetry |
| `.claude/hooks/lib/*` | Shared helpers (payload, paths, bash_parse) |
| `.claude/reference/{INDEX,README}.md` | On-demand reference catalog |

Plus, per selected pack: skills, agents, rules, hooks, reference materials.

## Available packs

Call `list_packs()` from the bundled package to enumerate. The eight shipping
packs:

- `+pr-flow`              — `open-pr`, `rebase-clean` skills; `reviewer` agent
- `+test-tooling`         — `debug-failing-test` skill; `test-writer` agent
- `+data-science` ★       — `inspect-df`, `clean-data`; `data-explorer` agent; pandas rule
- `+visualization` ★      — `quick-chart`, `chart-review`; plotting rule
- `+llm-app` ★            — `anthropic-sdk-bootstrap`, `migrate-model-version`; sdk rule
- `+llm-extraction` ★     — `extract-structured`, `build-extractor-eval`, `batch-extract`; `schema-designer` agent
- `+monorepo`             — per-package rule for apps/** and packages/**
- `+security-hardening` ★ — hooks.lock SessionStart verifier; tightened denies

★ = default-checked if the user accepts defaults.

## Constraints

- Never asks the user to install anything. Everything runs in the sandbox
  using the bundled package source.
- Never mutates anything outside the sandbox.
- The output zip is the deliverable; the user extracts it at their repo root.
- If the user wants ongoing scaffold/upgrade/audit tooling in Claude Code
  itself (not just this one-shot), point them at the README's "Persistent
  install" section: <https://github.com/Sdamirsa/claude-folder-handler-SKILL#install>

## After delivery

Suggest the user:
1. Unzip at their repo root: `cd <repo> && unzip <filename>`
2. Inspect `.claude/README.md` for the navigation map
3. (Optional) install the MCP server for ongoing audit/upgrade: see the project README
"""


SKILL_README = """# claude-folder-handler — Claude.ai Skill

This zip is an uploadable Skill for Claude.ai (web/desktop). After uploading
via **Settings → Skills → Add skill**, ask Claude:

> *"set up .claude for my project"*

The skill will gather your stack + pack preferences, scaffold a fresh
`.claude/` directory tree (CLAUDE.md, ROUTER.md, settings.json, deterministic
deny hooks, baseline skills, path-scoped rules, on-demand reference catalog),
and return a downloadable zip you extract at your repo root.

## Contents

- `SKILL.md` — the skill body (instructions Claude follows)
- `pkg/claude_folder_handler/` — the scaffold logic and bundled template + 8 packs
- `README.md` — this file

## For Claude Code users

If you're already on Claude Code, prefer the MCP install — it gives ongoing
`setup`, `install-pack`, `audit`, and `upgrade` tools, not just one-shot
scaffolding. See the project README for the one-line install.

## License

MIT. See https://github.com/Sdamirsa/claude-folder-handler-SKILL
"""


# Files / directories to exclude from the bundled pkg (we only ship the
# functions the skill needs at runtime, not the MCP server / CLI).
EXCLUDE_FROM_PKG = {"mcp_server.py", "cli.py", "__main__.py", "__pycache__"}


def _copy_pkg(dest: Path) -> int:
    """Copy src/claude_folder_handler into dest, skipping CLI + MCP server."""
    n = 0
    for src in SRC_PKG.rglob("*"):
        if any(part in EXCLUDE_FROM_PKG for part in src.relative_to(SRC_PKG).parts):
            continue
        if src.is_dir():
            continue
        rel = src.relative_to(SRC_PKG)
        target = dest / "claude_folder_handler" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        n += 1
    return n


def main() -> int:
    version = _read_version()
    DIST.mkdir(exist_ok=True)
    out = DIST / f"claude-folder-handler-skill-{version}.zip"

    # Build under a temp staging dir, then zip.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "skill"
        stage.mkdir()
        (stage / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
        (stage / "README.md").write_text(SKILL_README, encoding="utf-8")
        n = _copy_pkg(stage / "pkg")

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p in stage.rglob("*"):
                if p.is_file():
                    arc = p.relative_to(stage)
                    z.write(p, arcname=str(arc))

    size_kb = out.stat().st_size / 1024
    print(f"✓ Wrote {out}")
    print(f"  Version: {version}")
    print(f"  Bundled pkg files: {n}")
    print(f"  Zip size: {size_kb:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
