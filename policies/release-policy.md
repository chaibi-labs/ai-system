# Release Policy

A release means making something available to users — anyone other than Anis seeing or using the product.

## Requires Anis approval

- Production deploy of any kind
- App Store submission
- TestFlight distribution
- Play Store submission
- Public website launch (any domain pointing at the app)
- Paid service activation tied to a release (auth, hosting, analytics)
- Domain connection / DNS change

## Release checklist (every release)

Before requesting Anis approval:

- [ ] All tests pass on `main` (CI green for the merge commit)
- [ ] Security review complete (`policies/security-policy.md` checklist)
- [ ] Privacy implications reviewed (data collected, data retained, third-party sharing)
- [ ] Costs listed (any new recurring or usage-based cost)
- [ ] Rollback plan written (what to revert and how)
- [ ] Release notes drafted
- [ ] Anis approval recorded as a comment on the release issue

## Forbidden without approval

- Auto-release on merge
- Auto-deploy to a publicly reachable host
- Auto-publish to any app store
- Skipping the release issue / checklist for "small" changes

The checklist exists because the cost of one accidental publish is much higher than the cost of an extra approval round.
