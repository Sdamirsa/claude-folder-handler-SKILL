---
name: rebase-clean
description: |
  Rebases the current feature branch onto the latest tip of the target base branch and tidies the commit history (squashing fixups, dropping wip commits, rewriting unclear subject lines). Aborts on non-trivial conflicts rather than guessing; the user must resolve manually. Detects the base branch from `git config init.defaultBranch` or falls back to main/master/develop. Use when the user says "rebase on main", "rebase against master", "clean up history", "squash my commits", "tidy the commits", "rewrite the history before merging", or asks to get the branch up to date before opening a PR. NOT for force-pushing — that is a separate action gated by deny rules. NOT for resolving merge conflicts on protected branches; aborts immediately if the current branch is protected.
---

# rebase-clean

Rebase the current branch onto its base and clean up the commit history.

## Workflow

1. Detect current branch + base (`init.defaultBranch` → main → master → develop).
2. Refuse if the current branch is in the protected list.
3. Confirm working tree is clean (`git status --porcelain`); abort if dirty.
4. `git fetch origin <base>`.
5. List the commits to rebase: `git log <base>..HEAD --oneline`.
6. Identify fixup/wip/typo-only commits → squash candidates; identify unclear subjects → reword candidates.
7. Present the plan to the user; on confirmation, run `git rebase --interactive --autosquash origin/<base>` via a generated sequence-editor script that applies the plan non-interactively.
8. On conflict, run `git rebase --abort` and surface the conflict to the user with the conflicted file list.
9. On success, show the new history. DOES NOT push — the user (or `open-pr`) handles that.

## Constraints

- Never force-pushes; that's the user's explicit action.
- Aborts cleanly on conflict; doesn't try `theirs`/`ours` guessing.
- Refuses on protected branches.
