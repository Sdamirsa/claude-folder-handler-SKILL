# Upgrade flow

## Lifecycle

```
   /setup ─────────────► .claude/.meta/version = X
                         .gitignore: <!-- managed:claude-folder-handler -->
                         settings.json: hooks + denies
                         ROUTER.md: managed:baseline + managed:pack-* blocks
                         hooks.lock: sha256 of every hook script

   (time passes; tool releases version X+1)

   /upgrade (--apply) ─► For every file in the new template:
                          - If absent in repo → create.
                          - If marker-bearing → replace content INSIDE every
                            <!-- managed:* --> block; preserve outside.
                          - If unmanaged → skip (user owns it).
                        Update .meta/version, regenerate hooks.lock.
```

## Managed-block taxonomy

| Block name | File | Inserted by |
|---|---|---|
| `managed:baseline` | `.claude/ROUTER.md` | baseline /setup |
| `managed:agents-baseline` | `.claude/ROUTER.md` | baseline /setup |
| `managed:reference-baseline` | `.claude/ROUTER.md` | baseline /setup |
| `managed:reference-catalog` | `.claude/reference/INDEX.md` | baseline + packs |
| `managed:claude-folder-handler` | `.gitignore` | baseline /setup |
| `managed:pack-<name>` | `.claude/ROUTER.md` | +<name> pack |
| `managed:pack-<name>-agents` | `.claude/ROUTER.md` | +<name> pack (if agents) |
| `managed:pack-<name>-reference` | `.claude/ROUTER.md` | +<name> pack (if reference) |

User-written rows/lines go OUTSIDE these blocks. They survive `upgrade`.

## settings.json: list-aware merge

`settings.json` is strict JSON — no comment markers. Instead, `upgrade` does
a typed deep-merge:

- Lists (e.g., `permissions.deny`) are concatenated with dedupe.
- Dicts (e.g., `hooks.PreToolUse`) recursively merge.
- Scalars are replaced.

The deep-merge is idempotent: running `upgrade` twice with no template
changes produces no diff.

## hooks.lock regeneration

Every successful `upgrade` (and every `install-pack`) regenerates
`hooks.lock`. If your local hook edits intentionally diverge from the
template (you customized a hook), run `approve-hooks` after upgrading to
re-lock against your version.

## Dry-run by default

`uvx claude-folder-handler upgrade` is a dry-run — it prints the action plan
without writing. Pass `--apply` to actually mutate the repo.

Via MCP: `upgrade_claude_folder(apply=true)`.

## Removing a pack

Currently: manually delete the pack's files and remove its row from
`.claude/.meta/packs.json`. A first-class `uninstall-pack` command is on the
roadmap (see [`design/v4-mcp-distribution.md`](../design/v4-mcp-distribution.md)
§12 — "out of scope for v0.1").

## Conflict resolution

If two packs claim the same file path, `install_pack` refuses with a
`conflicts` list. Resolve by uninstalling one pack first.
