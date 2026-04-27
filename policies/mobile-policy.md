# Mobile Policy

Mobile work has unique cost and process constraints — calling them out explicitly so they are never "discovered" by the studio mid-flow.

## Stack defaults

- **iOS / Android:** Expo + React Native + TypeScript
- **State:** Zustand or React Query (decide per product)
- **Local data:** SQLite via `expo-sqlite`
- **Backend:** none until proven needed; FastAPI + Postgres if/when sync or accounts are required

## Hardware reality

- Native iOS development requires a Mac (Xcode, code signing). Most source work happens in WSL on the Windows machine; iOS-native build/signing/submission happens on Anis's Mac OR via EAS build (cost-gated).
- Android can be built fully on Windows / WSL.

## Cost gates specific to mobile

| Action                          | Gate              |
|---------------------------------|-------------------|
| Apple Developer Program ($99/y) | `ask_first`       |
| EAS paid build                  | `ask_first`       |
| TestFlight distribution         | `ask_first`       |
| App Store submission            | `never_silently`  |
| Play Store submission           | `never_silently`  |
| Push notification provider      | `ask_first`       |
| Paid food/fitness DB API        | `ask_first`       |
| Paid icon / asset packs         | `ask_first`       |

## Privacy defaults

- Local-first storage by default. No cloud sync until Anis approves.
- No analytics until Anis approves an analytics provider.
- No third-party data sharing without Anis approval.
- No account / auth provider until Anis approves.
- No collection of personally identifiable information until Anis approves.

## Build / release flow (when reached)

1. Mobile feature complete on `main`, all tests pass.
2. Ops agent prepares build instructions (no actual build yet).
3. Release issue opened with cost / privacy / rollback checklist.
4. Anis approves → Ops agent runs the build (or hands instructions to Anis if EAS quota gated).
5. Anis distributes (TestFlight invitation, side-load, or store submission).

## Forbidden without approval

- Bumping the app version for release
- Generating signing keys for production
- Connecting an Apple Developer account
- Submitting to TestFlight or any store
- Adding any cloud sync / push / analytics SDK
