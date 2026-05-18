"""Parse and replace `<!-- managed:NAME -->...<!-- /managed:NAME -->` regions.

Used by scaffold / install_pack / upgrade to insert content into ROUTER.md,
settings.json, .gitignore, etc. while preserving user content outside the
managed regions.

The block markers are language-agnostic; we choose the comment style per file:
  - markdown / html:  <!-- managed:X --> ... <!-- /managed:X -->
  - json:             /* managed:X */ ... /* /managed:X */   (only valid in JSONC)
  - shell / .gitignore / .python: # managed:X ... # /managed:X

settings.json uses JSONC-style markers; we tolerate them as a side-channel
because Claude Code accepts JSONC. For strict JSON we instead overlay via
key-set merge (see `apply_settings_overlay`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable


# ----- Markdown / HTML / .gitignore via comment markers ------------------------


@dataclass(frozen=True)
class BlockMarker:
    """Comment-style markers for a given file format."""

    open_template: str  # e.g. "<!-- managed:{name} -->"
    close_template: str  # e.g. "<!-- /managed:{name} -->"

    def open(self, name: str) -> str:
        return self.open_template.format(name=name)

    def close(self, name: str) -> str:
        return self.close_template.format(name=name)

    def pattern(self, name: str) -> re.Pattern[str]:
        return re.compile(
            re.escape(self.open(name)) + r"(?P<body>.*?)" + re.escape(self.close(name)),
            re.DOTALL,
        )


MARKDOWN = BlockMarker("<!-- managed:{name} -->", "<!-- /managed:{name} -->")
HASH = BlockMarker("# managed:{name}", "# /managed:{name}")


def replace_block(text: str, name: str, body: str, marker: BlockMarker = MARKDOWN) -> str:
    """Replace the contents of a named managed block. Inserts the block if absent.

    The returned text always contains the block; appending if not found.
    """
    pat = marker.pattern(name)
    replacement_body = body.strip("\n")
    replacement = f"{marker.open(name)}\n{replacement_body}\n{marker.close(name)}" if replacement_body else f"{marker.open(name)}\n{marker.close(name)}"

    if pat.search(text):
        return pat.sub(lambda _: replacement, text)

    # Not present — append (with a leading newline if file is non-empty).
    sep = "\n\n" if text.strip() else ""
    return text + sep + replacement + "\n"


def list_blocks(text: str, marker: BlockMarker = MARKDOWN) -> list[str]:
    """Return the names of managed blocks found in text."""
    pat = re.compile(
        re.escape(marker.open_template.format(name="")).replace("", "")
        + r"<!-- managed:([a-zA-Z0-9_\-./]+) -->",
        re.DOTALL,
    )
    # Simpler: match the open marker directly.
    open_pat = re.compile(r"<!-- managed:([a-zA-Z0-9_\-./]+) -->") if marker is MARKDOWN else re.compile(r"# managed:([a-zA-Z0-9_\-./]+)")
    return list(dict.fromkeys(open_pat.findall(text)))  # preserve order, dedupe


def remove_block(text: str, name: str, marker: BlockMarker = MARKDOWN) -> str:
    """Remove a named managed block entirely (including markers)."""
    pat = re.compile(
        re.escape(marker.open(name)) + r".*?" + re.escape(marker.close(name)) + r"\n?",
        re.DOTALL,
    )
    return pat.sub("", text)


# ----- settings.json overlay merge ---------------------------------------------
#
# We merge a pack's settings.json overlay into the project's settings.json by:
# 1. Reading the existing settings.json.
# 2. For each top-level key in the overlay, deep-merging lists (concat + dedupe)
#    and merging dicts. We track ownership via a "_managed" comment-like field
#    isn't possible in strict JSON; instead we keep a sidecar
#    `.claude/.meta/packs.json` describing which entries came from which pack.


def deep_merge_settings(base: dict, overlay: dict) -> dict:
    """Merge overlay into a copy of base. Lists concat+dedupe; dicts recursive merge."""
    out: dict = json.loads(json.dumps(base))  # cheap deep copy
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge_settings(out[k], v)
        elif k in out and isinstance(out[k], list) and isinstance(v, list):
            seen = set()
            merged: list = []
            for item in [*out[k], *v]:
                key = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
            out[k] = merged
        else:
            out[k] = v
    return out


def render_settings(settings: dict) -> str:
    """Render settings.json with stable 2-space indent and a trailing newline."""
    return json.dumps(settings, indent=2) + "\n"


__all__ = [
    "BlockMarker",
    "MARKDOWN",
    "HASH",
    "replace_block",
    "remove_block",
    "list_blocks",
    "deep_merge_settings",
    "render_settings",
]
