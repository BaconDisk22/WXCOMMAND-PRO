# Phase 3 acceptance checklist

Do not merge this branch until these checks are completed. Automated tests
do not prove radio transmissions or correct live weather alert handling.

## CI
- [ ] Python 3.11, 3.12 and 3.13 workflow jobs pass.
- [ ] No-transmit smoke check passes.
- [ ] All tests in `tests/` pass.

## Radios (use test channels only)
- [ ] Meshtastic USB reconnect after unplug/replug.
- [ ] MeshCore USB reconnect after unplug/replug.
- [ ] Meshtastic BLE reconnect after out-of-range and return.
- [ ] Network discovery finds a known Meshtastic TCP radio.
- [ ] TCP reconnect works after router/radio restart.
- [ ] Default fan-out sends once per enabled radio.
- [ ] Failover enabled sends only once when primary succeeds.
- [ ] Failover enabled sends via backup when primary is offline.
- [ ] Both radios offline reports failure, never false success.
- [ ] Verify logs show actual queue acceptance; do not equate it with
  delivery acknowledgement by remote recipients.

## NWS/IPAWS
- [ ] NWS filters by monitored zone and severity.
- [ ] Updates/cancellations and duplicate suppression checked.
- [ ] Expired and stale warnings never broadcast.
- [ ] IPAWS test/exercise alerts stay on test channels.
- [ ] IPAWS geographic scope and live-alert policy explicitly reviewed.
- [ ] Polling errors and upstream outages are visible.

## Backups
- [ ] MESHWX_BACKUP_DIR configured on target host.
- [ ] Backup file passes PRAGMA quick_check.
- [ ] Backup retention keeps only newest seven copies.
- [ ] Offline restore tested to a disposable database.
- [ ] Restart with restored DB tested, with radio TX disabled.

## Release
- [ ] Raspberry Pi 4 systemd startup and reboot tested.
- [ ] Intel Mac launch tested.
- [ ] Review security of configuration-changing API routes.
- [ ] Merge Phase 3 only after required checks pass.
