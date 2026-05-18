"""Detect the project's language/stack from marker files.

Returns a dict with keys: languages, build, test, lint, project_name.
Multi-language repos are supported (returns all detected languages).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


MARKERS: dict[str, list[str]] = {
    "python": ["pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Pipfile"],
    "node": ["package.json"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
    "ruby": ["Gemfile"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
}


def detect_stack(cwd: Path) -> dict[str, object]:
    """Inspect cwd for known marker files; return a normalized stack descriptor."""
    cwd = Path(cwd).resolve()
    languages = [lang for lang, files in MARKERS.items() if any((cwd / f).exists() for f in files)]

    project_name = _detect_project_name(cwd, languages)
    build, test, lint = _detect_commands(cwd, languages)

    return {
        "cwd": str(cwd),
        "languages": languages,
        "project_name": project_name,
        "build": build,
        "test": test,
        "lint": lint,
    }


def _detect_project_name(cwd: Path, languages: list[str]) -> str:
    """Try to extract a human-readable project name from manifest files."""
    if "node" in languages:
        pkg = cwd / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                name = data.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
            except (json.JSONDecodeError, OSError):
                pass

    if "python" in languages:
        pyp = cwd / "pyproject.toml"
        if pyp.exists():
            try:
                data = tomllib.loads(pyp.read_text(encoding="utf-8"))
                name = data.get("project", {}).get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
            except (tomllib.TOMLDecodeError, OSError):
                pass

    if "rust" in languages:
        cargo = cwd / "Cargo.toml"
        if cargo.exists():
            try:
                data = tomllib.loads(cargo.read_text(encoding="utf-8"))
                name = data.get("package", {}).get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
            except (tomllib.TOMLDecodeError, OSError):
                pass

    return cwd.name


def _detect_commands(cwd: Path, languages: list[str]) -> tuple[str, str, str]:
    """Return (build, test, lint) commands as user-facing strings."""
    build = test = lint = "TODO: fill in"

    if "node" in languages:
        pkg = cwd / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                scripts = data.get("scripts", {}) or {}
                if "build" in scripts:
                    build = "npm run build"
                if "test" in scripts:
                    test = "npm test"
                if "lint" in scripts:
                    lint = "npm run lint"
            except (json.JSONDecodeError, OSError):
                pass

    if "python" in languages:
        # Heuristics — let user override later
        if (cwd / "pyproject.toml").exists():
            content = ""
            try:
                content = (cwd / "pyproject.toml").read_text(encoding="utf-8")
            except OSError:
                pass
            if re.search(r"\b(pytest|tool\.pytest)\b", content):
                test = "uv run pytest" if "uv" in content else "pytest"
            if re.search(r"\bruff\b", content):
                lint = "ruff check ."
            elif re.search(r"\bflake8\b", content):
                lint = "flake8 ."
            if build == "TODO: fill in":
                build = "uv build" if "uv" in content else "python -m build"

    if "rust" in languages:
        build, test, lint = "cargo build", "cargo test", "cargo clippy"

    if "go" in languages:
        build, test, lint = "go build ./...", "go test ./...", "go vet ./..."

    return build, test, lint
