# Cost Policy

The system must not create variable costs without explicit Anis approval.

## Allowed without approval

- Local compute (CPU, GPU, RAM, disk on Anis's hardware)
- Existing ChatGPT subscription usage within the normal subscription quota
- Free GitHub features (Free plan limits)
- Local Docker, local Postgres, local Redis
- Free-tier experiments that do not require entering a payment method
- Public repos, public Actions on public repos (free)

## Requires Anis approval

- Apple Developer Program ($99/year)
- Expo Application Services paid plans or EAS build overages
- Domain purchase
- Hosting (Vercel paid, Railway, Fly.io, AWS, etc.)
- Hosted databases (Supabase paid, Neon paid, Postgres providers)
- Hosted auth providers (Auth0, Clerk, Supabase auth on paid)
- Analytics / observability products with cost
- Any usage-based AI API
- Buying templates, fonts, icons, stock assets
- App Store / Play Store publishing fees
- Long-running Codex sessions, parallel Codex agents, cloud Codex delegation

## Never allowed silently — explicit Anis confirmation required

- Pay-per-request LLM API (OpenAI API key, Anthropic API key, etc.)
- Usage-based AI API of any kind
- Recurring SaaS subscriptions
- Entering a payment method anywhere
- Production deployment that incurs hosting cost

## How agents interact with cost

- Every PR template requires the author to declare `cost: none | <list>`
- Tasks with cost implications get the `cost:approval-needed` label automatically
- The reviewer agent must check cost claims as part of every review
- Nightly reports include a "Cost risks" section (§22.5.8 of the source plan)

## Cost gates

The full machine-readable list of cost gates lives in `policies/cost-gates.yaml`. The orchestrator checks proposed actions against that file before execution.

See also: `policies/liveness-policy.md` §"Quota-aware degradation" for how the system behaves as Codex subscription quota is consumed during a billing window.
