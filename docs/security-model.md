# Security model

Three concentric defenses, each with a different failure mode.

## 1. Permission rules (advisory)

`settings.json` `permissions.deny` lists patterns Claude Code refuses before
invoking the underlying tool. Useful for fast-path blocks but **the model can
still try variants**. Treat this layer as documentation + speed.

Baseline denies (see `data/template/claude/settings.json.tmpl`):

- `Read(**/.env*)`, `Read(**/credentials*)`, `Read(**/id_rsa*)`, `Read(**/*.pem)`, `Read(**/*.key)`
- `Read(~/.ssh/**)`, `Read(~/.aws/**)`, `Read(~/.gnupg/**)`, `Read(~/.kube/config)`, `Read(~/.docker/config.json)`
- `Read(/proc/*/environ)`
- `Edit(**/.env*)`, `Write(**/.env*)`
- `Edit(**/.git/**)`, `Write(**/.git/**)`, `Edit(**/.claude/hooks/**)`, `Write(**/.claude/hooks/**)`
- `Bash(rm -rf /*)`, `Bash(rm -rf ~*)`, `Bash(rm -rf $HOME*)`, `Bash(sudo *)`
- `Bash(curl *169.254.169.254*)`, `Bash(curl *metadata.google.internal*)`
- `Bash(curl * | sh)`, `Bash(curl * | bash)`, `Bash(wget * | sh)`, `Bash(wget * | bash)`

## 2. PreToolUse hooks (deterministic)

`.claude/hooks/10-pre-deny-secrets.py` and `20-pre-deny-destructive.py` are
the **only** layer that *guarantees* a block. They run as subprocesses on
every relevant tool call; exit code 2 + stderr is hard-block.

Both hooks are stdlib-only Python with UV inline-script headers (`uv run
--script`). They:

- Canonicalize paths via `pathlib.Path.resolve()` — closes `./.env` vs
  `./../../.env` vs `/abs/path/.env` bypasses.
- Parse Bash commands via `shlex.split()` and walk leading-assignment
  substitutions — closes `F=.env; cat $F` bypasses.
- Handle compound commands (`;`, `&&`, `||`, `|`, `$()`) by splitting into
  clauses and inspecting each independently.
- Normalize flag bundles (`-rf`, `-fr`, `-r -f`, `--recursive --force`) so a
  single rule catches every variant.
- Catch `find ... -delete` and `find ... -exec rm ...` masquerading as a
  non-`rm` destructive op.

### What gets blocked

**Credentials (10-pre-deny-secrets.py):**

- Any path resolving to `*/.env`, `*/.env.*`, `*/credentials*`, `*/id_rsa*`,
  `*/*.pem`, `*/*.key`, `*/.git-credentials`, `*/.npmrc`, `*/.netrc`,
  `*/.pypirc`, `~/.ssh/**`, `~/.aws/**`, `~/.gnupg/**`, `~/.kube/config`,
  `~/.docker/config.json`, `/proc/*/environ`
- Bash commands referencing those paths even after env-var indirection.

**Destructive (20-pre-deny-destructive.py):**

- `rm -rf` / `rm -fr` / `rm -r -f` targeting `/`, `~`, `$HOME`, `/root`, `/home`, `/Users`, `/var`, or the project dir
- `find -delete`, `find -exec rm/shred/truncate`
- `shred`, `truncate -s0`
- `git push --force`/`-f`/`--force-with-lease`/`+ref` to branches in
  `.claude/.meta/protected-branches.json` (default: `main`, `master`,
  `develop`, `release/*`)
- `git reset --hard <protected>`
- `sudo`, `doas`, `su`
- `curl ... | sh`, `wget ... | bash`, base64-decode piped to shell, `eval $(curl ...)`
- `curl` / `wget` to cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`)

### Hook integrity (hooks.lock)

`.claude/.meta/hooks.lock` records sha256 for each hook file. The
`+security-hardening` pack's `05-verify-hooks-lock.py` runs at SessionStart
and refuses to chain other hooks when the lock mismatches.

Legitimate edits → `claude-folder-handler approve-hooks` (or ask Claude
*"approve hooks"*) to regenerate the lock.

## 3. CLAUDE.md / rules (preventive nudges)

The lowest defense: text in CLAUDE.md and `rules/00-global.md` reminds Claude
not to touch sensitive things. Important but not load-bearing.

## What's NOT blocked

Intentional gaps (don't expect protection from):

- **Reading repo-tracked code** — that's normal use.
- **Writing repo files** (other than `.git/**`, `.claude/hooks/**`, `.env*`) — Claude's job is to write code.
- **`git push` to non-protected branches** — `ask` permission instead.
- **Network egress in general** — only the `curl|sh` / metadata-endpoint shapes are blocked.

## `.mcp.json` trust model

`.mcp.json` is gitignored by default. `.mcp.json.example` is committed as a
template. This prevents "PR adds a malicious MCP server that runs on every
session" scenarios. Each developer's `.mcp.json` is their own.

## Telemetry

`.claude/.cache/invocations.jsonl` is local-only — never network. `+telemetry`
pack writes it; `audit` reads it. Add `.claude/.cache/` to `.gitignore` (the
baseline already does).
