# Pack catalog

| Pack | Default | Adds |
|---|---|---|
| `+pr-flow` | — | `open-pr`, `rebase-clean` skills; `reviewer` agent |
| `+test-tooling` | — | `debug-failing-test` skill; `test-writer` agent |
| `+data-science` | ★ | `inspect-df`, `clean-data` skills; `data-explorer` agent; `rules/pandas.md`; `reference/datasets/_template.md` |
| `+visualization` | ★ | `quick-chart`, `chart-review` skills; `rules/plotting.md`; `reference/charts/_examples.md` |
| `+llm-app` | ★ | `anthropic-sdk-bootstrap`, `migrate-model-version` skills; `rules/anthropic-sdk.md`; `hooks/15-warn-stale-model.py`; `reference/apis/anthropic-sdk.md` |
| `+llm-extraction` | ★ | `extract-structured`, `build-extractor-eval`, `batch-extract` skills; `schema-designer` agent; `rules/extraction.md`; `reference/schemas/_template.md`, `reference/prompts/_template.md`, `reference/extraction-checklist.md` |
| `+monorepo` | — | `rules/per-package.md` for `apps/**` and `packages/**` |
| `+security-hardening` | ★ | `hooks/05-verify-hooks-lock.py` (SessionStart drift warning); tighter denies (token/secret/terraform/gcp creds, `eval *`, `exec *`, ssh with `StrictHostKeyChecking=no`) |

`+telemetry`'s functionality is built into the baseline — the
`90-stop-log-invocation.py` hook ships with /setup. Audit reads the resulting
`.claude/.cache/invocations.jsonl` to flag dead skills.

## Listing the catalog

```bash
uvx claude-folder-handler list-packs
```

## Installing

Ask Claude:

> *"install the data-science pack"*

Or via CLI:

```bash
uvx claude-folder-handler install-pack data-science
```

## Default-checked at `setup`

`+data-science +visualization +llm-app +llm-extraction +security-hardening`

(The `+telemetry` baseline functionality is always on.) Override with
`--packs` to pick your own set:

```bash
uvx claude-folder-handler setup --packs pr-flow test-tooling
```

## Pack file layout

Each pack lives under `data/packs/<name>/`:

```
packs/<name>/
├── pack.toml                       # name, summary, default, depends_on
├── router-rows.md                  # skills-table rows for ROUTER.md managed:pack-<name>
├── router-rows-agents.md           # optional; managed:pack-<name>-agents
├── router-rows-reference.md        # optional; managed:pack-<name>-reference
├── settings-overlay.json           # optional; merged into .claude/settings.json
└── content/                        # copied verbatim under .claude/
    ├── skills/<skill>/SKILL.md
    ├── agents/<agent>.md
    ├── rules/<rule>.md
    ├── hooks/<NN-name>.py
    └── reference/<topic>/<file>.md
```

The pack loader copies `content/*` into the target repo's `.claude/`, applies
the ROUTER managed-block updates, deep-merges `settings-overlay.json`, appends
to `.claude/.meta/packs.json`, and regenerates `hooks.lock`.

## Adding your own pack

(Not yet a first-class feature — would require either committing to a fork of
this repo or hand-managing the files inside the target repo's `.claude/`.
Tracked for a future release.)
