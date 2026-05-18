# Critique Synthesis (v0 → v1 deltas)

Four critique agents reviewed v0 through different lenses. Their findings converged on a reframe rather than tweaks.

## Convergent findings (where ≥2 lenses agreed)

| Finding | Trigger | Simple | Security | Red-team |
|---|---|---|---|---|
| MANIFEST.json adds drift cost for no triggering value | ✓ | ✓ |  | ✓ |
| `agents/` baseline (3 agents) is over-budget; ship 0 or 1 | ✓ | ✓ |  | ✓ |
| Bash hooks are unsafe — regex misses obvious bypasses |  |  | ✓ | ✓ |
| `.mcp.json` committed by default is a supply-chain hole |  |  | ✓ | ✓ |
| Need a single-source-of-truth router (vs N racing descriptions) | ✓ |  |  | ✓ |
| No upgrade/migration story for already-bootstrapped repos |  | ✓ |  | ✓ |
| Default scaffold is too big — ship a lean baseline + opt-in packs |  | ✓ |  | ✓ |
| Skill descriptions need symptom-phrase keywords, not internal names | ✓ |  |  | ✓ |

## Divergent findings (single-lens, but high-value)

- **(Security):** Hook-script supply chain → need `hooks.lock` (sha256) + first-run approval; the `permissions.deny` rules have ~10 named bypasses.
- **(Simplicity):** CLAUDE.md ≤80 lines needs a *forcing function*, not a norm — wire to a hook.
- **(Trigger):** Meta-skill self-collision with `/audit` on the phrase "audit my claude config".
- **(Red-team):** Adopt `obra/superpowers` ROUTER pattern, `launchdarkly` external-JSON-driven SessionStart, `disler` UV Python hooks, `dotclaude` deep auto-detection.

## v0 → v1 design moves

1. **Drop MANIFEST.json; replace with ROUTER.md** (single canonical triggering doc, injected at SessionStart). Router serves humans + agents + triggering all at once.
2. **Ship lean baseline (1 skill, 2 hooks, 0 agents); rest as opt-in packs** (`+security`, `+pr-flow`, `+test-tooling`, `+frontend`). `/setup` picks packs.
3. **Hooks in Python with UV inline deps**, not bash. Real shlex parsing, real glob via `pathlib`, real regex with anchors. Cross-platform.
4. **`.mcp.json` gitignored by default**, ship `.mcp.json.example` + first-run prompt to approve. Same model for hooks via `hooks.lock`.
5. **Drop `/audit` from baseline** until there's >1 skill to audit. Replace with a SessionStart soft-warning when artifacts drift.
6. **Add upgrade machinery**: `.claude/.meta/version`, `<!-- managed:* -->` blocks in templates, `/upgrade` command in packs (not baseline).
7. **Sharper meta-skill description** (negative scope: only triggers on explicit ".claude" / "CLAUDE.md" / "claude code config" mentions, never on generic "setup", "init", "scaffold").
8. **Rewrite triggering convention** with symptom-phrase requirements + minimum 600 chars + ≥5 keyword variants drawn from how users actually talk.
9. **Tightened permission denies** using `**/.env*`, `**/credentials*`, `**/.git/**`, `**/.claude/hooks/**`, plus WebFetch domain allowlist and SSRF deny patterns.
10. **Monorepo story**: documented per-package `CLAUDE.md` path-scoped pattern; per-package `.claude/` is opt-in.

## What stays from v0

- The five design principles (still right).
- The folder taxonomy (still right; the criticism was about *how many directories to populate by default*, not their existence).
- The CLAUDE.md "≤80 lines, points to .claude/" pattern.
- Path-scoped rules under `.claude/rules/`.
- Settings.json / settings.local.json split.
- SessionStart hook for context injection (now external-JSON-driven).
- PreToolUse hook for deny-secrets (now Python).
