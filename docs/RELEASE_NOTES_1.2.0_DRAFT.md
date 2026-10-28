# MeshWX v1.2.0 — Draft Release Notes

**Status: release candidate preparation only. Not published.**

## Highlights
- Operator Center with health cards, radio overview, recent transmissions
  and weather history.
- Display-only NWS warning polygons, simplified national visualization.
- Safe payload preview that never transmits.
- Compact, advanced and monitor display modes; configurable widget visibility.
- Radio connection history and opt-in backup failover improvements.
- Scheduled SQLite backups with integrity checks.
- Raspberry Pi systemd installation helper and standalone Intel Mac app ZIP and drag-and-drop DMG.
- Privacy-conscious diagnostic summary and improved installation guides.

## Security and operational notes
- New installations on Phase 4 bind HTTP to localhost by default.
  Explicit network exposure requires access-control review.
- Default fan-out radio behavior is preserved unless failover is enabled.
- An accepted transmit queue entry does not prove remote delivery.
- The map is informational only and is not used to decide broadcasts.
- This version has not passed full CI, device, or platform certification.

## Known limitations
- Geographic visualization is simplified and the NWS feed is capped.
- Mobile PWA lacks full offline functionality and complete app icons.
- Guided wizard, notification persistence and advanced timeline filters
  are not fully implemented.
- macOS bundle includes its runtime and dependencies; it is ad-hoc signed, not Developer ID signed or notarized. Physical-radio and target-OS acceptance require separate testing.
- Physical Meshtastic/MeshCore and restore testing remain outstanding.

## Before publishing
See `docs/RELEASE_CHECKLIST.md`. Do not tag or publish until all
release gates have passed.
