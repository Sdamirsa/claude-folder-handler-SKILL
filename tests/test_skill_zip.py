"""Verify the Claude.ai Skill zip builder produces a convention-compliant artifact.

Layout target (Anthropic skill-creator convention):

    claude-folder-handler/
    ├── SKILL.md
    └── scripts/
        ├── scaffold.py
        └── claude_folder_handler/...   (vendored package, no MCP/CLI)

The end-to-end test extracts the zip, runs `scaffold.py --list-packs` and
`scaffold.py --project-name ... --out ...`, then verifies the resulting
scaffold zip contains a real `.claude/` tree — i.e. a Claude.ai user could
unzip the skill, ask Claude to invoke it, and get a working scaffold.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_skill_zip.py"
SKILL_NAME = "claude-folder-handler"


@pytest.fixture(scope="module")
def built_zip() -> Path:
    """Run the build script and return the resulting zip path."""
    out_dir = REPO_ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
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


def test_zip_root_is_skill_named_folder(built_zip: Path):
    """Every entry must live under `<skill-name>/` per the skill convention."""
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    assert names, "zip is empty"
    for n in names:
        assert n.startswith(f"{SKILL_NAME}/"), (
            f"entry {n!r} is not under {SKILL_NAME}/ — Claude.ai expects the "
            "skill folder as the zip root"
        )


def test_zip_contains_skill_md_at_root(built_zip: Path):
    with zipfile.ZipFile(built_zip) as z:
        assert f"{SKILL_NAME}/SKILL.md" in z.namelist()


def test_skill_md_has_required_frontmatter(built_zip: Path):
    with zipfile.ZipFile(built_zip) as z:
        body = z.read(f"{SKILL_NAME}/SKILL.md").decode("utf-8")
    # Frontmatter delimiters
    assert body.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    end = body.find("\n---\n", 4)
    assert end > 0, "SKILL.md frontmatter must be closed with '---'"
    fm = body[4:end]
    assert "name: claude-folder-handler" in fm, "frontmatter missing `name` field"
    assert "description:" in fm, "frontmatter missing `description` field"


def test_zip_has_scripts_layout(built_zip: Path):
    """scripts/scaffold.py + bundled package live under scripts/."""
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    assert f"{SKILL_NAME}/scripts/scaffold.py" in names
    # Vendored package present.
    assert any(n.startswith(f"{SKILL_NAME}/scripts/claude_folder_handler/") for n in names)
    assert f"{SKILL_NAME}/scripts/claude_folder_handler/__init__.py" in names


def test_zip_excludes_mcp_and_cli(built_zip: Path):
    """The skill drives setup_repo() directly — no `mcp` dep needed."""
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    assert not any("mcp_server.py" in n for n in names), "mcp_server.py should be excluded"
    assert not any(n.endswith("/cli.py") for n in names), "cli.py should be excluded"
    assert not any(n.endswith("/__main__.py") for n in names), "__main__.py should be excluded"


def test_zip_bundles_template_and_packs(built_zip: Path):
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    template_files = [n for n in names if "/data/template/" in n]
    pack_files = [n for n in names if "/data/packs/" in n]
    assert len(template_files) >= 15, f"template incomplete: {len(template_files)} files"
    assert len(pack_files) >= 40, f"packs incomplete: {len(pack_files)} files"

    assert any("data/template/claude/ROUTER.md.tmpl" in n for n in names)
    assert any("data/template/claude/hooks/10-pre-deny-secrets.py" in n for n in names)
    expected_packs = {
        "pr-flow", "test-tooling", "data-science", "visualization",
        "llm-app", "llm-extraction", "monorepo", "security-hardening",
    }
    for pack in expected_packs:
        assert any(f"data/packs/{pack}/pack.toml" in n for n in names), f"missing {pack}/pack.toml"


def test_zip_skill_md_does_not_inline_python(built_zip: Path):
    """SKILL.md should delegate to scripts/scaffold.py, not paste Python at runtime.

    Inline `sys.path.insert` snippets are the failure mode we're fixing in
    v0.1.1 — deterministic work belongs in scripts/, not in prose.
    """
    with zipfile.ZipFile(built_zip) as z:
        body = z.read(f"{SKILL_NAME}/SKILL.md").decode("utf-8")
    assert "scripts/scaffold.py" in body, (
        "SKILL.md should reference scripts/scaffold.py as the entry point"
    )
    assert "sys.path.insert" not in body, (
        "SKILL.md should not ask Claude to run sys.path.insert at runtime — "
        "let scripts/scaffold.py handle that"
    )


def test_bundled_scaffold_list_packs(built_zip: Path):
    """Extract the skill, run scaffold.py --list-packs, verify catalog."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(built_zip) as z:
            z.extractall(tmp_path)
        scaffold = tmp_path / SKILL_NAME / "scripts" / "scaffold.py"
        assert scaffold.exists()

        result = subprocess.run(
            [sys.executable, str(scaffold), "--list-packs"],
            capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0, f"--list-packs failed: {result.stderr}"
        catalog = json.loads(result.stdout)
        assert catalog["ok"] is True
        names = {p["name"] for p in catalog["packs"]}
        assert len(names) == 8, f"expected 8 packs, got {names}"
        assert "data-science" in names
        assert "security-hardening" in names


def test_bundled_scaffold_builds_working_scaffold_zip(built_zip: Path):
    """End-to-end: extract skill → run scaffold.py → verify the output zip
    has a real .claude/ tree the user could unzip at a repo root.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(built_zip) as z:
            z.extractall(tmp_path)
        scaffold = tmp_path / SKILL_NAME / "scripts" / "scaffold.py"

        # Stand in for an uploaded pyproject.toml so detect_stack has signal.
        manifest = tmp_path / "uploaded-pyproject.toml"
        manifest.write_text('[project]\nname = "skill-test-target"\n', encoding="utf-8")

        out_zip = tmp_path / "scaffold-out.zip"
        result = subprocess.run(
            [
                sys.executable, str(scaffold),
                "--project-name", "skill-test-target",
                "--manifest-file", str(manifest),
                "--packs", "data-science,security-hardening",
                "--out", str(out_zip),
            ],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, (
            f"scaffold.py failed: stdout={result.stdout}\nstderr={result.stderr}"
        )
        summary = json.loads(result.stdout)
        assert summary["ok"] is True
        assert summary["out"] == str(out_zip)
        assert summary["files"] > 20, f"scaffold seems too small: {summary['files']} files"
        assert "data-science" in summary["packs_installed"]
        assert "security-hardening" in summary["packs_installed"]

        # Verify the OUTPUT zip is a real .claude/ scaffold a user could unzip.
        with zipfile.ZipFile(out_zip) as out:
            out_names = out.namelist()
        assert "CLAUDE.md" in out_names
        assert ".claude/ROUTER.md" in out_names
        assert ".claude/settings.json" in out_names
        assert ".claude/.meta/version" in out_names
        assert ".claude/hooks/10-pre-deny-secrets.py" in out_names
        # No leading project-name directory inside the output — users unzip at repo root.
        assert not any(n.startswith("skill-test-target/") for n in out_names), (
            "output zip should not nest under the project name"
        )


def test_bundled_scaffold_handles_no_packs(built_zip: Path):
    """Empty pack list is valid — baseline-only scaffold."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(built_zip) as z:
            z.extractall(tmp_path)
        scaffold = tmp_path / SKILL_NAME / "scripts" / "scaffold.py"

        out_zip = tmp_path / "baseline-only.zip"
        result = subprocess.run(
            [
                sys.executable, str(scaffold),
                "--project-name", "bare-repo",
                "--packs", "",
                "--out", str(out_zip),
            ],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"scaffold.py failed: {result.stderr}"
        summary = json.loads(result.stdout)
        assert summary["ok"] is True
        assert summary["packs_installed"] == []
        with zipfile.ZipFile(out_zip) as out:
            assert ".claude/ROUTER.md" in out.namelist()


def test_bundled_scaffold_missing_required_args_errors(built_zip: Path):
    """Argparse should fail-fast when --project-name or --out is missing."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(built_zip) as z:
            z.extractall(tmp_path)
        scaffold = tmp_path / SKILL_NAME / "scripts" / "scaffold.py"

        result = subprocess.run(
            [sys.executable, str(scaffold)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0, "scaffold.py with no args should fail"
