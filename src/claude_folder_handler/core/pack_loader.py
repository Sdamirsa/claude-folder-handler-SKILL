"""Discover and install opt-in packs bundled inside the package's `data/packs/`.

Each pack directory contains:
  - pack.toml             metadata (name, description, dependencies, defaults, files)
  - router-rows.md        managed-block content for ROUTER.md (skills + reference)
  - settings-overlay.json optional dict merged into .claude/settings.json
  - <content tree>        files copied verbatim under .claude/

The bundled data root is reached via importlib.resources to work both in a
wheel install and editable source checkout.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Iterable

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from claude_folder_handler.core.hooks_lock import write_lock
from claude_folder_handler.core.managed_blocks import (
    MARKDOWN,
    deep_merge_settings,
    render_settings,
    replace_block,
)


# ----- Locating bundled data ---------------------------------------------------


def _data_root() -> Path:
    """Path to the bundled `data/` directory inside the installed package."""
    return Path(resources.files("claude_folder_handler").joinpath("data"))


def _packs_root() -> Path:
    return _data_root() / "packs"


def _template_root() -> Path:
    return _data_root() / "template"


# ----- Pack metadata -----------------------------------------------------------


@dataclass(frozen=True)
class PackMeta:
    name: str
    summary: str
    description: str
    default: bool
    depends_on: tuple[str, ...]
    path: Path


def _load_pack_meta(pack_dir: Path) -> PackMeta:
    toml_path = pack_dir / "pack.toml"
    data: dict = {}
    if toml_path.exists():
        try:
            data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            data = {}
    pack = data.get("pack", {})
    return PackMeta(
        name=pack.get("name", pack_dir.name),
        summary=pack.get("summary", ""),
        description=pack.get("description", ""),
        default=bool(pack.get("default", False)),
        depends_on=tuple(pack.get("depends_on", []) or []),
        path=pack_dir,
    )


def list_packs() -> dict:
    """Return the catalog of bundled packs."""
    root = _packs_root()
    if not root.is_dir():
        return {"ok": True, "packs": []}
    metas: list[PackMeta] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        metas.append(_load_pack_meta(child))
    return {
        "ok": True,
        "packs": [
            {
                "name": m.name,
                "summary": m.summary,
                "default": m.default,
                "depends_on": list(m.depends_on),
                "description": m.description,
            }
            for m in metas
        ],
    }


def default_pack_names() -> list[str]:
    """The LLM-scientist defaults pre-checked at /setup."""
    catalog = list_packs()
    return [p["name"] for p in catalog["packs"] if p["default"]]


# ----- Pack installation -------------------------------------------------------


def _packs_state_path(cwd: Path) -> Path:
    return cwd / ".claude" / ".meta" / "packs.json"


def _load_packs_state(cwd: Path) -> dict:
    p = _packs_state_path(cwd)
    if not p.exists():
        return {"installed": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"installed": []}


def _save_packs_state(cwd: Path, state: dict) -> None:
    p = _packs_state_path(cwd)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iter_pack_files(pack_dir: Path) -> Iterable[tuple[Path, Path]]:
    """Yield (source_path, repo_relative_destination) for every content file in pack_dir.

    Skips pack.toml, router-rows.md, settings-overlay.json (metadata; processed separately).
    Files live in a `content/` subdir to keep meta and content separate.
    """
    content = pack_dir / "content"
    if not content.is_dir():
        return
    for p in sorted(content.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(content)
        yield p, rel


def install_pack(cwd: Path, name: str, dry_run: bool = False) -> dict:
    """Install a single pack into cwd's .claude/.

    Returns {"ok": bool, "name": str, "files_written": [...], "router_block": "...", ...}.
    Refuses if already installed (caller can /upgrade instead).
    """
    cwd = Path(cwd).resolve()
    claude_dir = cwd / ".claude"
    if not claude_dir.is_dir():
        return {"ok": False, "error": f"No .claude/ directory at {cwd}. Run setup first."}

    pack_dir = _packs_root() / name
    if not pack_dir.is_dir():
        return {"ok": False, "error": f"Unknown pack: {name}. See list_packs."}

    state = _load_packs_state(cwd)
    if name in state.get("installed", []):
        return {"ok": False, "error": f"Pack '{name}' is already installed. Use upgrade to refresh."}

    meta = _load_pack_meta(pack_dir)

    # Resolve dependencies (advisory — we just warn)
    missing_deps = [d for d in meta.depends_on if d not in state.get("installed", [])]

    # Pre-flight: conflict check
    planned: list[tuple[Path, Path]] = []  # (source, abs_dest)
    conflicts: list[str] = []
    for src, rel in _iter_pack_files(pack_dir):
        dest = claude_dir / rel
        if dest.exists():
            conflicts.append(str(rel))
        planned.append((src, dest))

    if conflicts and not dry_run:
        return {
            "ok": False,
            "error": "File-level conflicts with existing .claude/ content",
            "conflicts": conflicts,
        }

    files_written: list[str] = []
    if not dry_run:
        for src, dest in planned:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            files_written.append(str(dest.relative_to(cwd)))

        # ROUTER managed block
        router_path = claude_dir / "ROUTER.md"
        rows_path = pack_dir / "router-rows.md"
        if router_path.exists() and rows_path.exists():
            body = rows_path.read_text(encoding="utf-8")
            text = router_path.read_text(encoding="utf-8")
            text = replace_block(text, f"pack-{name}", body, MARKDOWN)
            router_path.write_text(text, encoding="utf-8")

        # settings overlay
        overlay_path = pack_dir / "settings-overlay.json"
        settings_path = claude_dir / "settings.json"
        if overlay_path.exists() and settings_path.exists():
            try:
                overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
                base = json.loads(settings_path.read_text(encoding="utf-8"))
                merged = deep_merge_settings(base, overlay)
                settings_path.write_text(render_settings(merged), encoding="utf-8")
            except json.JSONDecodeError as e:
                return {"ok": False, "error": f"Settings overlay merge failed: {e}"}

        # State + lock
        state.setdefault("installed", []).append(name)
        _save_packs_state(cwd, state)
        write_lock(cwd)

    return {
        "ok": True,
        "name": name,
        "dry_run": dry_run,
        "files_written": files_written,
        "files_planned": [str(d.relative_to(cwd)) for _, d in planned] if dry_run else files_written,
        "missing_deps": missing_deps,
    }


def install_packs(cwd: Path, names: list[str], dry_run: bool = False) -> dict:
    """Install multiple packs in order. Stops on first failure."""
    results: list[dict] = []
    for name in names:
        r = install_pack(cwd, name=name, dry_run=dry_run)
        results.append(r)
        if not r.get("ok"):
            return {"ok": False, "results": results, "failed_at": name}
    return {"ok": True, "results": results}


__all__ = [
    "PackMeta",
    "list_packs",
    "default_pack_names",
    "install_pack",
    "install_packs",
]
