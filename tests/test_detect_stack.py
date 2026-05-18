"""Test stack detection across language ecosystems."""

from __future__ import annotations

from pathlib import Path

from claude_folder_handler.core.detect_stack import detect_stack


def test_detects_python(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "myproj"\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
        encoding="utf-8",
    )
    stack = detect_stack(tmp_path)
    assert "python" in stack["languages"]
    assert stack["project_name"] == "myproj"


def test_detects_node(tmp_path: Path):
    (tmp_path / "package.json").write_text(
        '{"name":"my-app","scripts":{"test":"jest","build":"vite build","lint":"eslint ."}}',
        encoding="utf-8",
    )
    stack = detect_stack(tmp_path)
    assert "node" in stack["languages"]
    assert stack["project_name"] == "my-app"
    assert stack["test"] == "npm test"
    assert stack["build"] == "npm run build"


def test_detects_rust(tmp_path: Path):
    (tmp_path / "Cargo.toml").write_text(
        '[package]\nname = "rusty"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    stack = detect_stack(tmp_path)
    assert "rust" in stack["languages"]
    assert stack["project_name"] == "rusty"
    assert stack["test"] == "cargo test"


def test_detects_go(tmp_path: Path):
    (tmp_path / "go.mod").write_text("module example.com/foo\n\ngo 1.22\n", encoding="utf-8")
    stack = detect_stack(tmp_path)
    assert "go" in stack["languages"]
    assert stack["build"] == "go build ./..."


def test_detects_polyglot(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name":"front"}', encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "back"\n', encoding="utf-8"
    )
    stack = detect_stack(tmp_path)
    assert set(stack["languages"]) >= {"node", "python"}


def test_unknown_falls_back_to_dirname(tmp_path: Path):
    stack = detect_stack(tmp_path)
    assert stack["languages"] == []
    assert stack["project_name"] == tmp_path.name
