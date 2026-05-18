"""Test the bash command parser used by deny hooks."""

from __future__ import annotations

from pathlib import Path
import sys

# Make the hook lib importable in tests.
_LIB = Path(__file__).resolve().parents[1] / "src" / "claude_folder_handler" / "data" / "template" / "claude" / "hooks" / "lib"
sys.path.insert(0, str(_LIB))

from bash_parse import (  # noqa: E402
    all_clauses,
    collect_argv_with_inherited_env,
    has_flag,
    split_compound,
)


def test_split_compound_handles_semicolons():
    assert split_compound("a; b; c") == ["a", "b", "c"]


def test_split_compound_handles_pipes_and_and():
    assert split_compound("a | b && c || d") == ["a", "b", "c", "d"]


def test_assignment_then_dereference():
    # F=.env; cat $F
    expanded = collect_argv_with_inherited_env("F=.env; cat $F")
    # The first clause is the assignment; the second is `cat .env` after expansion.
    args = [argv for _, argv in expanded]
    assert ("cat", ".env") in [a for a in args]


def test_has_flag_short_and_long():
    cl = all_clauses("rm -rf /tmp")[0]
    assert has_flag(cl.argv, "-r", "--recursive")
    assert has_flag(cl.argv, "-f", "--force")


def test_has_flag_bundled_shorts():
    cl = all_clauses("rm -rf /tmp")[0]
    # `-rf` should match both -r and -f.
    assert has_flag(cl.argv, "-r")
    assert has_flag(cl.argv, "-f")


def test_has_flag_reverse_order_bundle():
    cl = all_clauses("rm -fr /tmp")[0]
    assert has_flag(cl.argv, "-r")
    assert has_flag(cl.argv, "-f")


def test_has_flag_long_with_value():
    cl = all_clauses("git push --force=true origin main")[0]
    assert has_flag(cl.argv, "--force")
