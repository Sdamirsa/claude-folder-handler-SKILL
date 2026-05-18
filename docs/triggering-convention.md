# Triggering convention

Every skill, agent, and MCP-tool description follows this template:

```
<First sentence: leads with the keyword users say; states capability in third person.>
<Optional second sentence: edge cases or expected inputs.>
Use when the user says "<verbatim 1>", "<verbatim 2>", "<verbatim 3>",
asks about <symptom 1>, <symptom 2>, or mentions <noun 1>, <noun 2>.
NOT for <negative scope referencing the most-similar other artifact>.
```

## Hard rules

| Rule | Why |
|---|---|
| 600 ≤ length ≤ 1200 chars | Below 600 under-triggers; above 1200 risks budget truncation (1536 cap) |
| ≥5 keyword variants | Anthropic's own guidance: descriptions should be "somewhat pushy" |
| ≥2 verbatim quoted user phrases | Direct keyword matches beat inference |
| One `NOT for ... use X instead` clause | Disambiguates from neighbours |
| Third person only | "I/you/we" breaks the model's recognition heuristic |

`description_lint` enforces these as advisory warnings in `audit`. The
`+security-hardening` pack can promote them to blocking.

## Example: the baseline `commit` skill

> Stages and commits the current changes in the working tree after a quick
> sanity check on the diff. Inspects `git status` and `git diff`, drafts a
> concise commit message from the diff (subject line + 1-2 line body
> explaining the WHY, not the WHAT), runs the project's lint or test gate if
> it is fast, and creates the commit. Honors the protected-branch list.
> Use when the user says "commit", "commit this", "save changes", "check in",
> "stage and commit", "wrap this up", "make a commit", or finishes a logical
> unit of work. NOT for opening a pull request — use the open-pr skill from
> the +pr-flow pack instead. NOT for amending or rewriting history.

Length: ~750 chars. 8 keyword variants. 5 quoted phrases. Two negative scopes.
Third person throughout.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| `"A skill that commits things."` | Generic; no symptom keywords; no quoted phrases |
| `"I will commit your changes."` | First person breaks recognition |
| `"Commits."` | Too short; will lose to longer competitors |
| `"Commits, opens PRs, reviews code, and ..."` | Too broad; will fire on neighbour intents |
| `"Use this for git operations."` | Internal vocabulary, no user-phrase grounding |

## Writing tip

Watch yourself use the tool. Note the phrases you naturally say. Quote those.
If you'd say *"clean up the history before I push,"* that exact phrase belongs
in the `rebase-clean` skill's description.
