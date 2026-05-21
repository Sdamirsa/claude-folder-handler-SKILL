"""Build a Claude.ai-uploadable Skill zip from this package.

Output: dist/claude-folder-handler-skill-<version>.zip
(download-artifact filename — the inner skill folder is `your-folder-handler/`
because Claude.ai's name validator reserves the word "claude".)

Claude.ai's uploader enforces FOUR constraints on skill zips:

  1. Exactly ONE `SKILL.md` (the skill body it loads).
  2. NO nested zip files inside the archive.
  3. The frontmatter `name:` MUST NOT contain the reserved word "claude".
  4. The frontmatter `description:` MUST be ≤ 1024 characters.

The bundled `data/` tree contains 13 nested `SKILL.md` files — the baseline
`commit` skill plus every pack-skill body — meant for the END USER's
`.claude/skills/` directory after they run the scaffold, NOT for Claude.ai's
loader. To satisfy rules #1 and #2 simultaneously we:

  - Ship `data/` as LOOSE files (no nested zip)
  - RENAME every `data/.../SKILL.md` to `data/.../_skill_body.md` at build
    time so only the legitimate top-level `SKILL.md` matches the validator's
    SKILL.md filter
  - Have `scripts/scaffold.py` rename them back to `SKILL.md` on disk on
    first run, before importing the `claude_folder_handler` package

Layout (matches https://github.com/anthropics/skills/tree/main/skills/algorithmic-art):

    your-folder-handler/
    ├── SKILL.md                          # the only SKILL.md in the outer zip
    └── scripts/
        ├── scaffold.py                   # CLI entry — renames + imports
        └── claude_folder_handler/        # vendored (no MCP/CLI deps)
            ├── __init__.py
            ├── core/                     # scaffold + audit + pack loader
            └── data/
                ├── template/.../skills/commit/_skill_body.md   ← was SKILL.md
                ├── packs/.../skills/X/_skill_body.md           ← was SKILL.md
                └── ...                                          (all other files as-is)
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PKG = ROOT / "src" / "claude_folder_handler"
DIST = ROOT / "dist"

# Identifier the SKILL.md frontmatter declares + the top-level folder name
# inside the uploaded zip. Cannot contain the reserved word "claude" per
# Claude.ai's skill name validator. The project-level name (Python package,
# GitHub repo, MCP server) is still `claude-folder-handler` — this string
# only governs the Claude.ai-uploaded skill's identity.
SKILL_NAME = "your-folder-handler"

# Download artifact filename. Kept tied to the project name (not SKILL_NAME)
# so the GitHub Release glob `dist/claude-folder-handler-skill-*.zip` and the
# README's release-artifact references stay stable across the rename.
ZIP_FILENAME = "claude-folder-handler-skill"

# Filename alias used to hide bundled SKILL.md files from Claude.ai's
# "exactly one SKILL.md" validator. The runtime scaffold.py renames these
# back to SKILL.md before importing the package.
SKILL_MD_ALIAS = "_skill_body.md"

# Hard limit Claude.ai enforces on the SKILL.md frontmatter `description:`.
DESCRIPTION_MAX_CHARS = 1024


def _read_version() -> str:
    init = (SRC_PKG / "__init__.py").read_text(encoding="utf-8")
    for line in init.splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("Could not determine __version__")


SKILL_MD = """---
name: your-folder-handler
description: Scaffolds a complete `.claude/` configuration directory for the user's coding project (CLAUDE.md, ROUTER.md, settings.json, deterministic deny hooks, baseline skills, path-scoped rules) and returns it as a downloadable zip the user extracts at their repo root. Detects the stack (Python, Node, Rust, Go) from an uploaded pyproject.toml or package.json and picks LLM-scientist defaults (data-science, visualization, llm-app, llm-extraction, security-hardening). Use whenever the user says "set up .claude for my project", "scaffold claude code config", "generate a .claude folder", "I want to start using Claude Code in my repo", "create the .claude structure for me", or asks how to organize a Claude Code configuration — even without the word "scaffold". NOT for editing an EXISTING `.claude/` folder; use the `claude-folder-handler` MCP server inside Claude Code for that. NOT for installing Claude Code itself; this skill only generates the per-project config tree.
---

# your-folder-handler

Produce a fresh, opinionated `.claude/` directory tree for the user's coding
project, delivered as a downloadable zip they extract at their repo root.

## How this skill works

The deterministic work — running stack detection, copying the template,
installing packs, generating `hooks.lock`, zipping the result — lives in
`scripts/scaffold.py`. You drive it with a single subprocess call. Don't
re-implement the logic inline; the script already handles the edge cases
(dotfile renames, gitignore merging, managed blocks, executable bits, and
the one-time restoration of bundled `SKILL.md` filenames from their
`_skill_body.md` aliases).

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

The bundled `data/` tree ships with every `SKILL.md` renamed to
`_skill_body.md` so the outer zip satisfies Claude.ai's TWO upload rules
simultaneously: (1) exactly one SKILL.md per upload, (2) no nested zip
files. On first run we rename `_skill_body.md` back to `SKILL.md` on disk,
then import the package as normal.

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
SKILL_MD_ALIAS = "_skill_body.md"
SKILL_MD_REAL = "SKILL.md"
RESTORED_SENTINEL = PKG_DATA / ".skill_md_restored"


