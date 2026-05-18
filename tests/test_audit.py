"""Audit reports + structure tests."""

from __future__ import annotations

from pathlib import Path

from claude_folder_handler.core.audit import audit_repo
from claude_folder_handler.core.scaffold import setup_repo


def _scaffolded(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\n', encoding="utf-8")
    setup_repo(tmp_path, packs=[], dry_run=False)
    return tmp_path


def test_audit_returns_ok_on_fresh_scaffold(tmp_path: Path):
    _scaffolded(tmp_path)
    result = audit_repo(tmp_path)
    assert result["ok"]
    # Fresh scaffold should have no drift / lint warnings.
    drift = [w for w in result["warnings"] if w["category"] == "drift"]
    lint = [w for w in result["warnings"] if w["category"] == "lint"]
    assert drift == [], drift
    assert lint == [], lint


def test_audit_detects_hooks_lock_drift(tmp_path: Path):
    repo = _scaffolded(tmp_path)
    hook = repo / ".claude" / "hooks" / "00-session-start.py"
    # Tamper.
    hook.write_text(hook.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    result = audit_repo(repo)
    drift = [w for w in result["warnings"] if w["category"] == "drift"]
    assert drift, "expected drift warnings"
    assert any(w["kind"] == "hooks-lock-mismatch" for w in drift)


def test_audit_detects_long_claude_md(tmp_path: Path):
    repo = _scaffolded(tmp_path)
    claude_md = repo / "CLAUDE.md"
    claude_md.write_text("\n".join(["# header"] + ["filler"] * 100), encoding="utf-8")
    result = audit_repo(repo)
    size = [w for w in result["warnings"] if w["category"] == "size"]
    assert any(w["kind"] == "claude-md-too-long" for w in size)


def test_audit_reports_no_claude_dir(tmp_path: Path):
    result = audit_repo(tmp_path)
    assert not result["ok"]
    assert "No .claude" in result["error"]
