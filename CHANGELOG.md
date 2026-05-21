# Changelog

All notable changes to `claude-folder-handler` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

While pre-1.0, MINOR bumps may introduce breaking changes; they will be
called out in the **Changed** or **Removed** sections.

## [Unreleased]

## [0.1.0] — 2026-05-21

### Added
- **MCP server + CLI** distributed as a single Python package, runnable via `uvx`.
- **Six MCP tools** with lint-clean descriptions: `setup_claude_folder`, `install_pack`, `upgrade_claude_folder`, `audit_claude_folder`, `approve_hooks`, `list_packs`.
- **CLI subcommands**: `setup`, `install-pack`, `upgrade`, `audit`, `approve-hooks`, `list-packs`, `print-mcp-config`, `mcp`.
- **Lean baseline scaffold** (21 files) — `CLAUDE.md`, `.mcp.json.example`, `.gitignore` managed block, and `.claude/` with `README`, `ROUTER`, `settings.json`, `.meta/*`, `rules/00-global`, `skills/commit`, 4 Python hooks + shared `lib/`, and `reference/{INDEX,README}`.
- **Eight opt-in packs**: `+pr-flow`, `+test-tooling`, `+data-science` ★, `+visualization` ★, `+llm-app` ★, `+llm-extraction` ★, `+monorepo`, `+security-hardening` ★ (★ = default at `setup`).
- **Deterministic deny hooks** with shlex-based Bash parsing, leading-assignment expansion, and short-flag bundle normalization — closes `./.env` vs `./../foo/.env`, `F=.env; cat $F`, `rm -fr` vs `rm -rf`, `find -delete`, `curl|sh`, base64-decode-to-shell, SSRF to `169.254.169.254`.
- **Force-push policy**: hard-deny on `main`/`master`/`develop`/`release/*`; `ask` permission elsewhere.
- **hooks.lock** (sha256-per-script) with `+security-hardening`-installed SessionStart verifier and `approve-hooks` command.
- **Claude.ai Skill zip** — `claude-folder-handler-skill-<version>.zip` ships alongside the wheel/sdist for users on Claude.ai web/desktop (no Claude Code required).
- **Triggering-convention lint** — every shipped `SKILL.md` and agent `.md` passes the description lint (3rd person, 600–1200 chars, ≥2 quoted user phrases, NOT-for clause).
- **Test suite**: 108 tests covering smoke, managed-block round-trips, stack detection, hooks.lock drift, description lint, scaffold end-to-end, pack catalog, audit categorization, bypass-resistant Bash parsing, hook-script integration, and the Skill zip extraction + bundled-pkg sandbox simulation.

### Documentation
- README with six install paths (Have-Claude-do-it, MCP persistent, one-shot, CLI tool, CI, contributors, Claude.ai Skill) collapsed into `<details>` dropdowns.
- `docs/` covers architecture, MCP setup, packs, triggering convention, security model, upgrade flow, dogfood run, release, and the roadmap grouped by intention.
- `design/` preserves the full v0 → v4 design history with critiques and interviews.

[Unreleased]: https://github.com/Sdamirsa/claude-folder-handler-SKILL/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Sdamirsa/claude-folder-handler-SKILL/releases/tag/v0.1.0
