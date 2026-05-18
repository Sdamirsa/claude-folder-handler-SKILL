"""Test hooks.lock generation and verification."""

from __future__ import annotations

from pathlib import Path

from claude_folder_handler.core.hooks_lock import (
    approve_hooks,
    generate_lock,
    verify_lock,
    write_lock,
)


def _make_hooks(tmp_path: Path, files: dict[str, str]) -> Path:
    hooks_dir = tmp_path / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        (hooks_dir / name).write_text(body, encoding="utf-8")
    return hooks_dir


def test_generate_then_verify(tmp_path: Path):
    _make_hooks(tmp_path, {"00-a.py": "print('a')\n", "10-b.py": "print('b')\n"})
    write_lock(tmp_path)
    result = verify_lock(tmp_path)
    assert result["ok"], result


def test_verify_detects_mismatch(tmp_path: Path):
    hooks = _make_hooks(tmp_path, {"00-a.py": "print('a')\n"})
    write_lock(tmp_path)
    (hooks / "00-a.py").write_text("print('TAMPERED')\n", encoding="utf-8")
    result = verify_lock(tmp_path)
    assert not result["ok"]
    assert "00-a.py" in result["mismatches"]


def test_verify_detects_extra_file(tmp_path: Path):
    _make_hooks(tmp_path, {"00-a.py": "x"})
    write_lock(tmp_path)
    (tmp_path / ".claude" / "hooks" / "20-new.py").write_text("y", encoding="utf-8")
    result = verify_lock(tmp_path)
    assert "20-new.py" in result["extra"]


def test_verify_detects_missing_file(tmp_path: Path):
    _make_hooks(tmp_path, {"00-a.py": "x", "10-b.py": "y"})
    write_lock(tmp_path)
    (tmp_path / ".claude" / "hooks" / "10-b.py").unlink()
    result = verify_lock(tmp_path)
    assert "10-b.py" in result["missing"]


def test_missing_lock_reported(tmp_path: Path):
    _make_hooks(tmp_path, {"00-a.py": "x"})
    result = verify_lock(tmp_path)
    assert not result["ok"]
    assert result["missing_lock"]


def test_approve_hooks_regenerates_lock(tmp_path: Path):
    _make_hooks(tmp_path, {"00-a.py": "v1"})
    write_lock(tmp_path)
    (tmp_path / ".claude" / "hooks" / "00-a.py").write_text("v2", encoding="utf-8")
    assert not verify_lock(tmp_path)["ok"]
    approve_hooks(tmp_path)
    assert verify_lock(tmp_path)["ok"]


def test_excludes_lib_dir(tmp_path: Path):
    _make_hooks(tmp_path, {"00-a.py": "x"})
    lib = tmp_path / ".claude" / "hooks" / "lib"
    lib.mkdir()
    (lib / "helper.py").write_text("y", encoding="utf-8")
    lock = generate_lock(tmp_path)
    assert "00-a.py" in lock["files"]
    assert all("/" not in k for k in lock["files"])
