"""Test description-lint rules."""

from __future__ import annotations

from pathlib import Path

from claude_folder_handler.core.description_lint import (
    lint_description,
    lint_file,
    parse_frontmatter,
)


GOOD = (
    "Stages and commits the current changes in the working tree after a quick sanity check "
    "on the diff. Inspects `git status` and `git diff`, drafts a concise commit message "
    "from the diff (subject line + 1-2 line body explaining the WHY, not the WHAT), runs "
    "the project's lint or test gate if it is fast, and creates the commit. Honors the "
    "protected-branch list. "
    'Use when the user says "commit", "commit this", "save changes", "check in", '
    '"stage and commit", "wrap this up", "make a commit", or finishes a logical unit of work. '
    "NOT for opening a pull request — use the open-pr skill from the +pr-flow pack instead. "
    "NOT for amending or rewriting history."
)


def test_good_description_passes():
    warnings = lint_description(GOOD)
    assert warnings == [], warnings


def test_too_short_warns():
    short = (
        'Commits things. Use when the user says "commit" or "save". '
        'NOT for opening a PR.'
    )
    warnings = lint_description(short)
    assert any("600" in w for w in warnings)


def test_missing_not_for_warns():
    no_not = (
        "Stages and commits the current changes in the working tree after a quick sanity check "
        "on the diff. Inspects `git status` and `git diff`, drafts a concise commit message. "
        'Use when the user says "commit", "commit this", "save changes", "check in", '
        '"stage and commit", "wrap this up", "make a commit", or finishes a logical unit of work. '
        "Adds detail. " * 5
    )
    warnings = lint_description(no_not)
    assert any("NOT for" in w for w in warnings)


def test_missing_quoted_phrases_warns():
    no_quotes = (
        "Commits stuff. " * 50 + " Use when committing. NOT for opening a PR — use open-pr."
    )
    warnings = lint_description(no_quotes[:1000])
    assert any("quoted" in w for w in warnings)


def test_first_person_warns():
    fp = (
        "I will commit your changes for you. " + "Adds detail. " * 50 +
        ' Use when the user says "commit" or "save". NOT for opening a PR — use open-pr.'
    )
    warnings = lint_description(fp[:1100])
    assert any("third-person" in w for w in warnings)


def test_parse_frontmatter_extracts_description(tmp_path: Path):
    md = tmp_path / "SKILL.md"
    md.write_text(
        '---\n'
        'name: foo\n'
        'description: |\n'
        '  hello world\n'
        '  more\n'
        '---\n\nbody\n',
        encoding="utf-8",
    )
    fm = parse_frontmatter(md)
    assert fm is not None
    assert fm["name"] == "foo"
    assert "hello world" in fm["description"]
    assert "more" in fm["description"]


def test_lint_file_on_baseline_commit():
    """The bundled baseline commit skill must pass the lint."""
    from claude_folder_handler.core.pack_loader import _template_root

    skill = _template_root() / "claude" / "skills" / "commit" / "SKILL.md"
    warnings = lint_file(skill)
    assert warnings == [], f"baseline commit skill should be lint-clean: {warnings}"
