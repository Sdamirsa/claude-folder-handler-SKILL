"""Scaffold the lean baseline .claude/ tree (plus selected packs) into a repo.

Template tree lives at `data/template/`. Files ending in `.tmpl` are rendered
with `{{name}}` placeholders substituted from the stack detection. Non-tmpl
files are copied verbatim.

Special filename remappings (avoids package-data tooling treating dotfiles
specially): the template uses underscored siblings of dotfiles, renamed at
write time.
"""

from __future__ import annotations

import json
import shutil
from importlib import resources
from pathlib import Path

from claude_folder_handler import __version__
from claude_folder_handler.core.detect_stack import detect_stack
from claude_folder_handler.core.hooks_lock import write_lock
from claude_folder_handler.core.managed_blocks import HASH, replace_block
from claude_folder_handler.core.pack_loader import (
    _template_root,
    default_pack_names,
    install_packs,
)


# Template-name → repo-relative-name remap (avoids dotfile tooling pitfalls).
NAME_REMAP = {
    "_mcp.json.example": ".mcp.json.example",
    "_gitignore.snippet": ".gitignore.snippet",
}

# Inside the template, the `.claude/` subtree is stored as `claude/` to avoid
# packaging issues with dotfiles. At scaffold time we relocate it.
TEMPLATE_DIR_REMAP = {
    "claude": ".claude",
    "meta": ".meta",  # under template/claude/meta → .claude/.meta
}


GITIGNORE_BLOCK_NAME = "claude-folder-handler"


def _render(text: str, ctx: dict[str, str]) -> str:
    """Lightweight `{{name}}` substitution."""
    out = text
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def _walk_template(src: Path) -> list[Path]:
    """All files under src, recursive."""
    return sorted(p for p in src.rglob("*") if p.is_file())


def _dest_for(src_file: Path, template_root: Path, cwd: Path) -> Path:
    """Map a template-tree source path to its repo-relative destination."""
    rel = src_file.relative_to(template_root)
    parts: list[str] = []
    for part in rel.parts:
        if part in NAME_REMAP:
            parts.append(NAME_REMAP[part])
        elif part in TEMPLATE_DIR_REMAP:
            parts.append(TEMPLATE_DIR_REMAP[part])
        else:
            parts.append(part)
    out = Path(*parts)
    # Strip trailing `.tmpl` from filename (content is rendered)
    if out.name.endswith(".tmpl"):
        out = out.with_name(out.name[: -len(".tmpl")])
    return cwd / out


def _build_context(cwd: Path) -> dict[str, str]:
    stack = detect_stack(cwd)
    languages = stack["languages"] or ["unknown"]
    return {
        "project_name": str(stack["project_name"]),
        "language": ", ".join(languages),  # type: ignore[arg-type]
        "build": str(stack["build"]),
        "test": str(stack["test"]),
        "lint": str(stack["lint"]),
        "version": __version__,
    }


def setup_repo(
    cwd: Path,
    packs: list[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """Scaffold the baseline + selected packs into cwd.

    If `.claude/` already exists, refuses and points at /upgrade.
    """
    cwd = Path(cwd).resolve()
    if (cwd / ".claude").exists():
        return {
            "ok": False,
            "error": f".claude/ already exists in {cwd}. Use upgrade_claude_folder instead.",
        }

    template_root = _template_root()
    if not template_root.is_dir():
        return {
            "ok": False,
            "error": f"Bundled template not found at {template_root}. Reinstall the package.",
        }

    ctx = _build_context(cwd)
    plan: list[tuple[Path, Path, bool]] = []  # (src, dest, is_tmpl)
    for src in _walk_template(template_root):
        dest = _dest_for(src, template_root, cwd)
        is_tmpl = src.name.endswith(".tmpl")
        plan.append((src, dest, is_tmpl))

    files_written: list[str] = []

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "stack": ctx,
            "packs_planned": packs if packs is not None else default_pack_names(),
            "files_planned": [str(d.relative_to(cwd)) for _, d, _ in plan],
        }

    # Write template files.
    for src, dest, is_tmpl in plan:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if is_tmpl:
            try:
                text = src.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                shutil.copy2(src, dest)
                files_written.append(str(dest.relative_to(cwd)))
                continue
            dest.write_text(_render(text, ctx), encoding="utf-8")
        else:
            shutil.copy2(src, dest)
        files_written.append(str(dest.relative_to(cwd)))

    # Move .gitignore snippet into the actual .gitignore (managed block).
    _apply_gitignore_snippet(cwd)

    # Write meta/version (canonical location).
    version_file = cwd / ".claude" / ".meta" / "version"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(__version__ + "\n", encoding="utf-8")
    if str(version_file.relative_to(cwd)) not in files_written:
        files_written.append(str(version_file.relative_to(cwd)))

    # Write initial packs.json (empty installed list).
    packs_state = cwd / ".claude" / ".meta" / "packs.json"
    packs_state.write_text(json.dumps({"installed": []}, indent=2) + "\n", encoding="utf-8")

    # Mark template hooks executable.
    hooks_dir = cwd / ".claude" / "hooks"
    if hooks_dir.is_dir():
        for hook in hooks_dir.glob("*.py"):
            hook.chmod(0o755)

    # Generate the initial hooks.lock.
    write_lock(cwd)
    lock_rel = ".claude/.meta/hooks.lock"
    if lock_rel not in files_written:
        files_written.append(lock_rel)

    # Install requested packs (or LLM-scientist defaults).
    pack_names = packs if packs is not None else default_pack_names()
    pack_result = install_packs(cwd, pack_names, dry_run=False) if pack_names else {"ok": True, "results": []}

    return {
        "ok": pack_result.get("ok", True),
        "dry_run": False,
        "stack": ctx,
        "packs_installed": pack_names if pack_result.get("ok", True) else [],
        "pack_result": pack_result,
        "files_written": files_written,
        "next_steps": [
            "Open Claude in this repo and say \"commit this\" to try the baseline skill.",
            "Run `audit_claude_folder` to verify the install.",
            "Add `.claude/settings.local.json` to your personal overrides if needed.",
        ],
    }


def _apply_gitignore_snippet(cwd: Path) -> None:
    """Append the gitignore snippet inside a managed block in `.gitignore`."""
    snippet_path = cwd / ".gitignore.snippet"
    if not snippet_path.exists():
        return
    snippet = snippet_path.read_text(encoding="utf-8").strip()
    snippet_path.unlink()

    gitignore = cwd / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    new = replace_block(existing, GITIGNORE_BLOCK_NAME, snippet, HASH)
    if not new.endswith("\n"):
        new += "\n"
    gitignore.write_text(new, encoding="utf-8")


__all__ = ["setup_repo"]
