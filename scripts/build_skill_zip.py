"""Build a Claude.ai-uploadable Skill zip from this package.

Output: dist/claude-folder-handler-skill-<version>.zip

Layout inside the zip follows Anthropic's official skill convention
(see https://github.com/anthropics/skills/tree/main/skills/algorithmic-art) —
exactly **one** SKILL.md at the top of the zip's skill folder, with payload
files nested under that folder:

    claude-folder-handler/
    ├── SKILL.md                          # frontmatter + lean instructions
    └── scripts/
        ├── scaffold.py                   # CLI entry point Claude invokes
        └── claude_folder_handler/
            ├── __init__.py
            ├── core/                     # scaffold + audit + pack loader code
            └── data.zip                  # template/ + packs/ packed as a blob

The `data/` tree contains 13 nested SKILL.md files (one per bundled pack-skill,
plus the baseline `commit` skill). Those are **scaffolded skill bodies for the
end-user's `.claude/skills/` directory** — not skills for Claude.ai's loader.
Claude.ai's validator counts every SKILL.md in the uploaded zip and rejects on
> 1, so we ship `data/` as `data.zip` and let `scaffold.py` extract it once
before importing the package. The validator sees only one SKILL.md (the top-
level one), and the package's existing `_data_root()` keeps working unchanged.

The vendored package excludes the MCP server, CLI, and `__main__` so the
skill ships without the `mcp` runtime dependency.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PKG = ROOT / "src" / "claude_folder_handler"
SRC_DATA = SRC_PKG / "data"
DIST = ROOT / "dist"

SKILL_NAME = "claude-folder-handler"


def _read_version() -> str:
    init = (SRC_PKG / "__init__.py").read_text(encoding="utf-8")
    for line in init.splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("Could not determine __version__")


# Single-line `description` (matches algorithmic-art / docx style — avoids
# YAML literal-block parsing edge cases in strict validators).
SKILL_MD = """---
name: claude-folder-handler
description: Scaffolds a complete `.claude/` configuration directory for the user's coding project (CLAUDE.md, ROUTER.md, settings.json, deterministic deny hooks, baseline skills, path-scoped rules, on-demand reference catalog) and returns it as a downloadable zip the user extracts at their repo root. Detects the user's stack (Python, Node, Rust, Go) from an uploaded pyproject.toml or package.json and picks LLM-scientist-friendly pack defaults (+data-science, +visualization, +llm-app, +llm-extraction, +security-hardening). Use this skill whenever the user says "set up .claude for my project", "scaffold claude code config", "generate a .claude folder", "I want to start using Claude Code in my repo", "create the .claude structure for me", "bootstrap claude for a new project", or asks how to organize a Claude Code configuration — even if they don't use the exact word "scaffold". NOT for editing an EXISTING `.claude/` folder; for that the user should install the `claude-folder-handler` MCP server inside Claude Code. NOT for installing Claude Code itself; this skill only generates the per-project config tree.
---

# claude-folder-handler

Produce a fresh, opinionated `.claude/` directory tree for the user's coding
project, delivered as a downloadable zip they extract at their repo root.

## How this skill works

The deterministic work — running stack detection, copying the template,
installing packs, generating `hooks.lock`, zipping the result — lives in
`scripts/scaffold.py`. You drive it with a single subprocess call. Don't
re-implement the logic inline; the script already handles the edge cases
(dotfile renames, gitignore merging, managed blocks, executable bits, and
one-time extraction of the bundled `data.zip` payload).

## Steps

1. **List the catalog** so you can show the user the pack menu:

   ```bash
   python scripts/scaffold.py --list-packs
   ```

   Returns JSON: `{"packs": [{"name", "summary", "default", "depends_on", "description"}, ...]}`.

2. **Gather inputs from the user:**

   - **Project name** — derive from an uploaded manifest (`pyproject.toml`
     `[project].name`, `package.json` `"name"`, `Cargo.toml` `[package].name`,
     `go.mod` `module`) or ask. Used for the scaffold's `{{project_name}}`
     substitution in CLAUDE.md.
   - **Manifest file (optional)** — if the user uploaded one, pass it via
     `--manifest-file` so stack detection works. Otherwise the scaffold
     produces a generic baseline.
   - **Packs** — show the catalog, propose the default-checked ones (those
     with `"default": true` — typically `data-science`, `visualization`,
     `llm-app`, `llm-extraction`, `security-hardening`), let the user adjust.
   - **Output filename** — default `dot-claude-scaffold.zip`.

