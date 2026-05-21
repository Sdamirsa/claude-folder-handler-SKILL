"""Verify the Claude.ai Skill zip builder produces a convention-compliant artifact.

Claude.ai's uploader enforces TWO rules:

  1. The outer zip must contain exactly one `SKILL.md`.
  2. The outer zip must not contain any nested `.zip` files.

The bundled `data/` tree has 13 nested `SKILL.md` files (baseline `commit`
skill + every pack-skill body) which are templates for the end-user's
`.claude/skills/` directory after scaffolding — NOT skills for Claude.ai's
loader. To satisfy both validator rules at once, the build script renames
every bundled `SKILL.md` to `_skill_body.md` at build time, and the embedded
`scripts/scaffold.py` renames them back to `SKILL.md` on disk on first run
before importing the package.

Layout (matches https://github.com/anthropics/skills/tree/main/skills/algorithmic-art):

    claude-folder-handler/
    ├── SKILL.md                          # the only SKILL.md in the outer zip
    └── scripts/
        ├── scaffold.py
        └── claude_folder_handler/
            ├── __init__.py
            ├── core/
            └── data/
                ├── template/.../skills/commit/_skill_body.md   ← was SKILL.md
                └── packs/.../skills/X/_skill_body.md           ← was SKILL.md

The end-to-end test verifies the rename round-trip: extract the zip, run
scaffold.py (which renames `_skill_body.md` -> `SKILL.md` before importing),
build a real scaffold, and confirm the output `.claude/skills/commit/SKILL.md`
exists in the result.
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
SKILL_MD_ALIAS = "_skill_body.md"


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
    """Every entry must live under `<skill-name>/`."""
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    assert names, "zip is empty"
    for n in names:
        assert n.startswith(f"{SKILL_NAME}/"), (
            f"entry {n!r} is not under {SKILL_NAME}/"
        )


def test_zip_contains_exactly_one_skill_md(built_zip: Path):
    """Claude.ai validator rule #1: exactly one SKILL.md per upload."""
    with zipfile.ZipFile(built_zip) as z:
        skill_mds = [
            n for n in z.namelist()
            if n.endswith("/SKILL.md") or n == "SKILL.md"
        ]
    assert len(skill_mds) == 1, (
        f"outer zip must contain exactly 1 SKILL.md, found {len(skill_mds)}: "
        f"{skill_mds}. Bundled data SKILL.md files must be aliased to "
        f"`{SKILL_MD_ALIAS}` at build time."
    )
    assert skill_mds[0] == f"{SKILL_NAME}/SKILL.md"


def test_zip_has_no_nested_zip_files(built_zip: Path):
    """Claude.ai validator rule #2: no nested .zip files in the upload.

    This was the v0.1.2 failure mode — we packed `data/` as `data.zip`,
    which solved rule #1 but tripped rule #2. v0.1.3 ships `data/` as
    loose files with the SKILL.md alias rename.
    """
    with zipfile.ZipFile(built_zip) as z:
        nested = [n for n in z.namelist() if n.lower().endswith(".zip")]
    assert not nested, (
        f"outer zip must not contain nested .zip files, found: {nested}"
    )


def test_skill_md_has_required_frontmatter(built_zip: Path):
    with zipfile.ZipFile(built_zip) as z:
        body = z.read(f"{SKILL_NAME}/SKILL.md").decode("utf-8")
    assert body.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    end = body.find("\n---\n", 4)
    assert end > 0, "SKILL.md frontmatter must be closed with '---'"
    fm = body[4:end]
    assert "name: claude-folder-handler" in fm
    assert "description:" in fm


def test_skill_md_description_is_single_line(built_zip: Path):
    """Match algorithmic-art / docx style: single-line description string."""
    with zipfile.ZipFile(built_zip) as z:
        body = z.read(f"{SKILL_NAME}/SKILL.md").decode("utf-8")
    fm = body.split("\n---\n", 2)[0][4:]
    desc_line = next((ln for ln in fm.splitlines() if ln.startswith("description:")), None)
    assert desc_line is not None, "no description: line in frontmatter"
    assert not desc_line.rstrip().endswith("|"), (
        "description should be inline, not a `|` literal block"
    )
    value = desc_line.split(":", 1)[1].strip()
    assert len(value) >= 200, f"description too short: {len(value)} chars"


def test_zip_has_scripts_layout(built_zip: Path):
    """scripts/scaffold.py + bundled package live under scripts/."""
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    assert f"{SKILL_NAME}/scripts/scaffold.py" in names
    assert f"{SKILL_NAME}/scripts/claude_folder_handler/__init__.py" in names
    assert f"{SKILL_NAME}/scripts/claude_folder_handler/core/scaffold.py" in names
    assert f"{SKILL_NAME}/scripts/claude_folder_handler/core/pack_loader.py" in names


def test_bundled_data_uses_skill_md_alias(built_zip: Path):
    """Every bundled SKILL.md in `data/` ships as `_skill_body.md`."""
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    data_files = [n for n in names if "/claude_folder_handler/data/" in n]
    assert len(data_files) >= 60, f"data tree incomplete: {len(data_files)} files"

    aliased = [n for n in data_files if n.endswith(f"/{SKILL_MD_ALIAS}")]
    # Baseline `commit` skill + every pack-skill (12) = 13 aliased files.
    assert len(aliased) == 13, (
        f"expected 13 `_skill_body.md` files, got {len(aliased)}. The build "
        "script must rename every bundled `SKILL.md` to the alias."
    )

    # No bundled SKILL.md should leak through under data/.
    leaked = [n for n in data_files if n.endswith("/SKILL.md")]
    assert not leaked, f"bundled SKILL.md leaked into outer zip: {leaked}"


