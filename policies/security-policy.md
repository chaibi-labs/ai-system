# Security Policy

Personal does not mean unsafe. The studio operates with secrets, owns code that may eventually be public, and runs autonomous agents — discipline matters.

## Repo secrets — never commit

Add to `.gitignore` globally:

```
.env
.env.*
*.pem
*.key
secrets/
credentials/
service-account*.json
.codex/
.openai/
```

GitHub secret scanning must be enabled for every repo (Settings → Code security and analysis → Secret scanning).

## Secrets storage and injection

Secrets live **outside** any repo, owned by the user only:

```
~/.ai-system/secrets/.env       # chmod 600
~/.ai-system/secrets/codex/     # Codex CLI session cache
```

Required at MVP — and only these:

```
GITHUB_TOKEN     # PAT scoped to: repo, project, workflow (only if needed)
                 # NOT: admin:org, delete_repo, packages, gist
GITHUB_USERNAME  # for gh CLI fallback
```

Codex authenticates via ChatGPT login (subscription-based). The presence of any `OPENAI_API_KEY` on disk is a **configuration error** — it implies pay-per-request usage which `policies/cost-policy.md` forbids.

## Agent forbidden paths

Agents may not read these directories or files (the orchestrator enforces this with a path-filter at tool invocation time):

```
~/.ssh
~/.aws
~/.config/gcloud
~/.config/azure
~/.gnupg
~/.ai-system/secrets/
.env
.env.*
secrets/
```

## Token rotation

- `GITHUB_TOKEN`: rotate every 90 days. The orchestrator emits a rotation reminder issue 7 days before expiry.
- Codex session: re-auth when CLI prompts. Do not script around the prompt.

## Anti-patterns to refuse

- `.env` files inside any product repo — wrong directory, even with `.gitignore`.
- Secrets in shell history — use `read -s` or `pass` for one-off use.
- Sharing one token across products — each product repo gets its own scoped PAT.
- Sending secret values through prompts to any model (local or Codex). Prompts may reference variable names but not values.

## Publishing safety

Publishing requires:

- Release issue with cost + privacy + rollback checklist
- Security review complete
- Anis approval recorded

See `policies/release-policy.md` for the full release flow.
