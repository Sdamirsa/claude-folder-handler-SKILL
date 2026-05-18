"""Three-way merge the existing .claude/ against the bundled template.

Strategy:
  - For each file in the template, replace ONLY the content inside
    `<!-- managed:* -->` blocks (or `# managed:*` for hash-comment files).
  - Files that don't exist in the repo are created.
  - Files outside the managed-block universe (e.g., user-edited skills) are
    left untouched.
  - Regenerates hooks.lock at the end.

Dry-run is the default; the caller must explicitly pass dry_run=False.
"""

from __future__ import annotations

import re
from pathlib import Path

from claude_folder_handler import __version__
from claude_folder_handler.core.hooks_lock import write_lock
from claude_folder_handler.core.managed_blocks import (
    HASH,
    MARKDOWN,
    BlockMarker,
    list_blocks,
    replace_block,
)
from claude_folder_handler.core.pack_loader import _template_root
from claude_folder_handler.core.scaffold import _dest_for, _walk_template


MARKER_BY_EXT = {
    ".md": MARKDOWN,
    ".html": MARKDOWN,
    ".tmpl": MARKDOWN,
    ".gitignore": HASH,
}


def _marker_for(path: Path) -> BlockMarker | None:
    if path.suffix == ".tmpl":
        stem_path = Path(path.stem)
        return MARKER_BY_EXT.get(stem_path.suffix, MARKDOWN if stem_path.suffix == "" else None)
    return MARKER_BY_EXT.get(path.suffix)


def upgrade_repo(cwd: Path, dry_run: bool = True) -> dict:
    """Three-way merge against the latest bundled template."""
    cwd = Path(cwd).resolve()
    claude_dir = cwd / ".claude"
    if not claude_dir.is_dir():
        return {
            "ok": False,
            "error": f"No .claude/ at {cwd}. Use setup_claude_folder instead.",
        }

    template_root = _template_root()
    actions: list[dict] = []

    for src in _walk_template(template_root):
        dest = _dest_for(src, template_root, cwd)
        marker = _marker_for(src)

        if not dest.exists():
            # Missing entirely → create on apply.
            actions.append({
                "action": "create",
                "path": str(dest.relative_to(cwd)),
                "marker": "n/a",
            })
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())
            continue

        if marker is None:
            # Binary or no-marker file → skip (user owns it).
            actions.append({
                "action": "skip-unmanaged",
                "path": str(dest.relative_to(cwd)),
            })
            continue

        # Inspect template for managed blocks; copy each block's body into the
        # destination's same-named block.
        template_text = src.read_text(encoding="utf-8")
        block_names = list_blocks(template_text, marker)
        if not block_names:
            actions.append({
                "action": "skip-no-managed-blocks",
                "path": str(dest.relative_to(cwd)),
            })
            continue

        dest_text = dest.read_text(encoding="utf-8")
        changed_blocks: list[str] = []
        for block_name in block_names:
            pat = marker.pattern(block_name)
            m = pat.search(template_text)
            if not m:
                continue
            new_body = m.group("body").strip("\n")
            new_text = replace_block(dest_text, block_name, new_body, marker)
            if new_text != dest_text:
                changed_blocks.append(block_name)
                dest_text = new_text
        if changed_blocks:
            actions.append({
                "action": "update-blocks",
                "path": str(dest.relative_to(cwd)),
                "blocks": changed_blocks,
            })
            if not dry_run:
                dest.write_text(dest_text, encoding="utf-8")

    # Bump version + regenerate hooks.lock on apply.
    if not dry_run:
        version_file = cwd / ".claude" / ".meta" / "version"
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(__version__ + "\n", encoding="utf-8")
        write_lock(cwd)
        actions.append({"action": "write-version", "version": __version__})
        actions.append({"action": "write-hooks-lock"})

    return {
        "ok": True,
        "dry_run": dry_run,
        "actions": actions,
        "summary": {
            "creates": sum(1 for a in actions if a["action"] == "create"),
            "updates": sum(1 for a in actions if a["action"] == "update-blocks"),
            "skipped": sum(1 for a in actions if a["action"].startswith("skip-")),
        },
    }


__all__ = ["upgrade_repo"]
