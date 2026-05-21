"""claude-folder-handler — scaffold, upgrade, audit .claude/ folders.

Two surfaces share the same `core` logic:
  - cli:        argparse subcommands (setup, install-pack, audit, upgrade, ...)
  - mcp_server: MCP tools that Claude can invoke ("set up .claude here")
"""

from __future__ import annotations

__version__ = "0.1.2"

__all__ = ["__version__"]
