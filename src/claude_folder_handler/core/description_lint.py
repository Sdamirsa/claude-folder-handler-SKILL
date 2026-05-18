"""Lint SKILL.md / agent .md frontmatter `description` fields against the
triggering convention.

Rules (all advisory — failures produce warnings, not blocking errors):
  R1. Length: 600 <= len(description) <= 1200
  R2. Quoted phrases: >= 2 distinct `"..."` substrings
  R3. NOT-for clause: contains the literal substring "NOT for" (case-sensitive)
  R4. Third person: no leading "I " or "You " or "We "
  R5. "Use when" present somewhere
"""

from __future__ import annotations

import re
from pathlib import Path

QUOTED_PHRASE_RE = re.compile(r'"([^"]{2,})"')
PRONOUN_RE = re.compile(r"\b(I am|I will|I can|You can|You will|We will|We can)\b")


def lint_description(desc: str) -> list[str]:
    """Return a list of human-readable warning messages."""
    warnings: list[str] = []
    if not desc.strip():
        warnings.append("description is empty")
        return warnings

    length = len(desc)
    if length < 600:
        warnings.append(f"description is {length} chars; should be >=600 for reliable triggering")
    if length > 1200:
        warnings.append(f"description is {length} chars; should be <=1200 to survive truncation budget")

    quoted = QUOTED_PHRASE_RE.findall(desc)
    if len(quoted) < 2:
        warnings.append(f'expected >=2 quoted user phrases (e.g. "set up .claude"); found {len(quoted)}')

    if "NOT for" not in desc:
        warnings.append('missing "NOT for ... use X instead" negative-scope clause')

    if PRONOUN_RE.search(desc):
        warnings.append("uses first/second-person pronouns; descriptions should be third-person")

    if "Use when" not in desc:
        warnings.append('missing "Use when ..." clause naming user trigger phrases')

    return warnings


def parse_frontmatter(path: Path) -> dict[str, str] | None:
    """Extract YAML frontmatter as a flat dict of strings. None if no frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip()
    out: dict[str, str] = {}
    current_key: str | None = None
    buf: list[str] = []
    for line in block.splitlines():
        if not line:
            if current_key is not None:
                buf.append("")
            continue
        if line[0].isalpha() and ":" in line and not line.startswith(" "):
            if current_key is not None:
                out[current_key] = "\n".join(buf).strip()
            key, _, value = line.partition(":")
            current_key = key.strip()
            value = value.strip()
            if value in {"|", ">"}:
                buf = []
            else:
                buf = [value] if value else []
        else:
            if current_key is not None:
                buf.append(line.lstrip())
    if current_key is not None:
        out[current_key] = "\n".join(buf).strip()
    return out


def lint_file(path: Path) -> list[str]:
    """Lint a single SKILL.md / agent .md file. Returns warning strings."""
    try:
        fm = parse_frontmatter(path)
    except (OSError, UnicodeDecodeError) as e:
        return [f"could not read: {e}"]
    if fm is None:
        return ["no YAML frontmatter found"]
    desc = fm.get("description", "")
    return lint_description(desc)


__all__ = ["lint_description", "lint_file", "parse_frontmatter"]
