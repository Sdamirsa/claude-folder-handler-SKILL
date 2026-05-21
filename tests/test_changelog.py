"""CHANGELOG.md sanity tests — keep the release flow honest."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"

sys.path.insert(0, str(ROOT / "scripts"))


def test_changelog_exists():
    assert CHANGELOG.exists(), "CHANGELOG.md must live at repo root"


def test_changelog_has_unreleased_section():
    text = CHANGELOG.read_text(encoding="utf-8")
    assert re.search(r"^## \[Unreleased\]\s*$", text, re.MULTILINE), (
        "CHANGELOG.md must have an '## [Unreleased]' section"
    )


def test_changelog_has_current_version_section():
    """The version in pyproject.toml must have a matching CHANGELOG section."""
    from claude_folder_handler import __version__

    text = CHANGELOG.read_text(encoding="utf-8")
    pat = rf"^## \[{re.escape(__version__)}\]"
    assert re.search(pat, text, re.MULTILINE), (
        f"CHANGELOG.md is missing a '[{__version__}]' section. "
        "Run scripts/bump.py before tagging the release."
    )


def test_extract_changelog_returns_current_section():
    """The extractor script can pull the current version's notes."""
    from claude_folder_handler import __version__
    from extract_changelog import extract  # type: ignore[import-not-found]

    body = extract(__version__)
    assert f"v{__version__}" in body
    # The body should include at least one of the standard Keep-a-Changelog headings.
    assert any(h in body for h in ("### Added", "### Changed", "### Fixed", "### Removed",
                                   "### Deprecated", "### Security", "### Documentation"))


def test_extract_changelog_unknown_version_errors():
    from extract_changelog import extract  # type: ignore[import-not-found]

    with pytest.raises(SystemExit):
        extract("99.99.99")
