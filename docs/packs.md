# Pack catalog

(Filled in as P4–P7 land. See `design/v4-mcp-distribution.md` §3 for the
intended contents of each pack.)

## Listing

```bash
uvx claude-folder-handler list-packs
```

Returns a JSON catalog: name, summary, default-checked flag, dependencies.

## Installing

Via Claude:

> *"install the data-science pack"*

Via CLI:

```bash
uvx claude-folder-handler install-pack data-science
```

## Default-checked at `/setup`

`+data-science +visualization +llm-app +llm-extraction +security-hardening +telemetry`

(Adjust by passing `--packs` to `setup`.)

## Pack file layout

```
packs/<name>/
├── pack.toml                       # name, summary, default, depends_on
├── content/                        # files copied verbatim under .claude/
│   ├── skills/<skill>/SKILL.md
│   ├── agents/<agent>.md
│   ├── rules/<rule>.md
│   ├── hooks/<NN-name>.py
│   └── reference/<topic>/<file>.md
├── router-rows.md                  # ROUTER.md managed-block content
└── settings-overlay.json           # additive merge into settings.json
```

The pack loader copies `content/*` into the repo's `.claude/`, then handles
the managed-block updates.