3. **Build the scaffold zip:**

   ```bash
   python scripts/scaffold.py \\
     --project-name "<name>" \\
     --manifest-file "<path/to/uploaded-pyproject.toml>" \\
     --packs "data-science,visualization,llm-app,llm-extraction,security-hardening" \\
     --out "/tmp/dot-claude-scaffold.zip"
   ```

   Flags:
   - `--project-name` (required) — substituted into CLAUDE.md
   - `--manifest-file PATH` (optional) — copied into the fake target so
     `detect_stack` picks it up
   - `--manifest-name NAME` (optional) — overrides the destination filename
     (default: source file's basename)
   - `--packs name1,name2,...` (optional) — comma-separated; omit for no
     packs, pass `--defaults` for the LLM-scientist defaults
   - `--out PATH` (required) — output zip path

   The script prints a JSON summary on success:
   `{"ok": true, "out": "...", "files": N, "packs_installed": [...], "stack": {...}}`.

4. **Present the zip** to the user as a downloadable file, plus a short
   summary:
   - Stack detected (language, build/test/lint commands)
   - Packs installed
   - File count
   - How to extract: `cd <repo> && unzip <filename>` (or use the OS unzipper)
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

## Constraints

- Never asks the user to install anything; the bundled `scripts/scaffold.py`
  has everything it needs.
- Never mutates anything outside the sandbox — work in `/tmp`, deliver via
  the output zip.
- If the user wants ongoing scaffold/upgrade/audit tooling inside Claude
  Code (not just this one-shot), point them at the repo README's "Persistent
  install" section: <https://github.com/Sdamirsa/claude-folder-handler-SKILL#install>

## After delivery

Suggest the user:
1. Unzip at their repo root: `cd <repo> && unzip <filename>`
2. Inspect `.claude/README.md` for the navigation map
3. (Optional) install the MCP server for ongoing audit/upgrade — see the project README
"""


SCAFFOLD_PY = '''"""Bundled scaffold runner for the claude-folder-handler Claude.ai skill.

This is the deterministic entry point the skill's SKILL.md invokes. It wraps
the vendored `claude_folder_handler` package so Claude doesn't have to write
`sys.path.insert` boilerplate at every invocation.

The bundled `data/` tree (template + 8 packs) ships as `data.zip` alongside
this file so the outer skill zip contains exactly one `SKILL.md` (the one
Claude.ai validates against). On first run we extract `data.zip` to `data/`
once, then import the package as normal.

Usage:
    # Enumerate available packs (for menu display):
    python scaffold.py --list-packs

    # Build a scaffold zip:
    python scaffold.py \\
        --project-name myrepo \\
        --manifest-file /mnt/user-data/uploads/pyproject.toml \\
        --packs data-science,visualization,security-hardening \\
        --out /tmp/dot-claude-scaffold.zip

    # Use bundled defaults instead of an explicit pack list:
    python scaffold.py --project-name myrepo --defaults --out /tmp/x.zip
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
PKG_ROOT = HERE / "claude_folder_handler"
PKG_DATA = PKG_ROOT / "data"
PKG_DATA_ZIP = PKG_ROOT / "data.zip"


def _ensure_data_extracted() -> None:
    """Extract the bundled data.zip on first run.

    The skill zip ships the data tree as a single inner zip to keep the
    outer zip's SKILL.md count at exactly 1 (Claude.ai's validator counts
    every SKILL.md and rejects on > 1; the bundled `data/` contains 13
    pack-skill SKILL.md files that aren't meant for Claude.ai's loader).
    """
    # Detect a complete extraction by checking for a known sentinel path.
    sentinel = PKG_DATA / "template"
    if sentinel.is_dir():
        return
    if not PKG_DATA_ZIP.is_file():
        # No data.zip available — assume the caller is using an in-place
        # source checkout where data/ already lives next to the code.
        return
    PKG_DATA.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PKG_DATA_ZIP) as z:
        z.extractall(PKG_DATA)


_ensure_data_extracted()
# Make the vendored package importable.
sys.path.insert(0, str(HERE))


def _list_packs() -> int:
    from claude_folder_handler.core.pack_loader import list_packs

    print(json.dumps(list_packs(), indent=2))
    return 0


def _parse_packs(raw: str | None, use_defaults: bool) -> list[str] | None:
    """Resolve the pack selection.

    Returns None when the user wants the loader's defaults (passed through
    to setup_repo as `packs=None`); returns an explicit list otherwise
    (including the empty list for `--packs ""`, which means "no packs").
    """
    if use_defaults:
        return None
    if raw is None:
        return []
    raw = raw.strip()
    if not raw:
        return []
    return [name.strip() for name in raw.split(",") if name.strip()]


