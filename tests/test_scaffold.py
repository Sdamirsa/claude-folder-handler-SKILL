"""Test scaffolding a fresh .claude/ into an empty repo."""

from __future__ import annotations

import json
from pathlib import Path

from claude_folder_handler.core.scaffold import setup_repo


def _make_node_repo(tmp_path: Path) -> Path:
    (tmp_path / "package.json").write_text(
        '{"name":"test-app","scripts":{"test":"jest"}}', encoding="utf-8"
    )
    return tmp_path


def test_setup_creates_baseline(tmp_path: Path):
    _make_node_repo(tmp_path)
    result = setup_repo(tmp_path, packs=[], dry_run=False)
    assert result["ok"], result

    # Spot-check the baseline files.
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".claude" / "ROUTER.md").exists()
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert (tmp_path / ".claude" / "rules" / "00-global.md").exists()
    assert (tmp_path / ".claude" / "skills" / "commit" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "hooks" / "00-session-start.py").exists()
    assert (tmp_path / ".claude" / "hooks" / "10-pre-deny-secrets.py").exists()
    assert (tmp_path / ".claude" / "hooks" / "20-pre-deny-destructive.py").exists()
    assert (tmp_path / ".claude" / "hooks" / "90-stop-log-invocation.py").exists()
    assert (tmp_path / ".claude" / ".meta" / "version").exists()
    assert (tmp_path / ".claude" / ".meta" / "hooks.lock").exists()
    assert (tmp_path / ".claude" / ".meta" / "packs.json").exists()
    assert (tmp_path / ".claude" / ".meta" / "protected-branches.json").exists()
    assert (tmp_path / ".claude" / "reference" / "INDEX.md").exists()
    assert (tmp_path / ".claude" / "reference" / "README.md").exists()


def test_setup_substitutes_stack(tmp_path: Path):
    _make_node_repo(tmp_path)
    setup_repo(tmp_path, packs=[], dry_run=False)
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "test-app" in claude_md
    assert "npm test" in claude_md


def test_setup_writes_gitignore_managed_block(tmp_path: Path):
    _make_node_repo(tmp_path)
    setup_repo(tmp_path, packs=[], dry_run=False)
    gi = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "# managed:claude-folder-handler" in gi
    assert ".claude/settings.local.json" in gi
    assert ".mcp.json" in gi


def test_setup_renders_settings_json(tmp_path: Path):
    _make_node_repo(tmp_path)
    setup_repo(tmp_path, packs=[], dry_run=False)
    settings_text = (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    settings = json.loads(settings_text)
    assert "permissions" in settings
    deny = settings["permissions"]["deny"]
    assert any(".env" in r for r in deny)
    assert any("rm -rf" in r for r in deny)


def test_setup_refuses_when_claude_exists(tmp_path: Path):
    _make_node_repo(tmp_path)
    (tmp_path / ".claude").mkdir()
    result = setup_repo(tmp_path, packs=[], dry_run=False)
    assert not result["ok"]
    assert "already exists" in result["error"]


def test_setup_dry_run_writes_nothing(tmp_path: Path):
    _make_node_repo(tmp_path)
    result = setup_repo(tmp_path, packs=[], dry_run=True)
    assert result["ok"]
    assert result["dry_run"]
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / "CLAUDE.md").exists()


def test_setup_hooks_are_executable(tmp_path: Path):
    _make_node_repo(tmp_path)
    setup_repo(tmp_path, packs=[], dry_run=False)
    hook = tmp_path / ".claude" / "hooks" / "00-session-start.py"
    assert hook.stat().st_mode & 0o111  # any execute bit set


def test_setup_hooks_lock_matches(tmp_path: Path):
    from claude_folder_handler.core.hooks_lock import verify_lock

    _make_node_repo(tmp_path)
    setup_repo(tmp_path, packs=[], dry_run=False)
    assert verify_lock(tmp_path)["ok"]
