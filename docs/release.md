# Releasing claude-folder-handler

## Cut a release (manual, until automated in CI)

### 1. Verify clean

```sh
git status                                # working tree clean
uv run pytest                             # all green
uv build                                  # sdist + wheel under dist/
uv run python scripts/build_skill_zip.py  # Claude.ai Skill zip under dist/
```

After this step `dist/` contains three artifacts: `*.tar.gz` (sdist),
`*.whl` (wheel), and `claude-folder-handler-skill-<version>.zip` (Claude.ai
Skill upload).

### 2. Bump version (if needed)

Edit `pyproject.toml`:

```toml
[project]
version = "0.1.0"
```

And `src/claude_folder_handler/__init__.py`:

```python
__version__ = "0.1.0"
```

(Keep them in sync. A test enforces that `--version` matches `__version__`.)

### 3. Tag

```sh
git tag -a v0.1.0 -m "v0.1.0 — initial release"
git push origin v0.1.0
```

### 4. Publish to PyPI

Prerequisites: a PyPI account, `~/.pypirc` configured (or env `PYPI_TOKEN`),
the `twine` CLI installed.

```sh
rm -rf dist && uv build
uv pip install twine
twine check dist/*
twine upload dist/*
```

Verify:

```sh
pip install claude-folder-handler==0.1.0
uvx --refresh claude-folder-handler --version
```

### 5. GitHub Release

Create a GitHub release pointing at the tag with the install snippet below
**and attach the Skill zip** so Claude.ai users can download it without
building from source:

```sh
gh release create v0.1.0 \
  dist/claude-folder-handler-skill-0.1.0.zip \
  --title "v0.1.0" \
  --notes-file - <<'EOF'
# v0.1.0 — initial release

Install for Claude Code (MCP):
\`\`\`json
{"mcpServers":{"claude-folder-handler":{"command":"uvx","args":["claude-folder-handler@0.1.0"]}}}
\`\`\`

Install for Claude.ai (web/desktop): download `claude-folder-handler-skill-0.1.0.zip`
and upload via Settings → Skills → Add skill.
EOF
```

Or do it through the GitHub UI: Releases → Draft new release → drag the
`claude-folder-handler-skill-<version>.zip` into the attachments area.

## Post-release install snippet

```json
{
  "mcpServers": {
    "claude-folder-handler": {
      "command": "uvx",
      "args": ["claude-folder-handler@0.1.0"]
    }
  }
}
```

## v0.1.0 release notes

### Initial release

`claude-folder-handler` is an MCP server + CLI that scaffolds, upgrades, and
audits `.claude/` configurations for any coding repo. Distributed via PyPI,
runnable with `uvx`.

**MCP tools:** `setup_claude_folder`, `install_pack`, `upgrade_claude_folder`,
`audit_claude_folder`, `approve_hooks`, `list_packs`.

**CLI subcommands:** `setup`, `install-pack`, `upgrade`, `audit`,
`approve-hooks`, `list-packs`, `print-mcp-config`, `mcp`.

**Bundled packs:** `+pr-flow`, `+test-tooling`, `+data-science` ★,
`+visualization` ★, `+llm-app` ★, `+llm-extraction` ★, `+monorepo`,
`+security-hardening` ★ (★ = default-checked at `/setup`).

**Baseline scaffolds:** `CLAUDE.md` (≤40 lines, stack-substituted),
`.mcp.json.example`, `.gitignore` (managed block), and `.claude/` with
`README`, `ROUTER.md`, `settings.json`, `.meta/`, `rules/00-global`,
`skills/commit`, 4 Python hooks (session-start, deny-secrets,
deny-destructive, telemetry) + shared `lib/`, and `reference/` (INDEX +
README).

**Security:** PreToolUse hooks block `rm -rf` on `/`/`~`/`$HOME`, force-push
to protected branches, `sudo`, `curl|sh`/`wget|bash`, base64-decode-to-shell,
SSRF to cloud-metadata endpoints, `find -delete`/`find -exec rm`,
`shred`/`truncate -s0`, and reads of `.env*`, `credentials*`, SSH/AWS/GCP
credentials. Bash parsing is shlex-based with leading-assignment expansion
and short-flag bundle normalization to close the bypasses cataloged in the
security review.

**Testing:** 103 tests covering smoke, managed-block round-trips, stack
detection, hooks.lock drift, description lint, scaffold end-to-end, pack
catalog, audit categorization, bypass-resistant Bash parsing, hook-script
integration via subprocess invocation, and every pack's installation +
description-lint cleanliness.

**Known limitations / out of scope for v0.1.** See [`docs/roadmap.md`](roadmap.md)
for the full list of planned features grouped by intention (distribution &
UX, pack ecosystem, observability, safety & integrity, scale & polish).
Short list of deferred work:

- `uninstall-pack` command
- External (git-resolved) packs and pack scaffold/validate helpers
- Self-update notification at SessionStart
- Telemetry dashboard subcommand
- Pack signing for supply-chain safety
- Windows-native path-handling audit
- Internationalization

See `design/v4-mcp-distribution.md` for the design history (v0 → v4) and
`docs/security-model.md` for the security model.
