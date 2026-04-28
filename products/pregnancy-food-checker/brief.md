# Product Brief: pregnancy-food-checker

**Status:** Drafting
**Date:** 2026-04-28
**Owner:** PM agent (Anis approves)

## One-liner

A private pregnancy food-safety web app for one user that checks a meal photo and highlights Germany-relevant pregnancy food concerns with a clear green/yellow/red result.

## Target user

One private user in Germany who wants quick, low-friction reassurance before eating during pregnancy.

## App vibe

Calm, colorful, and safety-first. The app should reduce anxiety, not amplify it. It should be direct about possible risks while making uncertainty obvious.

## Core promise

Upload or take a photo of food. The app uses a vision-capable LLM with a pregnancy-food-safety prompt to identify likely food items and flag anything that may be relevant for pregnancy in Germany.

The app is **not** a medical device, not diagnostic, and not a substitute for a doctor/midwife.

## MVP scope

- Google login for a single authorized user.
- Camera capture and gallery upload.
- Image preview before analysis.
- Send image to OpenAI vision model using a strict pregnancy food-safety prompt.
- Germany/EU-oriented risk framing.
- Colorful result:
  - **Green:** no obvious pregnancy-specific concern visible.
  - **Yellow:** check ingredient/preparation details before eating.
  - **Red:** avoid unless confirmed safe by source/clinician.
- Show:
  - likely detected foods,
  - pregnancy-relevant concerns,
  - what to check,
  - uncertainty level,
  - safe next action.
- Delete image immediately after analysis; store no image by default.
- Store minimal text history only if explicitly enabled later. MVP default: no history.
- Safety disclaimer on every result.

## Non-goals

- Nutrition, calories, macros, weight, or meal planning.
- Medical advice or diagnosis.
- Allergy detection.
- Guaranteeing safety from an image alone.
- Public/community use.
- Multi-user roles.
- Food database completeness.
- App Store/mobile app release.
- Paid subscriptions.

## Pregnancy food concern categories for MVP

The LLM prompt should specifically watch for visible or likely indicators of:

- raw or undercooked meat,
- raw fish / sushi / smoked fish ambiguity,
- raw or undercooked egg,
- unpasteurized milk/cheese risk,
- soft cheeses where pasteurization is unclear,
- deli meats/cold cuts where heating status is unclear,
- pâté/liver products,
- high-mercury fish risk,
- raw sprouts,
- alcohol-containing foods/drinks,
- buffet/leftover/storage-temperature ambiguity,
- unknown sauces/dressings that may contain raw egg or unpasteurized dairy.

## Draft LLM behavior contract

The model must:

- state uncertainty clearly,
- never claim a food is definitely safe from the image alone,
- prefer asking/checking over false reassurance,
- avoid diagnosing or giving medical instructions,
- provide practical next checks such as “confirm pasteurized,” “confirm fully cooked,” or “heat until steaming hot,”
- keep output concise.

## Draft result schema

```json
{
  "overall": "green | yellow | red",
  "summary": "short user-facing summary",
  "detected_foods": ["string"],
  "concerns": [
    {
      "item": "string",
      "severity": "green | yellow | red",
      "reason": "string",
      "what_to_check": "string"
    }
  ],
  "uncertainty": "low | medium | high",
  "safe_next_step": "string",
  "disclaimer": "Not medical advice. If unsure, ask your clinician/midwife."
}
```

## First 10 issue backlog

1. Create web app scaffold with TypeScript, auth placeholder, and CI.
2. Implement single-user Google login gate.
3. Implement camera/gallery image input and preview.
4. Implement OpenAI vision analysis API route with server-side key only.
5. Implement pregnancy food-safety prompt and JSON schema validation.
6. Implement green/yellow/red result UI.
7. Implement immediate image deletion/no-persistence behavior.
8. Add safety disclaimer and uncertainty UX.
9. Add tests for API schema, prompt contract, and no-image-storage behavior.
10. Add deployment/runbook checklist without deploying.

## Risks

- **Health/legal:** The product is pregnancy-health-adjacent. Must avoid medical-device positioning and must not provide definitive safety guarantees.
- **Privacy:** Food images may reveal personal/location context. MVP deletes images immediately and avoids storing history.
- **Technical:** Image interpretation can miss ingredients/preparation details invisible in photos.
- **Cost:** OpenAI vision API usage is paid. User has approved API direction in principle and will provide a key when needed; exact usage/cost guard still needs approval before real calls.
- **Auth/privacy:** Google login requires OAuth setup and careful secret handling.
- **Motivation decay:** If results are too cautious, the user may stop trusting it; if too confident, safety risk increases.

## Stack proposal

- **App:** Next.js + TypeScript.
- **UI:** Tailwind CSS.
- **Auth:** NextAuth/Auth.js with Google provider, restricted to one allowed Google account.
- **LLM:** OpenAI vision-capable model via server-side API route.
- **Storage:** No image storage in MVP. Optional text-only local history later.
- **Hosting:** local first; deployment target requires Anis approval.

## Decisions needed before code

- [ ] Confirm actual Google account email to allow.
- [ ] Confirm whether MVP may make paid OpenAI API calls during development, and any monthly/test budget.
- [ ] Confirm whether text result history should stay off for MVP.
- [ ] Confirm deployment target later, if any.
- [ ] Confirm final app name later; internal name is `pregnancy-food-checker`.