def test_zip_bundles_template_and_packs(built_zip: Path):
    with zipfile.ZipFile(built_zip) as z:
        names = z.namelist()
    template_files = [n for n in names if "/data/template/" in n]
    pack_files = [n for n in names if "/data/packs/" in n]
    assert len(template_files) >= 15, f"template incomplete: {len(template_files)} files"
    assert len(pack_files) >= 40, f"packs incomplete: {len(pack_files)} files"

    # Spot-check a few key paths still made it through (unaliased — only
    # SKILL.md gets renamed).
    assert any(n.endswith("data/template/claude/ROUTER.md.tmpl") for n in names)
    assert any(n.endswith("data/template/claude/hooks/10-pre-deny-secrets.py") for n in names)
    expected_packs = {
        "pr-flow", "test-tooling", "data-science", "visualization",
        "llm-app", "llm-extraction", "monorepo", "security-hardening",
    }
    for pack in expected_packs:
        assert any(f"data/packs/{pack}/pack.toml" in n for n in names), f"missing {pack}/pack.toml"


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
    assert "scripts/scaffold.py" in body
    assert "sys.path.insert" not in body


def test_bundled_scaffold_list_packs(built_zip: Path):
    """Extract → run scaffold.py --list-packs → verify catalog.

    Also verifies the SKILL.md restoration step worked: after running,
    every `_skill_body.md` under data/ has been renamed to `SKILL.md` on
    disk so the package's pack loader can find the skill bodies.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(built_zip) as z:
            z.extractall(tmp_path)
        scaffold = tmp_path / SKILL_NAME / "scripts" / "scaffold.py"

        # Pre-condition: extracted skill has `_skill_body.md` files, no SKILL.md
        # inside data/.
        data_dir = tmp_path / SKILL_NAME / "scripts" / "claude_folder_handler" / "data"
        pre_aliased = list(data_dir.rglob(SKILL_MD_ALIAS))
        pre_skill_mds = list(data_dir.rglob("SKILL.md"))
        assert len(pre_aliased) == 13, f"expected 13 aliased files pre-run, got {len(pre_aliased)}"
        assert len(pre_skill_mds) == 0, f"unexpected SKILL.md files pre-run: {pre_skill_mds}"

        # Run.
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

        # Post-condition: rename happened.
        post_aliased = list(data_dir.rglob(SKILL_MD_ALIAS))
        post_skill_mds = list(data_dir.rglob("SKILL.md"))
        assert len(post_aliased) == 0, (
            f"alias files should be gone after rename, found: {post_aliased}"
        )
        assert len(post_skill_mds) == 13, (
            f"expected 13 SKILL.md files post-rename, got {len(post_skill_mds)}"
        )
        # Sentinel file should exist.
        assert (data_dir / ".skill_md_restored").exists()


def test_bundled_scaffold_builds_working_scaffold_zip(built_zip: Path):
    """End-to-end: extract skill → run scaffold.py → verify output zip
    has a real .claude/ tree with the pack-skill SKILL.md files restored.
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
        # Baseline scaffold present.
        assert "CLAUDE.md" in out_names
        assert ".claude/ROUTER.md" in out_names
        assert ".claude/settings.json" in out_names
        assert ".claude/.meta/version" in out_names
        assert ".claude/hooks/10-pre-deny-secrets.py" in out_names
        # The user-facing OUTPUT (not the outer skill zip!) gets real
        # SKILL.md filenames — that's what `.claude/skills/` expects.
        assert ".claude/skills/commit/SKILL.md" in out_names
        # Pack-skill SKILL.md restored too.
        assert any(
            n.startswith(".claude/skills/") and n.endswith("/SKILL.md")
            and "commit" not in n
            for n in out_names
        ), "pack-skill SKILL.md files missing from scaffold output"
        # No alias filenames leak into the scaffold output.
        assert not any(n.endswith(f"/{SKILL_MD_ALIAS}") for n in out_names), (
            f"alias {SKILL_MD_ALIAS} leaked into scaffold output"
        )
        # No leading project-name dir.
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
            out_names = out.namelist()
        assert ".claude/ROUTER.md" in out_names
        # Baseline `commit` skill body is restored.
        assert ".claude/skills/commit/SKILL.md" in out_names


def test_bundled_scaffold_rename_is_idempotent(built_zip: Path):
    """Running scaffold.py twice in the same extraction must not break things.

    The sentinel file ensures the second run skips the rename loop.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(built_zip) as z:
            z.extractall(tmp_path)
        scaffold = tmp_path / SKILL_NAME / "scripts" / "scaffold.py"

        for run in range(2):
            result = subprocess.run(
                [sys.executable, str(scaffold), "--list-packs"],
                capture_output=True, text=True, timeout=20,
            )
            assert result.returncode == 0, f"run {run+1} failed: {result.stderr}"
            catalog = json.loads(result.stdout)
            assert len(catalog["packs"]) == 8


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
