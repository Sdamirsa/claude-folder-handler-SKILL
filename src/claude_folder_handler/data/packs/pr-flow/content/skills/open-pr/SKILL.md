---
name: open-pr
description: |
  Opens a pull request for the current branch with a clear title, summary, and test-plan checklist drawn from the diff against the target base branch. Pushes the branch if it has unpushed commits, runs the local lint/test gate if it is fast, and creates the PR via the gh CLI (or prints a manual git push instruction if gh is unavailable). Detects the target base branch from `git config` and falls back to main/master/develop. Use when the user says "open a PR", "open a pull request", "ship this", "send for review", "PR this", "make a PR", "submit for review", "raise a pull request", or finishes a feature increment ready for review. NOT for committing work-in-progress — use the commit skill first. NOT for pushing to a protected branch directly; the hooks will block that, and this skill won't try.
---

# open-pr

Open a pull request for the current branch.

## Workflow

1. `git status` and `git log <base>..HEAD --oneline` — confirm there are commits.
2. If there are uncommitted changes, ask the user to commit first (or invoke the `commit` skill).
3. Determine the base branch:
   - `git config --get init.defaultBranch` if set
   - else fall back: `main` if it exists, then `master`, then `develop`.
4. If the local branch has unpushed commits, `git push -u origin <branch>` (NOT to a protected branch — refuse and tell the user).
5. Draft PR body:
   - **Title**: imperative, ≤72 chars; if the branch has a single conventional commit, reuse its subject.
   - **Summary** (1-3 bullets): the WHY.
   - **Test plan** (checklist): how to verify, derived from the diff.
6. Create via `gh pr create --title ... --body "$(cat <<'EOF'\n...\nEOF\n)" --base <base>` if gh is installed; otherwise print the URL pattern (`<remote>/compare/<base>...<branch>`) and the body for manual submission.
7. Return the PR URL.

## Constraints

- Never opens a PR from a protected branch.
- Doesn't review the diff — that's the `reviewer` agent's job.
- Doesn't merge — explicit user action only.
