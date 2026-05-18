"""Smoke tests: package imports, version reachable, MCP server constructible."""

from __future__ import annotations

import subprocess
import sys

import claude_folder_handler


def test_version_is_present():
    assert isinstance(claude_folder_handler.__version__, str)
    assert claude_folder_handler.__version__.count(".") >= 1


def test_cli_version_flag():
    result = subprocess.run(
        [sys.executable, "-m", "claude_folder_handler", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert claude_folder_handler.__version__ in result.stdout


def test_mcp_server_module_imports():
    from claude_folder_handler import mcp_server

    assert mcp_server.app is not None


def test_data_template_resolves():
    from claude_folder_handler.core.pack_loader import _template_root

    root = _template_root()
    assert root.is_dir(), f"template root not found at {root}"
    # Spot-check a few baseline files.
    assert (root / "CLAUDE.md.tmpl").exists()
    assert (root / "claude" / "ROUTER.md.tmpl").exists()
    assert (root / "claude" / "settings.json.tmpl").exists()
    assert (root / "claude" / "hooks" / "00-session-start.py").exists()
    assert (root / "claude" / "skills" / "commit" / "SKILL.md").exists()
    assert (root / "claude" / "reference" / "INDEX.md").exists()


def test_data_packs_resolves():
    from claude_folder_handler.core.pack_loader import _packs_root

    root = _packs_root()
    assert root.is_dir(), f"packs root not found at {root}"


def test_print_mcp_config():
    result = subprocess.run(
        [sys.executable, "-m", "claude_folder_handler", "print-mcp-config"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "claude-folder-handler" in result.stdout
    assert "uvx" in result.stdout
