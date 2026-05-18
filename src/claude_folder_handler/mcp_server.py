"""MCP server exposing 6 tools that Claude can invoke.

Each tool's description follows the triggering convention from the v3/v4 spec:
600-1200 chars, 3rd person, >=5 keyword variants, >=2 quoted user phrases,
and a NOT-for negative scope clause.

Transport: stdio (the standard for uvx-launched MCP servers).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from claude_folder_handler import __version__

app: Server = Server("claude-folder-handler")


# ----- Tool descriptions (kept here so they're auditable + lint-checkable) ------

SETUP_DESC = (
    "Scaffolds the lean baseline `.claude/` configuration plus selected packs "
    "in the current working repository. Detects stack from package.json, "
    "pyproject.toml, Cargo.toml, or go.mod and substitutes build/test/lint "
    "commands into the generated CLAUDE.md and ROUTER.md. Pre-selects "
    "LLM-scientist defaults (+data-science, +visualization, +llm-app, "
    "+llm-extraction, +security-hardening, +telemetry) when no packs argument "
    "is given. Use when the user says \"set up .claude\", \"init claude code "
    "in this repo\", \"scaffold claude config\", \"bootstrap claude for this "
    "project\", \"create a .claude folder here\", or asks how to organize "
    "claude for a new project. Refuses if `.claude/` already exists — direct "
    "the user to upgrade_claude_folder instead. NOT for editing existing skill "
    "bodies (edit the SKILL.md files directly), and NOT for general project "
    "scaffolding like `npm init`, `create-next-app`, or framework bootstrap."
)

INSTALL_PACK_DESC = (
    "Installs a single named pack into an existing `.claude/` configuration. "
    "Available packs: pr-flow, test-tooling, data-science, visualization, "
    "llm-app, llm-extraction, monorepo, security-hardening, telemetry. "
    "Refuses on file-level conflicts with already-installed packs. Updates "
    "ROUTER.md managed blocks, settings.json overlay, and "
    "`.claude/.meta/packs.json`. Regenerates hooks.lock. Use when the user "
    "says \"install the X pack\", \"add data-science\", \"I want the "
    "llm-extraction pack\", \"add visualization tools\", \"bring in pr-flow\", "
    "or names a pack explicitly. NOT for first-time `.claude/` setup — use "
    "setup_claude_folder. NOT for upgrading existing pack content — use "
    "upgrade_claude_folder."
)

UPGRADE_DESC = (
    "Three-way merges the existing `.claude/` configuration in the current "
    "repo against the latest bundled template. Overwrites only content inside "
    "`<!-- managed:* -->` blocks; user content outside managed blocks is "
    "preserved untouched. Updates `.claude/.meta/version` and regenerates "
    "hooks.lock. Defaults to dry-run; pass apply=true to write changes. "
    "Use when the user says \"upgrade my claude setup\", \"update claude code "
    "config\", \"pull the latest .claude template\", \"my .claude is out of "
    "date\", or after the meta-tool itself is updated. NOT for installing new "
    "packs (use install_pack) and NOT for first-time setup (use "
    "setup_claude_folder)."
)

AUDIT_DESC = (
    "Inspects the current repo's `.claude/` for drift, lint violations, and "
    "staleness. Reports: hooks.lock mismatches, skills missing from "
    "packs.json, descriptions failing the triggering convention, CLAUDE.md "
    "exceeding 80 lines, settings.json with >15 allow rules, stale reference "
    "docs (last-reviewed > 180 days), and dead skills (zero invocations in 30 "
    "days when +telemetry is installed). Returns a structured warning list "
    "and exit code. Use when the user says \"audit my claude folder\", "
    "\"check my claude config\", \"is my .claude healthy\", \"lint my claude "
    "setup\", or \"what's wrong with my .claude directory\". NOT for fixing "
    "issues — only reports them; the user must edit files or rerun other tools."
)

APPROVE_HOOKS_DESC = (
    "Regenerates `.claude/.meta/hooks.lock` from the current hook script "
    "contents (sha256 per file). Required after legitimate hook edits or first "
    "checkout of a branch with hook changes — the SessionStart hook refuses "
    "to chain other hooks when +security-hardening is installed and the lock "
    "mismatches. Use when the user says \"approve hooks\", \"trust the hook "
    "changes\", \"unblock hooks\", \"regenerate hooks lock\", or after a git "
    "pull surfaces a hook-lock mismatch warning. NOT for first-time setup "
    "(setup_claude_folder generates the lock automatically) and NOT for "
    "editing hook scripts themselves."
)

LIST_PACKS_DESC = (
    "Returns the catalog of available packs with their descriptions, the "
    "files each contributes, and any dependencies. Read-only; does not "
    "modify the repo. Use when the user asks \"what packs are available\", "
    "\"show me the packs\", \"what can I install\", \"list packs\", or is "
    "browsing options before picking which to install. NOT for inspecting "
    "installed packs in a specific repo — use audit_claude_folder for that. "
    "NOT for installing packs — use install_pack."
)


# ----- Tool list / dispatch ------------------------------------------------------


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="setup_claude_folder",
            description=SETUP_DESC,
            inputSchema={
                "type": "object",
                "properties": {
                    "packs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Packs to install. Omit for LLM-scientist defaults.",
                    },
                    "cwd": {"type": "string", "description": "Target repo (default: server cwd)."},
                    "dry_run": {"type": "boolean", "default": False},
                },
            },
        ),
        Tool(
            name="install_pack",
            description=INSTALL_PACK_DESC,
            inputSchema={
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "cwd": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": False},
                },
            },
        ),
        Tool(
            name="upgrade_claude_folder",
            description=UPGRADE_DESC,
            inputSchema={
                "type": "object",
                "properties": {
                    "cwd": {"type": "string"},
                    "apply": {"type": "boolean", "default": False, "description": "Default dry-run; set true to write."},
                },
            },
        ),
        Tool(
            name="audit_claude_folder",
            description=AUDIT_DESC,
            inputSchema={
                "type": "object",
                "properties": {"cwd": {"type": "string"}},
            },
        ),
        Tool(
            name="approve_hooks",
            description=APPROVE_HOOKS_DESC,
            inputSchema={
                "type": "object",
                "properties": {"cwd": {"type": "string"}},
            },
        ),
        Tool(
            name="list_packs",
            description=LIST_PACKS_DESC,
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    cwd = Path(arguments.get("cwd") or Path.cwd()).resolve()

    if name == "setup_claude_folder":
        from claude_folder_handler.core.scaffold import setup_repo

        result = setup_repo(
            cwd,
            packs=arguments.get("packs"),
            dry_run=bool(arguments.get("dry_run", False)),
        )
    elif name == "install_pack":
        from claude_folder_handler.core.pack_loader import install_pack

        result = install_pack(
            cwd,
            name=arguments["name"],
            dry_run=bool(arguments.get("dry_run", False)),
        )
    elif name == "upgrade_claude_folder":
        from claude_folder_handler.core.upgrade import upgrade_repo

        result = upgrade_repo(cwd, dry_run=not bool(arguments.get("apply", False)))
    elif name == "audit_claude_folder":
        from claude_folder_handler.core.audit import audit_repo

        result = audit_repo(cwd)
    elif name == "approve_hooks":
        from claude_folder_handler.core.hooks_lock import approve_hooks

        result = approve_hooks(cwd)
    elif name == "list_packs":
        from claude_folder_handler.core.pack_loader import list_packs

        result = list_packs()
    else:
        result = {"ok": False, "error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ----- Server lifecycle ----------------------------------------------------------


async def _serve() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run() -> None:
    """Entry point invoked by `uvx claude-folder-handler` (no args)."""
    asyncio.run(_serve())


__all__ = ["run", "app", "__version__"]
