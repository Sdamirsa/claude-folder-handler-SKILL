"""Verify the Claude.ai Skill zip builder produces a convention-compliant artifact.

Layout target (Anthropic skill-creator convention, see
https://github.com/anthropics/skills/tree/main/skills/algorithmic-art):

    claude-folder-handler/
    ├── SKILL.md                          # exactly one — Claude.ai rejects > 1
    └── scripts/
        ├── scaffold.py
        └── claude_folder_handler/
            ├── __init__.py
            ├── core/                     # code-only (no data/)
            └── data.zip                  # template/ + 8 packs packed as a blob

Claude.ai's uploader counts every SKILL.md in the outer zip and rejects on
more than one. The bundled package's `data/` tree contains 13 nested
SKILL.md files (baseline `commit` skill + 12 pack-skill bodies) which are
templates for the end-user's `.claude/skills/` directory — NOT skills for
Claude.ai. We ship `data/` as `data.zip` so the outer namelist only sees one
SKILL.md.

The end-to-end test extracts the skill zip, runs `scaffold.py --list-packs`
and a real scaffold build, and verifies the bundled data.zip extracted
correctly — i.e. a Claude.ai user could drag-drop the .zip and immediately
get a working scaffold.
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


def test_zip_contains_exactly_one_skill_md(built_zip: Path):
    """Claude.ai's validator rejects any zip with > 1 SKILL.md.

    This was the v0.1.1 failure mode: bundling `data/` as plain files dragged
    the 13 nested SKILL.md files (pack-skill bodies, baseline `commit`) into
    the outer namelist. Fixed in v0.1.2 by packing `data/` as `data.zip`.
    """
    with zipfile.ZipFile(built_zip) as z:
        skill_mds = [
            n for n in z.namelist()
            if n.endswith("/SKILL.md") or n == "SKILL.md"
        ]
    assert len(skill_mds) == 1, (
        f"outer zip must contain exactly 1 SKILL.md, found {len(skill_mds)}: "
        f"{skill_mds}. The bundled `data/` tree must be packed as data.zip."
    )
    assert skill_mds[0] == f"{SKILL_NAME}/SKILL.md"


def test_skill_md_has_required_frontmatter(built_zip: Path):
    with zipfile.ZipFile(built_zip) as z:
        body = z.read(f"{SKILL_NAME}/SKILL.md").decode("utf-8")
    assert body.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    end = body.find("\n---\n", 4)
    assert end > 0, "SKILL.md frontmatter must be closed with '---'"
    fm = body[4:end]
    assert "name: claude-folder-handler" in fm, "frontmatter missing `name` field"
    assert "description:" in fm, "frontmatter missing `description` field"


def test_skill_md_description_is_single_line(built_zip: Path):
    """Match algorithmic-art / docx style: single-line description string.

    Literal-block (`description: |`) parses fine in standards-compliant YAML
    but tripped at least one validator we've seen. Keep it single-line for
    maximum tooling compatibility.
    """
    with zipfile.ZipFile(built_zip) as z:
        body = z.read(f"{SKILL_NAME}/SKILL.md").decode("utf-8")
    # Find the description line in the frontmatter.
    fm = body.split("\n---\n", 2)[0][4:]  # strip leading "---\n"
    desc_line = next((ln for ln in fm.splitlines() if ln.startswith("description:")), None)
    assert desc_line is not None, "no description: line in frontmatter"
    # The value should be on the same line (not `description: |` followed by indented text).
    assert not desc_line.rstrip().endswith("|"), (
        "description should be inline, not a `|` literal block"
    )
    value = desc_line.split(":", 1)[1].strip()
    assert len(value) >= 200, f"description too short: {len(value)} chars"


def test_zip_has_scripts_layout(built_zip: Path):
    """scripts/scaffold.py + bundled package code live under scripts/."""
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    assert f"{SKILL_NAME}/scripts/scaffold.py" in names
    assert f"{SKILL_NAME}/scripts/claude_folder_handler/__init__.py" in names
    # Code modules present.
    assert f"{SKILL_NAME}/scripts/claude_folder_handler/core/scaffold.py" in names
    assert f"{SKILL_NAME}/scripts/claude_folder_handler/core/pack_loader.py" in names


def test_zip_bundles_data_as_inner_zip(built_zip: Path):
    """The data/ tree is packed as data.zip — not as loose files in the outer zip."""
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    assert f"{SKILL_NAME}/scripts/claude_folder_handler/data.zip" in names
    # And there must be NO loose data/ files in the outer namelist.
    loose_data = [n for n in names if "/data/template/" in n or "/data/packs/" in n]
    assert not loose_data, (
        f"data/ files leaked into outer zip namelist: {loose_data[:3]}... — "
        "they must be inside data.zip"
    )


def test_data_zip_contents_complete(built_zip: Path):
    """The inner data.zip must contain the full template + 8 packs."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(built_zip) as z:
            z.extract(
                f"{SKILL_NAME}/scripts/claude_folder_handler/data.zip",
                tmp_path,
            )
        data_zip = tmp_path / SKILL_NAME / "scripts" / "claude_folder_handler" / "data.zip"
        with zipfile.ZipFile(data_zip) as dz:
            dnames = dz.namelist()

    template_files = [n for n in dnames if n.startswith("template/")]
    pack_files = [n for n in dnames if n.startswith("packs/")]
    assert len(template_files) >= 15, f"template incomplete: {len(template_files)} files"
    assert len(pack_files) >= 40, f"packs incomplete: {len(pack_files)} files"

    assert "template/claude/ROUTER.md.tmpl" in dnames
    assert "template/claude/hooks/10-pre-deny-secrets.py" in dnames
    expected_packs = {
        "pr-flow", "test-tooling", "data-science", "visualization",
        "llm-app", "llm-extraction", "monorepo", "security-hardening",
    }
    for pack in expected_packs:
        assert f"packs/{pack}/pack.toml" in dnames, f"missing {pack}/pack.toml"


