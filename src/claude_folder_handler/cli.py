"""CLI entrypoint.

Subcommands (all delegate to `core` modules):
  setup            scaffold .claude/ in cwd
  install-pack     install one named pack
  upgrade          three-way merge against latest template
  audit            drift + lint + stale checks
  approve-hooks    regenerate hooks.lock
  list-packs       print pack catalog
  print-mcp-config print the JSON block to add to ~/.claude/settings.json
  mcp              run as MCP server on stdio (default when no args)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from claude_folder_handler import __version__


def _cmd_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return 0


def _cmd_setup(args: argparse.Namespace) -> int:
    from claude_folder_handler.core.scaffold import setup_repo

    cwd = Path(args.cwd or Path.cwd()).resolve()
    packs = args.packs or None  # None → use defaults
    result = setup_repo(cwd, packs=packs, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def _cmd_install_pack(args: argparse.Namespace) -> int:
    from claude_folder_handler.core.pack_loader import install_pack

    cwd = Path(args.cwd or Path.cwd()).resolve()
    result = install_pack(cwd, name=args.name, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def _cmd_upgrade(args: argparse.Namespace) -> int:
    from claude_folder_handler.core.upgrade import upgrade_repo

    cwd = Path(args.cwd or Path.cwd()).resolve()
    result = upgrade_repo(cwd, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def _cmd_audit(args: argparse.Namespace) -> int:
    from claude_folder_handler.core.audit import audit_repo

    cwd = Path(args.cwd or Path.cwd()).resolve()
    result = audit_repo(cwd)
    print(json.dumps(result, indent=2))
    # Exit 0 on clean, 2 on warnings (advisory)
    return 2 if result.get("warnings") else 0


def _cmd_approve_hooks(args: argparse.Namespace) -> int:
    from claude_folder_handler.core.hooks_lock import approve_hooks

    cwd = Path(args.cwd or Path.cwd()).resolve()
    result = approve_hooks(cwd)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def _cmd_list_packs(_args: argparse.Namespace) -> int:
    from claude_folder_handler.core.pack_loader import list_packs

    catalog = list_packs()
    print(json.dumps(catalog, indent=2))
    return 0


def _cmd_print_mcp_config(_args: argparse.Namespace) -> int:
    config = {
        "mcpServers": {
            "claude-folder-handler": {
                "command": "uvx",
                "args": ["claude-folder-handler@latest"],
            }
        }
    }
    print(json.dumps(config, indent=2))
    return 0


def _cmd_mcp(_args: argparse.Namespace) -> int:
    """Run as MCP server (stdio transport)."""
    from claude_folder_handler.mcp_server import run

    run()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claude-folder-handler",
        description=(
            "Scaffold, upgrade, and audit .claude/ folders for coding repos. "
            "With no subcommand, runs as an MCP server on stdio."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="cmd")

    p_setup = sub.add_parser("setup", help="scaffold .claude/ in current repo")
    p_setup.add_argument("--cwd", help="target repo (default: current directory)")
    p_setup.add_argument(
        "--packs",
        nargs="*",
        help="packs to install; omit for LLM-scientist defaults",
    )
    p_setup.add_argument("--dry-run", action="store_true", help="print plan without writing")
    p_setup.set_defaults(func=_cmd_setup)

    p_install = sub.add_parser("install-pack", help="install a single pack")
    p_install.add_argument("name", help="pack name (see list-packs)")
    p_install.add_argument("--cwd", help="target repo (default: current directory)")
    p_install.add_argument("--dry-run", action="store_true")
    p_install.set_defaults(func=_cmd_install_pack)

    p_upgrade = sub.add_parser("upgrade", help="three-way merge against latest template")
    p_upgrade.add_argument("--cwd", help="target repo (default: current directory)")
    p_upgrade.add_argument("--dry-run", action="store_true", default=True)
    p_upgrade.add_argument(
        "--apply", dest="dry_run", action="store_false", help="apply the merge (overrides --dry-run default)"
    )
    p_upgrade.set_defaults(func=_cmd_upgrade)

    p_audit = sub.add_parser("audit", help="drift + lint + stale checks")
    p_audit.add_argument("--cwd", help="target repo (default: current directory)")
    p_audit.set_defaults(func=_cmd_audit)

    p_approve = sub.add_parser("approve-hooks", help="regenerate hooks.lock")
    p_approve.add_argument("--cwd", help="target repo (default: current directory)")
    p_approve.set_defaults(func=_cmd_approve_hooks)

    p_list = sub.add_parser("list-packs", help="print pack catalog")
    p_list.set_defaults(func=_cmd_list_packs)

    p_config = sub.add_parser("print-mcp-config", help="print the MCP config block to add to ~/.claude/settings.json")
    p_config.set_defaults(func=_cmd_print_mcp_config)

    p_mcp = sub.add_parser("mcp", help="run as MCP server (stdio transport)")
    p_mcp.set_defaults(func=_cmd_mcp)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd is None:
        # No subcommand → behave as MCP server (this is the uvx entry-point default).
        return _cmd_mcp(args)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
