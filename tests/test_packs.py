"""Pack installation integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claude_folder_handler.core.description_lint import lint_file
from claude_folder_handler.core.hooks_lock import verify_lock
from claude_folder_handler.core.managed_blocks import deep_merge_settings
from claude_folder_handler.core.pack_loader import (
    _packs_root,
    default_pack_names,
    install_pack,
    list_packs,
)
from claude_folder_handler.core.scaffold import setup_repo


ALL_PACKS = [
    "pr-flow",
    "test-tooling",
    "data-science",
    "visualization",
    "llm-app",
    "llm-extraction",
    "monorepo",
    "security-hardening",
]


def test_catalog_contains_all_packs():
    catalog = list_packs()
    names = {p["name"] for p in catalog["packs"]}
    assert names >= set(ALL_PACKS), f"missing: {set(ALL_PACKS) - names}"


def test_llm_scientist_defaults():
    """The default-checked packs should be the LLM-scientist set."""
    defaults = set(default_pack_names())
    expected = {"data-science", "visualization", "llm-app", "llm-extraction", "security-hardening"}
    assert defaults == expected, f"defaults={defaults} expected={expected}"


@pytest.fixture
def scaffolded(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    result = setup_repo(tmp_path, packs=[], dry_run=False)
    assert result["ok"], result
    return tmp_path


@pytest.mark.parametrize("pack_name", ALL_PACKS)
def test_install_each_pack(scaffolded: Path, pack_name: str):
    result = install_pack(scaffolded, name=pack_name, dry_run=False)
    assert result["ok"], f"{pack_name}: {result}"
    # Pack must be recorded in packs.json
    state = json.loads((scaffolded / ".claude" / ".meta" / "packs.json").read_text(encoding="utf-8"))
    assert pack_name in state["installed"]
    # hooks.lock must still verify after install
    assert verify_lock(scaffolded)["ok"], f"{pack_name}: lock drift after install"


def test_install_same_pack_twice_refuses(scaffolded: Path):
    r1 = install_pack(scaffolded, name="pr-flow", dry_run=False)
    assert r1["ok"]
    r2 = install_pack(scaffolded, name="pr-flow", dry_run=False)
    assert not r2["ok"]
    assert "already installed" in r2["error"]


def test_install_all_packs_together(scaffolded: Path):
    for name in ALL_PACKS:
        result = install_pack(scaffolded, name=name, dry_run=False)
        assert result["ok"], f"{name}: {result}"
    # All packs recorded
    state = json.loads((scaffolded / ".claude" / ".meta" / "packs.json").read_text(encoding="utf-8"))
    assert set(state["installed"]) == set(ALL_PACKS)
    # Router has rows from each pack
    router = (scaffolded / ".claude" / "ROUTER.md").read_text(encoding="utf-8")
    for name in ALL_PACKS:
        assert f"managed:pack-{name}" in router, f"missing managed block for {name}"


def test_install_dry_run_writes_nothing(scaffolded: Path):
    before = sorted((scaffolded / ".claude").rglob("*"))
    result = install_pack(scaffolded, name="pr-flow", dry_run=True)
    assert result["ok"]
    assert result["dry_run"]
    after = sorted((scaffolded / ".claude").rglob("*"))
    assert before == after


def test_settings_overlay_merges(scaffolded: Path):
    # llm-app adds a PostToolUse hook entry. Verify it lands.
    install_pack(scaffolded, name="llm-app", dry_run=False)
    settings = json.loads((scaffolded / ".claude" / "settings.json").read_text(encoding="utf-8"))
    post_hooks = settings.get("hooks", {}).get("PostToolUse", [])
    # Should have a matcher entry mentioning the stale-model hook.
    commands = []
    for entry in post_hooks:
        for h in entry.get("hooks", []):
            commands.append(h.get("command", ""))
    assert any("15-warn-stale-model" in c for c in commands), (
        f"PostToolUse missing stale-model hook; got commands: {commands}"
    )


# ----- Description lint: every shipped SKILL.md + agent .md must pass -----


def _collect_pack_descriptions() -> list[Path]:
    root = _packs_root()
    paths: list[Path] = []
    for pack_dir in root.iterdir():
        if not pack_dir.is_dir():
            continue
        content = pack_dir / "content"
        if not content.is_dir():
            continue
        paths.extend(content.rglob("SKILL.md"))
        agents = content / "agents"
        if agents.is_dir():
            paths.extend(agents.glob("*.md"))
    return paths


@pytest.mark.parametrize("path", _collect_pack_descriptions(), ids=lambda p: str(p.relative_to(_packs_root())))
def test_pack_description_lint_clean(path: Path):
    warnings = lint_file(path)
    assert warnings == [], f"{path} fails description lint: {warnings}"
