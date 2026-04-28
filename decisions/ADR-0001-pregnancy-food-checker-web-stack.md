# ADR-0001: pregnancy-food-checker web stack

**Status:** Accepted
**Date:** 2026-04-28
**Deciders:** Anis (Vega/architect proposed)

## Context

The product is a private single-user web app that accepts food images, sends them to a vision-capable LLM, and returns pregnancy food-safety concerns for Germany. It needs camera/gallery input, Google login, server-side secret handling for the OpenAI API key, and privacy-by-default image deletion. It does not need native app distribution for MVP.

## Decision

Use a Next.js + TypeScript web app with Tailwind CSS, Auth.js/NextAuth Google provider restricted to one allowed account, and a server-side API route for OpenAI vision analysis. Store no images in MVP; process the uploaded image in memory/request scope and discard immediately after analysis. Keep deployment local until Anis explicitly approves a hosting target.

## Consequences

- Easier: fast web MVP, mobile browser camera/gallery support, server-side API key isolation, straightforward CI.
- Easier: Google login can gate the app without building a custom auth system.
- Harder: requires Google OAuth setup later; agents must not create the external OAuth app/account without Anis approval.
- Harder: OpenAI vision calls are paid; development needs explicit budget guard before live API use.
- Risk: browser camera behavior differs across mobile devices; QA needs mobile browser checks.
- Risk: no image storage limits auditability/debugging; this is intentional for privacy.
