"""Test pack discovery + installation."""

from __future__ import annotations

from pathlib import Path

from claude_folder_handler.core.pack_loader import (
    default_pack_names,
    install_pack,
    list_packs,
)
from claude_folder_handler.core.scaffold import setup_repo


def test_list_packs_returns_catalog():
    cat = list_packs()
    assert cat["ok"]
    assert isinstance(cat["packs"], list)


def test_install_unknown_pack_fails(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\n', encoding="utf-8")
    setup_repo(tmp_path, packs=[], dry_run=False)
    result = install_pack(tmp_path, name="nonexistent-pack")
    assert not result["ok"]
    assert "Unknown pack" in result["error"]


def test_install_without_setup_fails(tmp_path: Path):
    result = install_pack(tmp_path, name="anything")
    assert not result["ok"]
    assert "No .claude" in result["error"]