def _build(args: argparse.Namespace) -> int:
    from claude_folder_handler.core.scaffold import setup_repo

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / args.project_name
        target.mkdir(parents=True)

        # Copy uploaded manifest in so detect_stack can read it.
        if args.manifest_file:
            mf = Path(args.manifest_file)
            if not mf.is_file():
                print(json.dumps({"ok": False, "error": f"manifest-file not found: {mf}"}))
                return 2
            dest_name = args.manifest_name or mf.name
            (target / dest_name).write_bytes(mf.read_bytes())

        packs = _parse_packs(args.packs, args.defaults)
        result = setup_repo(target, packs=packs, dry_run=False)
        if not result.get("ok"):
            print(json.dumps({"ok": False, "error": result.get("error", "scaffold failed"),
                              "detail": result}))
            return 1

        # Zip the scaffolded contents at the repo root (no leading project-name
        # directory inside the zip, so users `unzip` straight into their repo).
        n_files = 0
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p in sorted(target.rglob("*")):
                if not p.is_file():
                    continue
                z.write(p, arcname=str(p.relative_to(target)))
                n_files += 1

        summary = {
            "ok": True,
            "out": str(out_path),
            "files": n_files,
            "packs_installed": result.get("packs_installed", []),
            "stack": result.get("stack", {}),
            "size_bytes": out_path.stat().st_size,
        }
        print(json.dumps(summary, indent=2))
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scaffold.py",
        description="Build a .claude/ scaffold zip (Claude.ai skill entry point).",
    )
    parser.add_argument(
        "--list-packs", action="store_true",
        help="Print the JSON pack catalog and exit.",
    )
    parser.add_argument("--project-name", help="Project name (substituted into CLAUDE.md).")
    parser.add_argument(
        "--manifest-file",
        help="Path to an uploaded pyproject.toml / package.json / Cargo.toml / go.mod.",
    )
    parser.add_argument(
        "--manifest-name",
        help="Override destination filename for --manifest-file (default: source basename).",
    )
    parser.add_argument(
        "--packs", default=None,
        help="Comma-separated pack names. Omit for no packs; use --defaults for bundled defaults.",
    )
    parser.add_argument(
        "--defaults", action="store_true",
        help="Install the LLM-scientist default packs instead of an explicit list.",
    )
    parser.add_argument("--out", help="Output zip path.")

    args = parser.parse_args(argv)

    if args.list_packs:
        return _list_packs()

    if not args.project_name or not args.out:
        parser.error("--project-name and --out are required (unless using --list-packs).")
    return _build(args)


if __name__ == "__main__":
    sys.exit(main())
'''


# Files / directories to exclude when copying the vendored package code.
# data/ is excluded because we ship it as data.zip (see _build_data_zip).
EXCLUDE_FROM_PKG = {"mcp_server.py", "cli.py", "__main__.py", "__pycache__"}


def _copy_vendored_code(dest_pkg_root: Path) -> int:
    """Copy src/claude_folder_handler/* (CODE ONLY — no data/) into dest.

    Skips CLI + MCP server + cache dirs so the skill ships without the `mcp`
    runtime dependency. Also skips the `data/` tree, which is packed
    separately as data.zip by _build_data_zip.
    """
    n = 0
    for src in SRC_PKG.rglob("*"):
        rel = src.relative_to(SRC_PKG)
        if rel.parts and rel.parts[0] == "data":
            continue
        if any(part in EXCLUDE_FROM_PKG for part in rel.parts):
            continue
        if src.is_dir():
            continue
        target = dest_pkg_root / "claude_folder_handler" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        n += 1
    return n


def _build_data_zip(out_path: Path) -> int:
    """Pack src/claude_folder_handler/data/ into out_path as a single zip.

    Inner zip layout mirrors the on-disk layout (template/, packs/, ...)
    so the package's existing `_data_root()` works without modification
    once scaffold.py extracts it.
    """
    n = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(SRC_DATA.rglob("*")):
            if not p.is_file():
                continue
            if p.name == "__pycache__" or "__pycache__" in p.parts:
                continue
            z.write(p, arcname=str(p.relative_to(SRC_DATA)))
            n += 1
    return n


def main() -> int:
    version = _read_version()
    DIST.mkdir(exist_ok=True)
    out = DIST / f"claude-folder-handler-skill-{version}.zip"
    if out.exists():
        out.unlink()

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / SKILL_NAME
        stage.mkdir()
        (stage / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
        scripts_dir = stage / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "scaffold.py").write_text(SCAFFOLD_PY, encoding="utf-8")
        n_code = _copy_vendored_code(scripts_dir)
        n_data = _build_data_zip(scripts_dir / "claude_folder_handler" / "data.zip")

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            # stage = <tmp>/claude-folder-handler/; we want the zip rooted at
            # claude-folder-handler/, so use stage.parent as the arcname base.
            for p in sorted(stage.rglob("*")):
                if not p.is_file():
                    continue
                z.write(p, arcname=str(p.relative_to(stage.parent)))

    # Quick post-condition: outer zip must contain exactly one SKILL.md.
    with zipfile.ZipFile(out) as z:
        skill_mds = [n for n in z.namelist() if n.endswith("/SKILL.md") or n == "SKILL.md"]
    if len(skill_mds) != 1:
        raise SystemExit(
            f"ERROR: outer skill zip must contain exactly 1 SKILL.md, got {len(skill_mds)}: {skill_mds}"
        )

    size_kb = out.stat().st_size / 1024
    print(f"✓ Wrote {out}")
    print(f"  Skill name:           {SKILL_NAME}")
    print(f"  Version:              {version}")
    print(f"  Vendored code files:  {n_code}")
    print(f"  data.zip files:       {n_data}")
    print(f"  SKILL.md count:       {len(skill_mds)} ({skill_mds[0]})")
    print(f"  Outer zip size:       {size_kb:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
