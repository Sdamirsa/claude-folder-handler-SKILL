# Architecture

A two-surface design with shared core:

```
                    ┌────────────────────────┐
                    │  cli.py (argparse)     │   ← humans: uvx claude-folder-handler setup
                    │  mcp_server.py (tools) │   ← Claude: "set up .claude here"
                    └─────────┬──────────────┘
                              │
                              ▼
              ┌────────────────────────────────────┐
              │            core/                   │
              │  detect_stack    pack_loader       │
              │  managed_blocks  scaffold          │
              │  hooks_lock      upgrade           │
              │  description_lint  audit           │
              └─────────┬─────────────────┬────────┘
                        │                 │
                        ▼                 ▼
                 ┌─────────────┐   ┌─────────────┐
                 │ data/       │   │ target repo │
                 │  template/  │ → │ .claude/    │
                 │  packs/     │   │ CLAUDE.md   │
                 └─────────────┘   │ .gitignore  │
                                   └─────────────┘
```

## Layered enforcement (in target repos)

| Layer | Mechanism | Failure mode |
|---|---|---|
| Hooks (Python, UV-script) | Deterministic. PreToolUse exit 2 = hard deny. | None (within budget); Claude sees stderr |
| Skills / Agents | Probabilistic. Trigger by description match. | Under-trigger or over-trigger |
| CLAUDE.md / rules | Advisory. User message in context. | Model talked out of it |

`claude-folder-handler` configures all three layers consistently. See
[`security-model.md`](security-model.md) for the deny rules and what they
catch.

## Distribution

| Channel | URL | When |
|---|---|---|
| PyPI | `uvx claude-folder-handler@<ver>` | Default. Pinned or latest. |
| Git | `uvx --from git+https://github.com/Sdamirsa/claude-folder-handler-SKILL@<ref> claude-folder-handler` | Bleeding edge or pre-publish |
| Local | `uvx --from /path/to/repo claude-folder-handler` | Development |

No filesystem install required. `uvx` handles caching, isolation, and
version resolution.

## Managed blocks (the upgrade contract)

Files that change across versions (`ROUTER.md`, `settings.json`, `.gitignore`)
contain `<!-- managed:NAME -->...<!-- /managed:NAME -->` regions. `upgrade`
only rewrites *inside* those regions; user content outside is preserved.

Each pack contributes to specific managed blocks (e.g., `+data-science` writes
to `managed:pack-data-science` rows in ROUTER and `managed:pack-data-science`
keys in settings). Uninstall-by-rewriting is therefore possible without
ambiguity.

## Bundled data

`src/claude_folder_handler/data/` contains the template tree and all packs.
The package's wheel includes this directory via
`hatch.build.targets.wheel.force-include`. At scaffold time, `_mcp.json.example`
and `_gitignore.snippet` (underscored to avoid dotfile packaging quirks) are
renamed to their `.`-prefixed targets. The `claude/` subtree is relocated to
`.claude/` and `meta/` becomes `.meta/`.

## Tests

`uv run pytest` runs the suite (73+ tests). Categories:

| File | Tests |
|---|---|
| `test_smoke.py` | Imports, --version, data root reachable |
| `test_managed_blocks.py` | Block insert / replace / remove / list / settings merge |
| `test_detect_stack.py` | Stack detection across Python, Node, Rust, Go |
| `test_hooks_lock.py` | Lock generate / verify / drift detection |
| `test_description_lint.py` | All lint rules + baseline-skill cleanliness |
| `test_scaffold.py` | End-to-end scaffold into tmpdir |
| `test_pack_loader.py` | Pack catalog + install guards |
| `test_audit.py` | Audit warnings categorize correctly |
| `test_bash_parse.py` | Bypass-resistant Bash parsing for deny hooks |
| `test_hook_scripts.py` | Hook scripts as subprocesses with crafted payloads |
