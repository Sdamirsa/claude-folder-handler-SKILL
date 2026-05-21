# Changelog

All notable changes to `claude-folder-handler` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

While pre-1.0, MINOR bumps may introduce breaking changes; they will be
called out in the **Changed** or **Removed** sections.

## [Unreleased]

## [0.1.3] — 2026-05-21

### Fixed
- **Claude.ai Skill zip rejected as "Zip cannot contain nested zip files".** The v0.1.2 fix for the "exactly one SKILL.md" validator packed the bundled `data/` tree as a nested `data.zip` — which then tripped Claude.ai's *second* upload rule. The validator enforces both rules simultaneously: exactly one `SKILL.md`, and zero nested `.zip` files. v0.1.3 ships `data/` as loose files with every bundled `SKILL.md` renamed to `_skill_body.md` at build time. The embedded `scripts/scaffold.py` renames them back to `SKILL.md` on disk on first run (sentinel-guarded, idempotent) before importing the package, so the package's `_data_root()` / `_template_root()` / `_packs_root()` keep working unchanged.
- **`build_skill_zip.py`** now asserts BOTH invariants at build time: exactly 1 `SKILL.md`, zero `.zip` entries. Either failure aborts the build with a clear error.

### Documentation
- **README Install section** restructured by audience instead of by install variant: a top-level **Option 1** (Claude.ai web/desktop — drag-and-drop, no terminal) with a thorough non-technical walkthrough including a plain-English explanation of what `.claude/` is, step-by-step screenshots-free instructions, and an FAQ; a top-level **Option 2** (Claude Code MCP — full ongoing toolkit) wraps all six original install variants (A–F) as nested dropdowns. The old buried "Skill upload" option G is promoted into the new Option 1.

## [0.1.2] — 2026-05-21

### Fixed
- **Claude.ai Skill zip rejected as "Zip must contain exactly one SKILL.md file. Currently there are 14."** The v0.1.1 zip shipped the bundled `data/` tree as loose files, which dragged 13 nested `SKILL.md` files (baseline `commit` skill body + every `+pack`'s scaffolded skill bodies) into the outer namelist. Claude.ai's uploader counts every `SKILL.md` in the archive and rejects on > 1. Fixed by packing `data/` as a single `data.zip` inside the skill bundle; the embedded `scripts/scaffold.py` extracts it once at startup before importing the package.

### Changed
- **Skill zip layout** verified against the [`anthropics/skills/algorithmic-art` reference](https://github.com/anthropics/skills/tree/main/skills/algorithmic-art): exactly one top-level `SKILL.md`, payload under `scripts/`, no nested `SKILL.md` anywhere else in the outer zip.
- **`SKILL.md` frontmatter** uses an inline single-line `description:` value instead of a `|` literal block (matches the algorithmic-art / docx style; avoids strict-YAML-validator edge cases).
- **`build_skill_zip.py`** now asserts the SKILL.md-count invariant at build time and fails loudly if it ever regresses.

## [0.1.1] — 2026-05-21

### Changed
- **Claude.ai Skill zip layout** rebuilt to match Anthropic's skill-creator convention. The zip now roots at `claude-folder-handler/` (top-level folder = skill name), with `SKILL.md` and a `scripts/` directory containing a deterministic `scaffold.py` entry point alongside the vendored package. Previously the zip put `SKILL.md` at the zip root and asked Claude to run `sys.path.insert` + manual `import` boilerplate inline on every invocation — fragile and prone to drift.
- **`scripts/scaffold.py`** added as the skill's CLI entry point (bundled inside the zip). Supports `--list-packs`, `--project-name`, `--manifest-file`, `--manifest-name`, `--packs`, `--defaults`, `--out`. Returns a JSON summary on success.
- **`SKILL.md` (inside the zip)** rewritten to delegate all deterministic work to `scripts/scaffold.py` rather than asking Claude to re-derive the logic on each invocation. The "when to use" trigger language in the frontmatter is preserved.

### Removed
- **`README.md` inside the skill zip** — not part of the official skill convention; the SKILL.md is the only documentation Claude.ai consumes.

### Fixed
- Bundled package files now live under `scripts/claude_folder_handler/` (skill convention) instead of a custom `pkg/` directory.

### Documentation
- `docs/release.md` records the v0.1.0 release gotcha (environment tag rule defaults to ref type Branch and silently rejects every tag push).

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

[Unreleased]: https://github.com/Sdamirsa/claude-folder-handler-SKILL/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/Sdamirsa/claude-folder-handler-SKILL/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/Sdamirsa/claude-folder-handler-SKILL/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/Sdamirsa/claude-folder-handler-SKILL/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Sdamirsa/claude-folder-handler-SKILL/releases/tag/v0.1.0
