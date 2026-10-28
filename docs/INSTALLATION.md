# MeshWX Installation and Operations

> Phase 4 draft. These steps have not been verified on the user's Pi or Mac.
> Do not use a mesh radio as a replacement for official emergency alerting.

## Raspberry Pi 4
1. Install a current Raspberry Pi OS release and Python 3.11 or later.
2. Install system dependencies: `sudo apt update && sudo apt install -y python3-venv python3-pip git bluetooth bluez`.
3. Clone MeshWX1, then from the checkout run:
   `python3 -m venv .venv`
   `.venv/bin/python -m pip install -r requirements.txt`
4. Check that `.venv/bin/python -m app.smokecheck` completes successfully.
5. For USB radios, verify your user has access to the serial device. Use the
   distribution's supported serial group, typically `dialout`, and re-login.
6. Run `bash deploy/install_pi.sh`. It installs and enables a systemd service,
   and creates a private backup directory in your home folder.
7. Verify with `sudo systemctl status meshwx` and
   `journalctl -u meshwx -n 100 --no-pager`.
8. After confirming the configured HTTP bind address and port, open
   `/operator` from a trusted browser.
9. Reboot and confirm the service restarts, NWS polling resumes, and test
   radios reconnect before enabling live transmissions.

**Security:** the web interface contains settings and transmit operations.
The example service should not be exposed to the public Internet. Prefer
localhost or a trusted network protected by access controls.

## Intel Mac (including Intel Tahoe)
1. Download the standalone Intel DMG from GitHub Releases.
2. Drag `WXCOMMAND-PRO.app` to Applications and open it.
3. The Operator Center opens in its own window. Closing it keeps the server running; click the Dock icon to reopen, ⌘Q to quit.
4. Grant Bluetooth and local-network access when macOS requests it.
5. Keep dry-run enabled until actual radios have been checked on a dedicated test channel.

Python and dependencies are bundled. Settings remain in `~/Library/Application Support/WXCOMMAND-PRO` (existing MeshWX databases are still recognized), outside the app. Startup logs are in `~/Library/Logs/WXCOMMAND-PRO/desktop.log`.

The bundle is ad-hoc signed, not Developer ID signed or notarized. Gatekeeper may require explicit approval through Privacy & Security. See [Mac packaging](MACOS_PACKAGING.md) for build instructions and verification limits.

## Updating
1. Back up the database before changing versions.
2. Review release notes and update your checkout with `git pull`.
3. Update dependencies: `.venv/bin/python -m pip install -r requirements.txt`.
4. Run smoke checks and tests.
5. On the Pi, restart with `sudo systemctl restart meshwx`.
   On Mac, quit and relaunch MeshWX.app.
6. Confirm NWS polling, radios, logs and backups before resuming broadcasts.

The existing app Settings screen also provides an update checker. An
automatic updater is intentionally not enabled, to avoid silently replacing
a running emergency alert system.

## Troubleshooting
- **Radio offline:** check power, USB permissions, Bluetooth access,
  network reachability and the configured radio connection type.
- **Weather feed stale:** inspect the Operator Center, network connectivity
  and NWS request errors. Do not assume the absence of alerts means safety.
- **Broadcasts missing:** inspect Transmit Log and test channel settings.
  A radio accepting a packet is not proof a remote node received it.
- **High queue depth:** inspect transport status and reduce unnecessary sends.
- **Service exits:** inspect `journalctl -u meshwx -e`.
- **Backup issues:** verify `MESHWX_BACKUP_DIR` permissions and free disk space.
- **Diagnostics:** open `/operator`, enable Advanced, and select Refresh
  diagnostics. Do not share logs containing private device identifiers.

## Release acceptance
See `docs/PHASE3_ACCEPTANCE.md`. Real radio, platform, and restoration tests
must pass before a production release.
