# Dogfood run — 2026-05-18

End-to-end verification of the full install → setup → audit flow using the
v0.1.0 build of `claude-folder-handler`.

## Setup

```sh
mkdir /tmp/dogfood && cd /tmp/dogfood
cat > pyproject.toml <<EOF
[project]
name = "dogfood-demo"
version = "0.1.0"
dependencies = ["anthropic", "pandas", "matplotlib"]
EOF
git init -q

uvx --refresh --from /path/to/claude-folder-handler-SKILL claude-folder-handler setup --cwd /tmp/dogfood
```

## Result: 40 files created

- 16 baseline files (CLAUDE.md, `.claude/{README,ROUTER,settings.json,.meta/*,rules/00-global,skills/commit,hooks/{00-90}.py + lib/}`, reference/{INDEX,README})
- 5 default packs installed: `+data-science`, `+visualization`, `+llm-app`, `+llm-extraction`, `+security-hardening`
- 6 skills + 2 agents + 4 rules + 6 reference docs added by packs
- 2 additional hooks installed by packs (`05-verify-hooks-lock`, `15-warn-stale-model`)
- 1 settings overlay merged: PostToolUse hook + 14 new deny rules

## Audit

```sh
uvx claude-folder-handler audit --cwd /tmp/dogfood
```

```json
{
  "ok": true,
  "installed_packs": ["data-science", "llm-app", "llm-extraction", "security-hardening", "visualization"],
  "warnings": [],
  "summary": {"total": 0}
}
```

Zero warnings — drift, lint, size, reference-staleness, telemetry all clean.

## ROUTER managed blocks populated

| Block | Content |
|---|---|
| `managed:baseline` | baseline `commit` skill row |
| `managed:pack-data-science` | inspect-df, clean-data |
| `managed:pack-visualization` | quick-chart, chart-review |
| `managed:pack-llm-app` | anthropic-sdk-bootstrap, migrate-model-version |
| `managed:pack-llm-extraction` | extract-structured, build-extractor-eval, batch-extract |
| `managed:pack-data-science-agents` | data-explorer |
| `managed:pack-llm-extraction-agents` | schema-designer |
| `managed:pack-data-science-reference` | datasets/ |
| `managed:pack-visualization-reference` | charts/_examples.md |
| `managed:pack-llm-app-reference` | apis/anthropic-sdk.md |
| `managed:pack-llm-extraction-reference` | schemas/, prompts/, extraction-checklist.md |

## settings.json after merges

- PreToolUse: 2 hook entries (baseline only — packs didn't add Pre hooks)
- PostToolUse: 1 hook entry (`15-warn-stale-model.py` from +llm-app)
- SessionStart: 2 hook entries (baseline `00-session-start` + security `05-verify-hooks-lock`)
- Stop: 1 hook entry (baseline telemetry)
- `permissions.deny`: 42 rules (28 baseline + 14 from +security-hardening)

## hooks.lock

Includes sha256 of all 6 hooks now on disk:
`00-session-start`, `05-verify-hooks-lock`, `10-pre-deny-secrets`,
`15-warn-stale-model`, `20-pre-deny-destructive`, `90-stop-log-invocation`.

## Tests

103/103 unit + integration tests pass:

```
$ uv run pytest
103 passed in 2.25s
```

Includes: 73 from the foundation + 30 pack-level tests (every pack installs
clean, every shipped description passes the lint, settings overlays merge,
hooks.lock stays consistent across pack installs).

## Conclusion

Ready for v0.1.0 tag + PyPI publish (P9).