def _restore_skill_md_filenames() -> None:
    """Rename `_skill_body.md` -> `SKILL.md` throughout the bundled data tree.

    The skill zip ships SKILL.md files under an alias so Claude.ai's
    "exactly one SKILL.md per zip" validator passes (the bundled `data/`
    tree contains 13 SKILL.md files that aren't meant for Claude.ai's
    loader). After one-time restoration, the data tree on disk matches the
    MCP install layout exactly, and the package's `_data_root()` /
    `_template_root()` / `_packs_root()` keep working unchanged.

    Idempotent: a sentinel file ensures we only do the walk once per
    extracted skill directory.
    """
    if not PKG_DATA.is_dir():
        return
    if RESTORED_SENTINEL.exists():
        return
    for body in PKG_DATA.rglob(SKILL_MD_ALIAS):
        target = body.with_name(SKILL_MD_REAL)
        if not target.exists():
            body.rename(target)
    RESTORED_SENTINEL.touch()


_restore_skill_md_filenames()
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


# Files / directories to skip when copying the vendored package.
EXCLUDE_FROM_PKG = {"mcp_server.py", "cli.py", "__main__.py", "__pycache__"}


def _copy_vendored_pkg(dest_pkg_root: Path) -> tuple[int, int]:
    """Copy src/claude_folder_handler into dest, with two transformations:

    1. Skip CLI + MCP server + cache dirs (so the skill ships without the
       `mcp` runtime dependency).
    2. Rename every `SKILL.md` to `_skill_body.md` so the outer zip has only
       one SKILL.md (the top-level one) — Claude.ai's validator otherwise
       rejects > 1 SKILL.md per upload.

    Returns (total_files_copied, n_renamed_skill_md).
    """
    n_files = 0
    n_renamed = 0
    for src in SRC_PKG.rglob("*"):
        rel = src.relative_to(SRC_PKG)
        if any(part in EXCLUDE_FROM_PKG for part in rel.parts):
            continue
        if src.is_dir():
            continue
        # Apply the SKILL.md alias rename (filename-only; the directory
        # structure is preserved so the parent `skills/<name>/` folder still
        # identifies the skill).
        if src.name == "SKILL.md":
            out_rel = rel.with_name(SKILL_MD_ALIAS)
            n_renamed += 1
        else:
            out_rel = rel
        target = dest_pkg_root / "claude_folder_handler" / out_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        n_files += 1
    return n_files, n_renamed


def _post_build_assertions(out: Path) -> tuple[int, int, int]:
    """Verify the produced zip satisfies all four Claude.ai upload rules.

    Raises SystemExit on any violation. Returns
    (skill_md_count, nested_zip_count, description_chars).
    """
    import re

    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        body = z.read(f"{SKILL_NAME}/SKILL.md").decode("utf-8")

    # Rule 1: exactly one SKILL.md
    skill_mds = [n for n in names if n.endswith("/SKILL.md") or n == "SKILL.md"]
    if len(skill_mds) != 1:
        raise SystemExit(
            f"ERROR: outer skill zip must contain exactly 1 SKILL.md, "
            f"got {len(skill_mds)}: {skill_mds}"
        )

    # Rule 2: no nested .zip
    nested_zips = [n for n in names if n.lower().endswith(".zip")]
    if nested_zips:
        raise SystemExit(
            f"ERROR: outer skill zip must not contain nested .zip files, got: {nested_zips}"
        )

    # Parse frontmatter for rules 3 + 4.
    if not body.startswith("---\n"):
        raise SystemExit("ERROR: SKILL.md must start with YAML frontmatter")
    end = body.find("\n---\n", 4)
    if end < 0:
        raise SystemExit("ERROR: SKILL.md frontmatter must be closed with '---'")
    fm = body[4:end]

    # Rule 3: name must not contain reserved word "claude"
    name_m = re.search(r"^name:\s*(\S.*?)\s*$", fm, re.MULTILINE)
    if not name_m:
        raise SystemExit("ERROR: SKILL.md frontmatter missing `name:` field")
    skill_name = name_m.group(1).strip()
    if "claude" in skill_name.lower():
        raise SystemExit(
            f"ERROR: SKILL.md `name:` contains reserved word 'claude': {skill_name!r}"
        )

    # Rule 4: description ≤ 1024 chars (inline single-line value)
    desc_m = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
    if not desc_m:
        raise SystemExit("ERROR: SKILL.md frontmatter missing `description:` field")
    desc = desc_m.group(1).strip()
    if len(desc) > DESCRIPTION_MAX_CHARS:
        raise SystemExit(
            f"ERROR: SKILL.md description is {len(desc)} chars (> {DESCRIPTION_MAX_CHARS} max). "
            "Trim trigger phrases or NOT-for clauses."
        )

    return len(skill_mds), len(nested_zips), len(desc)


def main() -> int:
    version = _read_version()
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{ZIP_FILENAME}-{version}.zip"
    if out.exists():
        out.unlink()

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / SKILL_NAME
        stage.mkdir()
        (stage / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
        scripts_dir = stage / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "scaffold.py").write_text(SCAFFOLD_PY, encoding="utf-8")
        n_files, n_renamed = _copy_vendored_pkg(scripts_dir)

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p in sorted(stage.rglob("*")):
                if not p.is_file():
                    continue
                z.write(p, arcname=str(p.relative_to(stage.parent)))

    skill_md_count, nested_zip_count, desc_chars = _post_build_assertions(out)

    size_kb = out.stat().st_size / 1024
    print(f"✓ Wrote {out}")
    print(f"  Skill name (frontmatter): {SKILL_NAME}")
    print(f"  Version:                  {version}")
    print(f"  Vendored pkg files:       {n_files}")
    print(f"  SKILL.md renamed:         {n_renamed} (to {SKILL_MD_ALIAS})")
    print(f"  SKILL.md in outer zip:    {skill_md_count} (must be 1)")
    print(f"  Nested .zip in outer:     {nested_zip_count} (must be 0)")
    print(f"  description chars:        {desc_chars} / {DESCRIPTION_MAX_CHARS}")
    print(f"  Outer zip size:           {size_kb:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