def test_zip_excludes_mcp_and_cli(built_zip: Path):
    """The skill drives setup_repo() directly — no `mcp` dep needed."""
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    assert not any("mcp_server.py" in n for n in names), "mcp_server.py should be excluded"
    assert not any(n.endswith("/cli.py") for n in names), "cli.py should be excluded"
    assert not any(n.endswith("/__main__.py") for n in names), "__main__.py should be excluded"


def test_zip_skill_md_does_not_inline_python(built_zip: Path):
    """SKILL.md should delegate to scripts/scaffold.py, not paste Python at runtime."""
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

        # The first run should have materialized data/ from data.zip on disk.
        data_dir = tmp_path / SKILL_NAME / "scripts" / "claude_folder_handler" / "data"
        assert (data_dir / "template").is_dir(), "data.zip was not extracted"
        assert (data_dir / "packs").is_dir(), "data.zip was not extracted"


def test_bundled_scaffold_builds_working_scaffold_zip(built_zip: Path):
    """End-to-end: extract skill → run scaffold.py → verify output zip
    has a real .claude/ tree the user could unzip at a repo root.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(built_zip) as z:
            z.extractall(tmp_path)
        scaffold = tmp_path / SKILL_NAME / "scripts" / "scaffold.py"

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

        with zipfile.ZipFile(out_zip) as out:
            out_names = out.namelist()
        assert "CLAUDE.md" in out_names
        assert ".claude/ROUTER.md" in out_names
        assert ".claude/settings.json" in out_names
        assert ".claude/.meta/version" in out_names
        assert ".claude/hooks/10-pre-deny-secrets.py" in out_names
        # The OUTPUT zip — which IS scaffolded for the user's project — will
        # naturally contain pack-skill SKILL.md files. That's correct: those
        # belong in the user's .claude/skills/ directory. Only the OUTER
        # skill zip (the one we upload to Claude.ai) has the 1-SKILL.md rule.
        assert ".claude/skills/commit/SKILL.md" in out_names
        # No leading project-name directory inside the output.
        assert not any(n.startswith("skill-test-target/") for n in out_names)


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
