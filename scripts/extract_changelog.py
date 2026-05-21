"""Print a single version's section of CHANGELOG.md.

Used by the GitHub Actions release workflow to populate release notes.

Usage:
    python scripts/extract_changelog.py 0.2.0
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"


def extract(version: str) -> str:
    text = CHANGELOG.read_text(encoding="utf-8")
    # Match `## [<version>] — <date>` heading and capture body up to next `## [` or EOF.
    pat = re.compile(
        rf"^##\s*\[{re.escape(version)}\][^\n]*$"  # heading line
        r"\s*\n"
        r"(?P<body>.*?)"
        r"(?=^##\s*\[|\Z)",  # next heading or EOF
        re.MULTILINE | re.DOTALL,
    )
    m = pat.search(text)
    if not m:
        raise SystemExit(f"ERROR: no [{version}] section in CHANGELOG.md")
    body = m.group("body").strip()

    # Strip trailing link-reference definitions (`[Unreleased]: ...`, `[0.1.0]: ...`).
    # These live at the bottom of CHANGELOG.md and get swept into the last section
    # because there's no `## [` heading after them.
    lines = body.splitlines()
    while lines and re.match(r"^\[[^\]]+\]:\s*\S", lines[-1].strip()):
        lines.pop()
    # Also strip any blank lines exposed by removing the links.
    while lines and not lines[-1].strip():
        lines.pop()
    body = "\n".join(lines)

    # Prepend a synthesized header so the GitHub release body has top-level context.
    header = f"# v{version}\n\n"

    # Append install snippets so users see them on every release page.
    repo_root = "https://github.com/Sdamirsa/claude-folder-handler-SKILL"
    install = (
        "\n\n## Install\n\n"
        "**Claude Code (MCP):** add to `~/.claude/settings.json`\n\n"
        "```json\n"
        "{\n"
        '  "mcpServers": {\n'
        '    "claude-folder-handler": {\n'
        '      "command": "uvx",\n'
        '      "args": [\n'
        '        "--from",\n'
        f'        "git+{repo_root}@v{version}",\n'
        '        "claude-folder-handler"\n'
        "      ]\n"
        "    }\n"
        "  }\n"
        "}\n"
        "```\n\n"
        "**CLI:**\n\n"
        "```bash\n"
        f"uv tool install --from git+{repo_root}@v{version} claude-folder-handler\n"
        "```\n\n"
        "**Claude.ai (web/desktop):** download "
        f"`claude-folder-handler-skill-{version}.zip` from this release's "
        "Assets, then Settings → Skills → Add skill.\n"
    )

    return header + body + install


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    print(extract(argv[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
