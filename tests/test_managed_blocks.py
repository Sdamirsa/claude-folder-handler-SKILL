"""Test managed-block insert/replace round-trips."""

from __future__ import annotations

import json

from claude_folder_handler.core.managed_blocks import (
    HASH,
    MARKDOWN,
    deep_merge_settings,
    list_blocks,
    remove_block,
    render_settings,
    replace_block,
)


def test_insert_markdown_block_when_absent():
    text = "# Title\n\nsome body\n"
    out = replace_block(text, "pack-foo", "row 1\nrow 2", MARKDOWN)
    assert "<!-- managed:pack-foo -->" in out
    assert "<!-- /managed:pack-foo -->" in out
    assert "row 1" in out
    assert "row 2" in out


def test_replace_existing_markdown_block():
    text = (
        "# Title\n\n"
        "<!-- managed:pack-foo -->\nold content\n<!-- /managed:pack-foo -->\n"
    )
    out = replace_block(text, "pack-foo", "new content", MARKDOWN)
    assert "old content" not in out
    assert "new content" in out
    assert out.count("<!-- managed:pack-foo -->") == 1


def test_idempotent_replace():
    text = "<!-- managed:x -->\nbody\n<!-- /managed:x -->\n"
    out1 = replace_block(text, "x", "body", MARKDOWN)
    out2 = replace_block(out1, "x", "body", MARKDOWN)
    assert out1 == out2


def test_remove_block():
    text = "before\n<!-- managed:y -->\nfoo\n<!-- /managed:y -->\nafter\n"
    out = remove_block(text, "y", MARKDOWN)
    assert "foo" not in out
    assert "before" in out and "after" in out


def test_list_blocks():
    text = (
        "<!-- managed:a -->\n1\n<!-- /managed:a -->\n"
        "<!-- managed:b -->\n2\n<!-- /managed:b -->\n"
        "<!-- managed:a -->\n1again\n<!-- /managed:a -->\n"
    )
    assert list_blocks(text, MARKDOWN) == ["a", "b"]


def test_hash_marker_for_gitignore():
    text = "# project ignores\n*.log\n"
    out = replace_block(text, "claude-folder-handler", ".claude/settings.local.json", HASH)
    assert "# managed:claude-folder-handler" in out
    assert "# /managed:claude-folder-handler" in out
    assert ".claude/settings.local.json" in out


def test_deep_merge_settings_lists_dedupe():
    base = {"permissions": {"deny": ["a", "b"], "ask": ["x"]}}
    overlay = {"permissions": {"deny": ["b", "c"]}}
    out = deep_merge_settings(base, overlay)
    assert out["permissions"]["deny"] == ["a", "b", "c"]
    assert out["permissions"]["ask"] == ["x"]


def test_deep_merge_settings_dict_recurses():
    base = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": []}]}}
    overlay = {"hooks": {"Stop": [{"matcher": ""}]}}
    out = deep_merge_settings(base, overlay)
    assert "PreToolUse" in out["hooks"]
    assert "Stop" in out["hooks"]


def test_render_settings_is_stable():
    s = {"a": 1, "b": [1, 2, 3]}
    out = render_settings(s)
    assert json.loads(out) == s
    assert out.endswith("\n")
