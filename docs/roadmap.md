# Roadmap

Not promises — directions. Each item describes **what** we'd build and the
**intention** (the user pain it relieves). Order within each section is
roughly by where we'd start if we had a free afternoon.

---

## Distribution & UX
*Intention: make install, update, and recovery so frictionless that a user can adopt or abandon the tool in a minute.*

- **`uninstall-pack <name>`** — remove a pack's files + ROUTER blocks + settings overlay + packs.json entry. Currently a manual chore; the loader already has the ownership info needed (managed blocks, packs.json, file lists in `pack.toml`).
- **Self-update notification** — at SessionStart, compare `.meta/version` against the latest available version from the installed package; if drift, inject a one-line `additionalContext` suggesting `upgrade_claude_folder`. Saves users from running stale templates for months.
- **`migrate-from-v3` helper** — detect a `~/.claude/skills/claude-folder-handler` install left over from the old `install.sh` design and offer to remove it. Trivial because v3 never shipped publicly; useful as goodwill for any early adopters who pre-cloned.
- **`init` wizard mode** — when called without `--packs`, interactively walk the user through pack selection (multi-select with descriptions) instead of using defaults. Currently the choice is made silently from `default=true` in `pack.toml`; a wizard is friendlier for first-time users.
- **Windows-native install hardening** — UV and git already work; the remaining gaps are path handling in `bash_parse.py` (assumes `/` separators) and the protected-branches glob behavior. Intention: not block Windows-native dev shops from adopting.
- **`print-mcp-config --merge`** — read `~/.claude/settings.json`, print the merged result with `claude-folder-handler` added. Users currently hand-merge; one bad-JSON edit is a long debugging trip.

## Pack ecosystem
*Intention: let users build their own packs without forking this repo.*

- **External pack support** — `install-pack git+https://github.com/x/y` resolves a pack from a remote source instead of the bundled catalog. Once external sources are trusted, the catalog stops being a bottleneck.
- **Pack scaffold command** — `claude-folder-handler new-pack <name>` creates the `pack.toml` + `content/` skeleton + `router-rows.md` stubs. Reduces "how do I build a pack?" from a README scavenger hunt to a single command.
- **Pack manifest validation** — `claude-folder-handler validate-pack <path>` runs the description lint, checks `pack.toml` schema, dry-runs the install, and reports problems. Today the only validation is "did install_pack crash?".
- **Pack dependency resolution** — if pack A `depends_on = ["data-science"]`, install A automatically installs data-science first. We already parse `depends_on`; we just warn instead of resolving.
- **Versioned packs** — `pack.toml` declares a `version`; `install-pack data-science@1.2` pins it. Enables upgrading packs independently of the meta-tool.

## Observability
*Intention: make telemetry actually useful instead of write-only logs.*

- **`telemetry-dashboard`** — a CLI subcommand that renders `.cache/invocations.jsonl` as a markdown summary (top skills, dead skills, success rate, p50/p95 duration). Currently audit just flags dead skills.
- **Per-pack adoption metrics** — track which packs' skills/agents are actually used vs ignored after install. Lets users prune (or signals which packs are worth keeping in defaults).
- **Schema for invocation records** — current format is best-effort `{ts, event, session_id, ...}`. A typed schema + versioning would survive log format evolution.
- **Hook execution timing** — log the duration of each PreToolUse hook. If `10-pre-deny-secrets.py` takes 200ms on every call we want to know.
- **Opt-in anonymized usage report** — for users who want to contribute back, a `share-anonymized-stats` command that emails counts (not content) to a public stats page. Helps prioritize future pack work. Strictly off by default.

## Safety & integrity
*Intention: shrink the attack surface a malicious PR could exploit.*

- **Pack signing** — `pack.toml` records a sha256 of the entire `content/` tree; `install-pack` verifies. Stops "PR replaces a skill body with a backdoor" attacks once we have external packs.
- **Hook bypass logging** — when a deny hook fires (exit 2), append a redacted record to `.cache/blocks.jsonl`. Useful for post-incident analysis ("did the model try to read `.env` ten times today?").
- **Description-lint as a pre-commit hook** — `+security-hardening` pack contains the lint logic, but doesn't yet install a pre-commit hook. Adding one promotes lint warnings to "you can't merge bad descriptions".
- **Per-pack permission scopes** — packs declare which `permissions.allow` rules they actually need. Catches "this pack quietly added `Bash(*)` to allow" supply-chain games.
- **Symlink defense** — current path canonicalization handles `..` and `~`; but a symlink farm (`./safe -> /etc/shadow`) could theoretically slip past glob match. We resolve via `Path.resolve()` which DOES follow symlinks, but should add an explicit test matrix.

## Scale & polish
*Intention: keep the tool fast and pleasant at sizes beyond the 50-file test repo.*

- **Lazy data loading** — currently `list_packs()` walks every `pack.toml` on import; for a catalog of 100+ external packs this gets expensive. Lazy-load + cache.
- **Faster scaffold** — measured ~150ms cold-start on a fresh `uvx` install; dominated by Python startup + mcp SDK import. Investigate whether mcp's deps can be lazy-imported.
- **Multi-language project detection** — current `detect_stack` returns all languages but defaults to one set of build/test/lint commands. Polyglot repos (Python backend + TS frontend) deserve a multi-section CLAUDE.md.
- **Internationalization** — descriptions, ROUTER rows, audit output are English-only. Hard problem (the model's keyword-matching is mostly tuned for English) but worth tracking.
- **Notebook-aware hooks** — `90-stop-log-invocation.py` doesn't know it's running inside a `.ipynb`-driven workflow; a notebook-specific PostToolUse hook could capture cell outputs separately.

## What we will probably **not** build
*Intention: be explicit about scope so we can say no without re-arguing.*

- **A GUI** — this is a CLI/MCP tool. Visualization belongs in the editor.
- **Hosted telemetry backend** — local-only JSONL is the contract. Don't add network egress.
- **A skills marketplace with auth/billing** — out of charter; if external packs land, they're git-resolved (free), period.
- **Auto-PR-creation on upgrade** — opening PRs in the user's repo without their knowledge is a footgun.
- **Replacing Claude Code's own permission system** — we add denies; we don't try to subsume what Claude Code does natively.
- **Cross-MCP-server orchestration** — out of scope; that's the Claude Agent SDK's job.

---

## How to propose an addition

1. Open an issue with the user pain in 1-2 sentences ("I keep doing X manually and want Y").
2. Tag it with the relevant section above. If it doesn't fit, that's interesting — surface why.
3. If you have code, send a PR against a feature branch. Keep `pack.toml` / `pyproject.toml` updates minimal until the design is settled.

## Design history

- [`design/v0-claude-folder-system.md`](../design/v0-claude-folder-system.md) — initial sketch
- [`design/v1-claude-folder-interview.md`](../design/v1-claude-folder-interview.md) — first design pass
- [`design/v2-final-plan.md`](../design/v2-final-plan.md) — interview round 1
- [`design/v3-locked-spec.md`](../design/v3-locked-spec.md) — interview round 2; decisions locked
- [`design/v4-mcp-distribution.md`](../design/v4-mcp-distribution.md) — pivot to MCP/uvx distribution
