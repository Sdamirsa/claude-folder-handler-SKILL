---
paths:
  - "apps/**"
  - "packages/**"
applies_when: "always within these paths"
---

# Monorepo conventions

## Per-package CLAUDE.md
- Every package under `apps/<name>/` or `packages/<name>/` should have its
  own `CLAUDE.md` (≤30 lines) describing:
  - What this package does (1-2 sentences).
  - Build/test/lint commands SPECIFIC to this package (if they differ from root).
  - Internal dependencies (other packages this depends on).
- These per-package CLAUDE.md files are lazy-loaded only when Claude reads
  files inside the package — they don't tax the root context.

## Cross-package changes
- Touching ≥2 packages → mention which in the commit subject.
- Don't introduce cross-package imports that bypass the public API.
- If a refactor cascades across many packages, open a tracking issue first.

## Tests
- Each package owns its own tests under `apps/<name>/tests/` or `packages/<name>/tests/`.
- A failed test in package A shouldn't be "fixed" by editing package B unless
  the bug truly lives there.

## Skills + agents in monorepos
- Skills and agents live at the repo-root `.claude/skills/` and `.claude/agents/`.
- For package-specific workflows, prefer path-scoped rules over package-local
  skill duplicates.

## Stub for each package

```markdown
# <package-name>

## Purpose
<one-paragraph>

## Run
- Build: `<cmd>`
- Test: `<cmd>`
- Lint: `<cmd>`

## Depends on
- `packages/<other-name>` for X
```
