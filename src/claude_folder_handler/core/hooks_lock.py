"""Manage `.claude/.meta/hooks.lock` — a sha256-per-hook-script integrity record.

The +security-hardening pack's `05-verify-hooks-lock.py` runs at SessionStart
before any other hook, refusing to chain hooks when the lock and the on-disk
content disagree. This module generates and verifies that lock.

Lock format (deterministic JSON, sorted keys):
    {
      "version": 1,
      "files": {
        "00-session-start.py": "sha256:abc...",
        "10-pre-deny-secrets.py": "sha256:def..."
      }
    }
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


LOCK_REL = Path(".claude/.meta/hooks.lock")
HOOKS_REL = Path(".claude/hooks")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _iter_hook_files(hooks_dir: Path) -> list[Path]:
    """All *.py files directly inside .claude/hooks/, sorted (excludes lib/)."""
    if not hooks_dir.is_dir():
        return []
    return sorted(p for p in hooks_dir.iterdir() if p.is_file() and p.suffix == ".py")


def generate_lock(cwd: Path) -> dict:
    """Compute the lock dict for the current hook contents in cwd."""
    cwd = Path(cwd).resolve()
    hooks_dir = cwd / HOOKS_REL
    files = {p.name: _sha256(p) for p in _iter_hook_files(hooks_dir)}
    return {"version": 1, "files": files}


def write_lock(cwd: Path) -> Path:
    """Generate and write hooks.lock. Returns the lock path."""
    cwd = Path(cwd).resolve()
    lock_path = cwd / LOCK_REL
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = generate_lock(cwd)
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return lock_path


def verify_lock(cwd: Path) -> dict:
    """Compare on-disk hook content against the recorded lock.

    Returns {"ok": bool, "missing_lock": bool, "mismatches": [name, ...], "extra": [name, ...], "missing": [name, ...]}.
    """
    cwd = Path(cwd).resolve()
    lock_path = cwd / LOCK_REL
    if not lock_path.exists():
        return {"ok": False, "missing_lock": True, "mismatches": [], "extra": [], "missing": []}

    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "missing_lock": False, "mismatches": [], "extra": [], "missing": [], "error": "lock file is not valid JSON"}

    expected: dict[str, str] = lock.get("files", {})
    current = {p.name: _sha256(p) for p in _iter_hook_files(cwd / HOOKS_REL)}

    mismatches = [name for name, sha in expected.items() if name in current and current[name] != sha]
    missing = [name for name in expected if name not in current]
    extra = [name for name in current if name not in expected]

    ok = not (mismatches or missing or extra)
    return {
        "ok": ok,
        "missing_lock": False,
        "mismatches": mismatches,
        "missing": missing,
        "extra": extra,
    }


def approve_hooks(cwd: Path) -> dict:
    """Regenerate hooks.lock from current on-disk content (i.e., 'approve' edits)."""
    cwd = Path(cwd).resolve()
    if not (cwd / HOOKS_REL).is_dir():
        return {"ok": False, "error": f"No .claude/hooks directory at {cwd}"}
    lock_path = write_lock(cwd)
    return {"ok": True, "lock_path": str(lock_path.relative_to(cwd)), "files": list(generate_lock(cwd)["files"].keys())}


__all__ = ["generate_lock", "write_lock", "verify_lock", "approve_hooks"]
