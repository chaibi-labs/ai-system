# Design Brief: pregnancy-food-checker

**Status:** Drafting
**Date:** 2026-04-28

## Design goal

Make pregnancy food-risk checking feel calm, fast, and legible. The user should get a clear color-coded answer while understanding uncertainty.

## Primary flow

1. User opens app.
2. Google login if not authenticated.
3. Home screen shows two primary actions:
   - Take photo
   - Upload image
4. User previews selected image.
5. User taps “Check food”.
6. Loading state explains: “Checking visible food and pregnancy-relevant concerns.”
7. Result screen shows green/yellow/red summary and detailed concerns.
8. User can discard result and start over.

## Screens

### 1. Login gate

- Minimal page.
- Product name placeholder: Pregnancy Food Checker.
- CTA: “Continue with Google”.
- Small privacy note: “Private single-user app. Images are deleted after analysis.”

### 2. Home / capture

- Friendly headline: “Check a meal before eating.”
- Two large buttons:
  - “Take photo”
  - “Upload image”
- Secondary note: “Best results: clear photo, include sauces/labels when possible.”

### 3. Preview

- Image preview card.
- CTA: “Check food”.
- Secondary action: “Choose another”.
- Reminder: “Image is sent for analysis, then deleted.”

### 4. Result

Top card:

- Green: “No obvious pregnancy-specific concern visible.”
- Yellow: “Check details before eating.”
- Red: “Avoid unless confirmed safe.”

Sections:

- Likely detected foods.
- Things to check.
- Concern cards.
- Uncertainty badge.
- Safety disclaimer.

### 5. Error / unclear image

- Yellow neutral state.
- “I can’t confidently identify enough from this image.”
- Suggestions: retake photo, include packaging/label, check preparation details.

## Visual style

- Calm medical-adjacent, not hospital sterile.
- Soft background, high-contrast cards.
- Use color sparingly but clearly:
  - Green: safe/no obvious issue.
  - Yellow: check/uncertain.
  - Red: avoid/high concern.
- Rounded cards, large tap targets, mobile-first responsive layout.

## Component list

- `LoginGate`
- `ImageInput`
- `ImagePreviewCard`
- `AnalyzeButton`
- `LoadingState`
- `RiskBadge`
- `ResultSummaryCard`
- `DetectedFoodsList`
- `ConcernCard`
- `UncertaintyBadge`
- `DisclaimerBox`
- `ErrorState`

## Interaction details

- Disable analyze button while uploading/analyzing.
- Do not auto-submit image immediately after capture; always show preview first.
- If analysis returns invalid JSON, show a yellow error state and ask user to retry.
- Result copy must never say “safe to eat” as a guarantee. Use “no obvious concern visible” instead.

## Motion

- Subtle only.
- Loading spinner or pulsing dot.
- Result card fades in.
- No gamification/confetti; this is safety-related.

## Accessibility

- Color must not be the only signal: include labels Green/Yellow/Red and icons/text.
- Buttons should be large enough for mobile use.
- Result content should be readable in one hand on a phone.
