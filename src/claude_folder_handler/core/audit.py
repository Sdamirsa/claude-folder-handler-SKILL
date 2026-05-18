"""Audit a target repo's .claude/ for drift, lint warnings, and staleness."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from claude_folder_handler.core.description_lint import lint_file
from claude_folder_handler.core.hooks_lock import verify_lock


LAST_REVIEWED_RE = re.compile(r"<!--\s*last-reviewed:\s*(\d{4}-\d{2}-\d{2})\s*-->")
STALE_REFERENCE_DAYS = 180
CLAUDE_MD_MAX_LINES = 80
ALLOW_RULES_SOFT_CAP = 15


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def audit_repo(cwd: Path) -> dict:
    cwd = Path(cwd).resolve()
    claude_dir = cwd / ".claude"
    if not claude_dir.is_dir():
        return {
            "ok": False,
            "error": f"No .claude/ at {cwd}. Run setup first.",
            "warnings": [],
        }

    warnings: list[dict] = []

    # --- 1. Hooks lock drift ---
    lock = verify_lock(cwd)
    if not lock["ok"]:
        if lock.get("missing_lock"):
            warnings.append({"category": "drift", "kind": "hooks-lock-missing"})
        if lock.get("mismatches"):
            warnings.append({
                "category": "drift",
                "kind": "hooks-lock-mismatch",
                "files": lock["mismatches"],
            })
        if lock.get("extra"):
            warnings.append({
                "category": "drift",
                "kind": "hooks-lock-extra",
                "files": lock["extra"],
            })
        if lock.get("missing"):
            warnings.append({
                "category": "drift",
                "kind": "hooks-lock-missing-files",
                "files": lock["missing"],
            })

    # --- 2. packs.json consistency ---
    packs_state_path = claude_dir / ".meta" / "packs.json"
    installed = []
    if packs_state_path.exists():
        try:
            state = json.loads(packs_state_path.read_text(encoding="utf-8"))
            installed = state.get("installed", [])
        except json.JSONDecodeError:
            warnings.append({"category": "drift", "kind": "packs-json-invalid"})

    # --- 3. CLAUDE.md line count ---
    claude_md = cwd / "CLAUDE.md"
    if claude_md.exists():
        line_count = sum(1 for _ in _read_text(claude_md).splitlines())
        if line_count > CLAUDE_MD_MAX_LINES:
            warnings.append({
                "category": "size",
                "kind": "claude-md-too-long",
                "lines": line_count,
                "limit": CLAUDE_MD_MAX_LINES,
            })

    # --- 4. settings.json allow-rule budget ---
    settings_path = claude_dir / "settings.json"
    if settings_path.exists():
        try:
            settings = json.loads(_read_text(settings_path))
            allow = settings.get("permissions", {}).get("allow", []) or []
            if isinstance(allow, list) and len(allow) > ALLOW_RULES_SOFT_CAP:
                warnings.append({
                    "category": "size",
                    "kind": "too-many-allow-rules",
                    "count": len(allow),
                    "soft_cap": ALLOW_RULES_SOFT_CAP,
                })
        except json.JSONDecodeError:
            warnings.append({"category": "drift", "kind": "settings-json-invalid"})

    # --- 5. Description lint on all skills + agents ---
    for skill_md in (claude_dir / "skills").rglob("SKILL.md") if (claude_dir / "skills").is_dir() else []:
        msgs = lint_file(skill_md)
        if msgs:
            warnings.append({
                "category": "lint",
                "kind": "description-warnings",
                "path": str(skill_md.relative_to(cwd)),
                "messages": msgs,
            })
    if (claude_dir / "agents").is_dir():
        for agent_md in (claude_dir / "agents").glob("*.md"):
            msgs = lint_file(agent_md)
            if msgs:
                warnings.append({
                    "category": "lint",
                    "kind": "description-warnings",
                    "path": str(agent_md.relative_to(cwd)),
                    "messages": msgs,
                })

    # --- 6. Reference docs: stale (last-reviewed > 180 days) ---
    ref_dir = claude_dir / "reference"
    if ref_dir.is_dir():
        now = datetime.now(timezone.utc).date()
        for md in ref_dir.rglob("*.md"):
            text = _read_text(md)
            m = LAST_REVIEWED_RE.search(text)
            if not m:
                if md.name not in {"INDEX.md", "README.md"}:
                    warnings.append({
                        "category": "reference",
                        "kind": "missing-last-reviewed",
                        "path": str(md.relative_to(cwd)),
                    })
                continue
            try:
                dt = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            except ValueError:
                warnings.append({
                    "category": "reference",
                    "kind": "bad-last-reviewed",
                    "path": str(md.relative_to(cwd)),
                })
                continue
            age = (now - dt).days
            if age > STALE_REFERENCE_DAYS:
                warnings.append({
                    "category": "reference",
                    "kind": "stale-reference",
                    "path": str(md.relative_to(cwd)),
                    "age_days": age,
                    "threshold_days": STALE_REFERENCE_DAYS,
                })

    # --- 7. Telemetry: dead skills (if +telemetry installed) ---
    if "telemetry" in installed:
        invocations_file = claude_dir / ".cache" / "invocations.jsonl"
        if invocations_file.exists():
            # Best-effort parse: count invocations by skill name.
            counts: dict[str, int] = {}
            for line in _read_text(invocations_file).splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                name = rec.get("skill_invoked") or rec.get("agent_invoked")
                if name:
                    counts[name] = counts.get(name, 0) + 1

            for skill_md in (claude_dir / "skills").rglob("SKILL.md") if (claude_dir / "skills").is_dir() else []:
                skill_name = skill_md.parent.name
                if counts.get(skill_name, 0) == 0:
                    warnings.append({
                        "category": "telemetry",
                        "kind": "dead-skill",
                        "path": str(skill_md.relative_to(cwd)),
                    })

    return {
        "ok": True,
        "cwd": str(cwd),
        "installed_packs": installed,
        "warnings": warnings,
        "summary": _summarize(warnings),
    }


def _summarize(warnings: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for w in warnings:
        cat = w.get("category", "other")
        out[cat] = out.get(cat, 0) + 1
    out["total"] = len(warnings)
    return out


__all__ = ["audit_repo"]
