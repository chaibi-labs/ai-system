# GitHub Policy

All product changes happen through GitHub.

## Branches

```
main         protected; PR required; no force push; no deletion
feature/*    new features
fix/*        bug fixes
meta/*       changes to ai-system itself (prompts, policies, workflows, scripts)
chore/*      maintenance (deps, tooling, formatting)
```

Naming: `feature/<short-kebab-description>` or `feature/issue-<N>-<short>` for traceability.

## Pull requests

- PR is required to merge to `main`.
- PR body must follow the template in `templates/pr_template.md`:
  - Summary (1-3 lines)
  - Linked issue (`Closes #N`)
  - Tests run (command + result)
  - Risk (low / medium / high — with reasoning)
  - Cost flags (none or explicit list)
  - Decisions needed from Anis (if any)
  - Screenshots for any UI change
- The `task_spec` (if applicable) is attached as a code block in the PR body or as a linked file.
- Linear history is required (rebase, not merge commit).

## Agents may

- Create issues
- Update Project board (status, fields, labels)
- Create branches under any allowed prefix
- Commit to feature branches
- Open PRs
- Comment on PRs
- Close issues they own (after merge)

## Product Owner merge authority

Each product may name exactly one Product Owner agent in `products/<name>.yaml` via
`po_agent`. The Product Owner is repo-scoped: it may only act with merge authority
inside the assigned product repository.

The Product Owner may merge PRs for its assigned product repo only when all of
these gates pass:

- PR targets the assigned product repo and protected `main` branch.
- PR uses the normal PR workflow from an allowed branch prefix.
- Reviewer verdict is approve, or all reviewer blockers are explicitly resolved.
- CI and required acceptance checks are green.
- PR body includes summary, linked issue if applicable, tests run, risk, cost
  flags, and decisions needed.
- No unresolved blocker comments remain.
- No new cost, paid service, external account, secret, privacy/legal, release,
  publishing, branch-protection, or governance decision is introduced.
- Diff is small and one-concern.

If any gate fails, the Product Owner comments with the failed gate and does not
merge.

## Agents may not

- Merge PRs, except for an assigned Product Owner merging an eligible PR in its
  assigned product repo under the Product Owner merge gates above, or unless
  `auto-merge` is explicitly enabled later by Anis for a labeled class.
- Delete repositories or branches with history
- Change branch protection rules
- Force push to `main`
- Bypass the PR workflow
- Push directly to `main` (even though admins technically can — the agents are configured not to)

## Org / repo conventions

- Org: `chaibi-labs`
- ai-system is **public** (required for branch protection on Free plan; no secrets in repo by design)
- Product repos visibility decided per product (default: private; switch to public if branch protection is needed and Pro is not in use)

## Failure modes

- If a push fails because of branch protection, the agent does NOT bypass — it opens a PR instead and links it back to the original issue.
- If CI is failing on `main`, all `coder.execute` work for that repo pauses (cascade halt — see `policies/liveness-policy.md` §22.5.7). The only allowed work is a fix branch.
