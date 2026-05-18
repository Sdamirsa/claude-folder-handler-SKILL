# MCP setup & troubleshooting

## Install (one block)

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "claude-folder-handler": {
      "command": "uvx",
      "args": ["claude-folder-handler@latest"]
    }
  }
}
```

Restart Claude Code. The server starts on stdio next session.

## Verify it loaded

1. Open a fresh Claude Code session.
2. Ask: *"what packs are available in claude-folder-handler?"*
3. Claude should invoke the `list_packs` MCP tool and print the catalog.

If nothing happens, `uvx` may not be on PATH for the Claude Code process.
See **Troubleshooting** below.

## Version pinning

| Pattern | Behavior |
|---|---|
| `claude-folder-handler@latest` | Whatever's newest on PyPI; uvx caches; refresh manually |
| `claude-folder-handler@0.1.0` | Pinned semver |
| `claude-folder-handler>=0.1,<0.2` | Range |
| `--from git+https://github.com/Sdamirsa/claude-folder-handler-SKILL@main claude-folder-handler` | Bleeding edge from git |
| `--from git+https://github.com/Sdamirsa/claude-folder-handler-SKILL@v0.1.0 claude-folder-handler` | Pinned to a git tag |

## Refresh after a new release

```bash
uvx --refresh claude-folder-handler --version
```

Or pin to the new version in your `mcpServers` config.

## Per-repo install

If you only want the tool active in some repos, add the block to that repo's
`.mcp.json` instead of `~/.claude/settings.json`. (Note: `.mcp.json` is in the
template's default `.gitignore`.)

## Six tools the server exposes

| Tool | Triggered by phrases like |
|---|---|
| `setup_claude_folder` | "set up .claude here", "scaffold claude config", "init claude code" |
| `install_pack` | "install the data-science pack", "add llm-extraction" |
| `upgrade_claude_folder` | "upgrade my claude setup", "pull the latest .claude template" |
| `audit_claude_folder` | "audit my claude folder", "what's wrong with my .claude" |
| `approve_hooks` | "approve hooks", "trust hook changes" |
| `list_packs` | "what packs are available", "list packs" |

All tool descriptions follow the [triggering convention](triggering-convention.md)
so Claude reliably picks the right tool from the user's natural language.

## CLI alternative

Same tool, no MCP wiring:

```bash
uvx claude-folder-handler setup
uvx claude-folder-handler install-pack data-science
uvx claude-folder-handler audit
uvx claude-folder-handler upgrade --apply
uvx claude-folder-handler list-packs
uvx claude-folder-handler approve-hooks
```

Or install persistently:

```bash
uv tool install claude-folder-handler
claude-folder-handler --version
```

## Troubleshooting

### `uvx: command not found`

Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `brew install uv`).

### MCP server doesn't show up in Claude Code

1. Run `uvx claude-folder-handler --version` in a terminal — confirm it works there.
2. Check `~/.claude/settings.json` is valid JSON: `python -m json.tool ~/.claude/settings.json`
3. Restart Claude Code completely (not just the session).
4. Check Claude Code's MCP log — typically `~/.claude/logs/mcp.log`.

### "Tool failed: bundled template not found"

The wheel was built without `data/` included. Force a fresh install:

```bash
uvx --refresh --no-cache claude-folder-handler --version
```

### Stale cached version

```bash
uvx cache clean
uvx --refresh claude-folder-handler --version
```

### Pre-publish bootstrap

Until `v0.1.0` lands on PyPI, point uvx at the git repo:

```json
"args": [
  "--from",
  "git+https://github.com/Sdamirsa/claude-folder-handler-SKILL@main",
  "claude-folder-handler"
]
```

## Uninstall

1. Remove the block from `~/.claude/settings.json`.
2. (Optional) `uvx cache clean`.
3. (Optional) `uv tool uninstall claude-folder-handler` if you used `uv tool install`.

The tool is stateless — no `~/.claude/skills/` install to clean up.
