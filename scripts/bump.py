"""Version bumper for claude-folder-handler.

Usage:
    python scripts/bump.py <version>           # e.g. 0.2.0, 0.2.0-rc1
    python scripts/bump.py {patch|minor|major}

Effects (in order, all-or-nothing):
  1. Refuse if working tree dirty (use --allow-dirty to override).
  2. Refuse if current branch is not main (use --allow-branch X).
  3. Refuse if CHANGELOG.md [Unreleased] section is empty.
  4. Bump version in pyproject.toml and src/claude_folder_handler/__init__.py.
  5. Promote CHANGELOG [Unreleased] → [<version>] — <YYYY-MM-DD>;
     add a fresh empty [Unreleased] at top.
  6. Commit with message `chore: release v<version>`.
  7. Tag with `v<version>`.
  8. Print next-step `git push --tags` command (NEVER pushes automatically).

The release GitHub Action fires on the tag push.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
INIT_PY = ROOT / "src" / "claude_folder_handler" / "__init__.py"
CHANGELOG = ROOT / "CHANGELOG.md"

SEMVER_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?$"
)


def _read_current_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        sys.exit("ERROR: could not find version in pyproject.toml")
    return m.group(1)


def _resolve_target_version(arg: str, current: str) -> str:
    if arg in {"patch", "minor", "major"}:
        m = SEMVER_RE.match(current)
        if not m:
            sys.exit(f"ERROR: current version {current!r} is not strict semver; "
                     "specify the new version explicitly")
        major, minor, patch = int(m["major"]), int(m["minor"]), int(m["patch"])
        if arg == "patch":
            patch += 1
        elif arg == "minor":
            minor += 1
            patch = 0
        else:  # major
            major += 1
            minor = 0
            patch = 0
        return f"{major}.{minor}.{patch}"
    if not SEMVER_RE.match(arg):
        sys.exit(f"ERROR: {arg!r} is not a valid semver "
                 "(expected MAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH-PRERELEASE)")
    return arg


def _git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if check and result.returncode != 0:
        sys.exit(f"ERROR: git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def _ensure_clean_tree(allow_dirty: bool) -> None:
    status = _git("status", "--porcelain")
    if status and not allow_dirty:
        sys.exit("ERROR: working tree dirty — commit or stash, or pass --allow-dirty.\n"
                 + status)


def _ensure_branch(allow_branch: str | None) -> None:
    if allow_branch is None:
        return
    current = _git("rev-parse", "--abbrev-ref", "HEAD")
    if current != allow_branch:
        sys.exit(f"ERROR: on branch {current!r}; expected {allow_branch!r}. "
                 "Pass --allow-branch <name> to override.")


def _bump_pyproject(new_version: str) -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    new_text, n = re.subn(
        r'^(version\s*=\s*)"[^"]+"',
        rf'\1"{new_version}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        sys.exit("ERROR: could not bump version in pyproject.toml")
    PYPROJECT.write_text(new_text, encoding="utf-8")


def _bump_init(new_version: str) -> None:
    text = INIT_PY.read_text(encoding="utf-8")
    new_text, n = re.subn(
        r'__version__\s*=\s*"[^"]+"',
        f'__version__ = "{new_version}"',
        text,
        count=1,
    )
    if n != 1:
        sys.exit("ERROR: could not bump __version__ in src/claude_folder_handler/__init__.py")
    INIT_PY.write_text(new_text, encoding="utf-8")


def _promote_changelog(new_version: str) -> None:
    text = CHANGELOG.read_text(encoding="utf-8")

    # Find the [Unreleased] section.
    m = re.search(r"^## \[Unreleased\]\s*$", text, re.MULTILINE)
    if not m:
        sys.exit("ERROR: CHANGELOG.md missing [Unreleased] section")

    # The body of [Unreleased] is everything until the next `## [` heading.
    start = m.end()
    next_section = re.search(r"^## \[", text[start:], re.MULTILINE)
    end = start + next_section.start() if next_section else len(text)
    body = text[start:end].strip()

    if not body:
        sys.exit(
            "ERROR: [Unreleased] section is empty. Add notes under it before bumping.\n"
            "  (Edit CHANGELOG.md and put entries under '## [Unreleased]'.)"
        )

    today = date.today().isoformat()
    replacement = (
        f"## [Unreleased]\n\n## [{new_version}] — {today}\n\n{body}\n\n"
    )
    new_text = text[:m.start()] + replacement + text[end:]

    # Update / insert the compare links at the bottom.
    repo = "https://github.com/Sdamirsa/claude-folder-handler-SKILL"
    link_block = re.search(
        r"\n\[Unreleased\]:.*?(?=\n##|\Z)",
        new_text,
        re.DOTALL,
    )
    if link_block:
        # Find previous version's tag (whatever the existing [Unreleased] pointed to).
        old_compare = re.search(r"\[Unreleased\]:\s*(\S+)", new_text)
        prev_tag = "v0.1.0"
        if old_compare:
            # Extract the start of the compare range
            ref = old_compare.group(1)
            m2 = re.search(r"/compare/(\S+?)\.\.\.", ref)
            if m2:
                prev_tag = m2.group(1)
        new_links = (
            f"[Unreleased]: {repo}/compare/v{new_version}...HEAD\n"
            f"[{new_version}]: {repo}/compare/{prev_tag}...v{new_version}\n"
        )
        # Replace [Unreleased] line and insert [<version>] line; keep other version links.
        new_text = re.sub(
            r"\[Unreleased\]:.*\n",
            new_links,
            new_text,
            count=1,
        )

    CHANGELOG.write_text(new_text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bump version, promote CHANGELOG, commit, tag.")
    parser.add_argument("target", help="new version (e.g. 0.2.0) or 'patch'/'minor'/'major'")
    parser.add_argument("--allow-dirty", action="store_true", help="skip clean-tree check")
    parser.add_argument(
        "--allow-branch",
        default="main",
        help="required current branch (default: main; pass empty string to skip)",
    )
    parser.add_argument("--dry-run", action="store_true", help="print actions; don't write/commit")
    parser.add_argument("--no-commit", action="store_true", help="write files but skip commit + tag")
    args = parser.parse_args(argv)

    current = _read_current_version()
    new_version = _resolve_target_version(args.target, current)

    if new_version == current and not args.dry_run:
        sys.exit(f"ERROR: target version {new_version} equals current {current}")

    branch_required = args.allow_branch if args.allow_branch else None

    print(f"Current version: {current}")
    print(f"Target version:  {new_version}")

    if args.dry_run:
        print("(dry run — not modifying files)")
        return 0

    _ensure_clean_tree(args.allow_dirty)
    _ensure_branch(branch_required)

    _bump_pyproject(new_version)
    _bump_init(new_version)
    _promote_changelog(new_version)

    if args.no_commit:
        print(f"✓ Files updated. Skipping commit + tag (--no-commit).")
        return 0

    _git("add", "pyproject.toml", "src/claude_folder_handler/__init__.py", "CHANGELOG.md")
    _git("commit", "-m", f"chore: release v{new_version}")
    _git("tag", "-a", f"v{new_version}", "-m", f"v{new_version}")

    print()
    print(f"✓ Bumped to v{new_version}; committed and tagged.")
    print(f"  Push to trigger the release workflow:")
    print(f"    git push origin {args.allow_branch or 'HEAD'} --tags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
