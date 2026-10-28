# MeshWX v1.2.0 Release Candidate — NOT RELEASED

## Automated acceptance
- [ ] Python 3.11, 3.12, 3.13 CI jobs pass.
- [ ] `python -m compileall -q app` passes.
- [ ] `python -m app.smokecheck` passes.
- [ ] `python -m pytest -q tests` passes.
- [ ] API routes and responsive UI tested in desktop and mobile browsers.

## Security
- [x] Default HTTP host set to 127.0.0.1 on Phase 4 branch.
- [ ] Review authentication for all settings, profile, radio and manual send routes.
- [ ] Verify CSRF protection for state-changing endpoints.
- [ ] Verify secrets and radio identifiers never appear in diagnostics.
- [ ] Verify NWS response handling, request timeouts and geographic accuracy.
- [ ] Confirm reverse-proxy configuration before any remote access.
- [ ] Review third-party dependencies and license compliance.

## Hardware and data
- [ ] Raspberry Pi 4 boot, restart, backup and offline restore verified.
- [ ] Intel Mac standalone ZIP and DMG tested on actual target hardware, including Finder launch, native window, Dock reopen, ⌘Q quit, and Gatekeeper approval.
- [ ] Meshtastic and MeshCore USB, TCP, BLE tests completed where supported.
- [ ] Failover tested without duplicate sends on test channels.
- [ ] NWS/IPAWS filter, dedupe, cancellation and expiration behavior verified.
- [ ] All tests conducted with dry run enabled or dedicated test channels.

## GitHub
- [ ] Phase 3 PR #3 CI green, reviewed and merged.
- [ ] Phase 4 PR #4 rebased onto main after Phase 3 merge.
- [ ] Phase 4 CI green, reviewed and merged.
- [ ] Version updated from 1.1.2 to 1.2.0 after passing gates.
- [ ] Changelog and release notes reviewed.
- [ ] Git tag v1.2.0 created only from verified main.
- [ ] Release assets tested and published.

Do not claim production readiness until every critical gate passes.
