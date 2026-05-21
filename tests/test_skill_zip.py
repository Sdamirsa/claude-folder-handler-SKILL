"""Verify the Claude.ai Skill zip builder produces a working artifact."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_skill_zip.py"


@pytest.fixture(scope="module")
def built_zip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run the build script into a tmp dist; return the resulting zip path."""
    # Patch DIST at the env level by running the build in-process with a custom CWD.
    # Simpler: just run it; the script writes to repo-relative dist/.
    out_dir = REPO_ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    # Find existing zip and delete to force rebuild
    for existing in out_dir.glob("claude-folder-handler-skill-*.zip"):
        existing.unlink()
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"build failed: {result.stderr}"
    zips = list(out_dir.glob("claude-folder-handler-skill-*.zip"))
    assert len(zips) == 1, f"expected one skill zip, got {zips}"
    return zips[0]


def test_skill_zip_contains_skill_md(built_zip: Path):
    with zipfile.ZipFile(built_zip) as z:
        assert "SKILL.md" in z.namelist()


def test_skill_zip_contains_readme(built_zip: Path):
    with zipfile.ZipFile(built_zip) as z:
        assert "README.md" in z.namelist()


def test_skill_zip_excludes_mcp_server(built_zip: Path):
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    # We strip MCP server + CLI to avoid the mcp runtime dep.
    assert not any("mcp_server.py" in n for n in names), "mcp_server.py should be excluded"
    assert not any("/cli.py" in n for n in names), "cli.py should be excluded"
    assert not any("__main__.py" in n for n in names), "__main__.py should be excluded"


def test_skill_zip_includes_template_and_packs(built_zip: Path):
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    template_files = [n for n in names if "/data/template/" in n]
    pack_files = [n for n in names if "/data/packs/" in n]
    assert len(template_files) >= 15, f"template incomplete: {len(template_files)} files"
    assert len(pack_files) >= 40, f"packs incomplete: {len(pack_files)} files"

    # Spot-check a few key files.
    assert any("data/template/claude/ROUTER.md.tmpl" in n for n in names)
    assert any("data/template/claude/hooks/10-pre-deny-secrets.py" in n for n in names)
    # Each of the 8 packs has at least its pack.toml.
    expected_packs = {
        "pr-flow", "test-tooling", "data-science", "visualization",
        "llm-app", "llm-extraction", "monorepo", "security-hardening",
    }
    for pack in expected_packs:
        assert any(f"data/packs/{pack}/pack.toml" in n for n in names), f"missing {pack}/pack.toml"


def test_skill_zip_extracted_pkg_imports_and_scaffolds(built_zip: Path):
    """End-to-end: extract zip, import bundled pkg, scaffold a fake repo."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Extract.
        with zipfile.ZipFile(built_zip) as z:
            z.extractall(tmp_path)

        # Set up a fake target repo with a pyproject.toml so detect_stack works.
        target = tmp_path / "fake-repo"
        target.mkdir()
        (target / "pyproject.toml").write_text(
            '[project]\nname = "skill-test-target"\n', encoding="utf-8"
        )

        # Run the scaffold using the BUNDLED pkg (not the repo's installed pkg).
        # We do this in a subprocess to avoid module-import collisions with
        # the already-imported claude_folder_handler from the repo install.
        runner = f"""
import sys, json
sys.path.insert(0, {str(tmp_path / 'pkg')!r})

# Force fresh import (the test process may have the repo version loaded).
for mod in list(sys.modules):
    if mod.startswith('claude_folder_handler'):
        del sys.modules[mod]

from claude_folder_handler.core.scaffold import setup_repo
from claude_folder_handler.core.pack_loader import list_packs

cat = list_packs()
assert cat['ok'] and len(cat['packs']) == 8, f'packs not visible from skill zip: {{cat}}'

result = setup_repo({str(target)!r}, packs=[], dry_run=False)
assert result['ok'], result

# Confirm a couple of key scaffolded files exist.
from pathlib import Path
t = Path({str(target)!r})
assert (t / 'CLAUDE.md').exists()
assert (t / '.claude' / 'ROUTER.md').exists()
assert (t / '.claude' / 'hooks' / '10-pre-deny-secrets.py').exists()
print(json.dumps({{'ok': True, 'files': len(result['files_written'])}}))
"""
        result = subprocess.run(
            [sys.executable, "-c", runner],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"sandbox simulation failed:\nstdout={result.stdout}\nstderr={result.stderr}"
        assert '"ok": true' in result.stdout
