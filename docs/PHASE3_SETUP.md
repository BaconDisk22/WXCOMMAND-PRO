# Phase 3 installation and validation

## Raspberry Pi 4
1. Install Python 3.11+, git and Bluetooth support on Raspberry Pi OS.
2. Clone the repository and create a virtual environment:
   `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
3. Confirm a USB, TCP or BLE radio works in Settings. The Bluetooth scanner operates on the Pi, not the browsing device.
4. Copy `deploy/meshwx.service` to `/etc/systemd/system/meshwx.service`, adjusting the user, working directory and Python executable paths.
5. Run `sudo systemctl daemon-reload && sudo systemctl enable --now meshwx`.
6. Inspect logs with `journalctl -u meshwx -f` and confirm reconnect after a power cycle.

## Intel Mac
1. Install Python 3.11+ and create a virtual environment:
   `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
2. Grant Bluetooth access to Terminal in System Settings → Privacy & Security → Bluetooth.
3. Run `chmod +x "deploy/Start MeshWX.command"` once, then double-click the launcher.
4. Test BLE discovery using the macOS UUID, USB serial and TCP separately.
5. The launcher opens a Terminal window; it is not a signed macOS .app bundle.

## Database backup
Use the SQLite backup API while MeshWX is running:
`python -m app.backup backup --database /path/to/meshwx.db --output /path/to/backup.db`
Stop MeshWX before restoring. Keep backups outside the application directory, protect them with filesystem permissions and periodically verify them.

## Pre-merge checks
- Run `python -m pip install -r requirements-dev.txt`
- Run `python -m compileall -q app`
- Run `python -m pytest -q tests`
- Verify the radio tools, settings and alert screens on mobile and desktop.
- Verify NOAA/NWS and IPAWS alert handling using a safe test environment; do not broadcast test alerts on live channels.
- Verify both protocols' USB, TCP and BLE behavior on real radios.
- Confirm that WiFi discovery only changes an unset Meshtastic TCP host when exactly one compatible announcement is found.
- Verify no duplicate broadcasts after connection loss.
- Review HTTP access control before exposing the service beyond a trusted LAN.

No physical radio or host platform has been certified by these instructions.


## Optional daily backups
Set `MESHWX_BACKUP_DIR` to a writable directory outside the application's
working directory before starting MeshWX. It performs a backup at startup and
every 24 hours, retaining the seven most recent snapshots. Backups contain
settings and operational data, so restrict directory permissions. Verify
restores offline before relying on backups.

## Optional primary/backup failover
In Radio Tools, enable the failover switch. When enabled, MeshWX tries enabled
radios in their configured order and stops after the first confirmed send.
This avoids intentional duplicate fan-out, but cannot guarantee exactly-once
delivery if a transport times out after a radio actually transmitted.
Leave disabled to preserve the existing broadcast-on-all-radios behavior.


## Standalone macOS application bundle
Use the Intel DMG or app ZIP from Releases. The app bundles its runtime and no longer depends on this checkout. See [Mac packaging](MACOS_PACKAGING.md) for building and validation. Developer ID signing, notarization and physical-radio acceptance remain separate.

## Release verification
The safe smoke check is `python -m app.smokecheck`. It imports the NWS,
IPAWS, Bluetooth and radio components but does not verify real transmissions.
Run all pytest tests, check GitHub Actions, and test failover using test
channels and actual hardware before tagging a release.
