# Standalone Intel Mac distribution

`deploy/build_macos_app.py` builds an x86_64 PyInstaller onedir application, wraps it in a macOS bundle, and creates:

- `dist/WXCOMMAND-PRO.app`
- `dist/WXCOMMAND-PRO-macOS-Intel.zip` (preserves the app root and symlinks)
- `dist/WXCOMMAND-PRO-macOS-Intel.dmg` (app plus an Applications shortcut)

The app includes CPython, native extensions, Meshtastic/MeshCore transports, CoreBluetooth integration, local-network discovery, Jinja templates including demo mode, CA certificates and timezone data. The existing weather/alert logic and safe defaults are unchanged. The Mac entry point runs the existing application, and shows the Operator Center in its own native window (WebKit), with a Dock icon and standard menus. Links to outside sites open in the default browser. Closing the window keeps the server and alert broadcasting running; click the Dock icon to reopen it. A busy port fails startup rather than displaying another service. Bluetooth and local-network purpose strings are included in Info.plist.

## Build on Intel macOS

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r packaging/requirements-macos.txt
.venv/bin/python deploy/build_macos_app.py
.venv/bin/python deploy/verify_macos_bundle.py
```

AutoPilot uses Python 3.12 on `macos-15-intel` with x64 architecture. PyInstaller rejects incompatible native libraries. Build and verification failures block artifact upload and the aggregate release gate.

The verifier temporarily renames the checkout and restores it in a `finally` block. Run it with no other jobs using that checkout. It extracts the ZIP, mounts the DMG read-only, copies its app into a temporary Applications directory, unmounts it, then checks each relocated app. It checks ad-hoc signature integrity, all Mach-O architectures and linked library paths, and starts the bundled executable with an isolated home, minimal PATH and no inherited Python environment. The offline self-test imports native transport dependencies, compiles templates, checks certificates/time zones, serves `/healthz` and `/demo`, and exercises the non-transmitting preview API. It deliberately disables application lifespan, so it never starts radio discovery, weather polling or transmissions and does not touch operator settings.

## Publishing and safety

The existing main-only successful AutoPilot release workflow downloads the new `wxcommand-pro-macos-intel-standalone` artifact. The different artifact name prevents publishing the old checkout-dependent launcher as a standalone release. Both ZIP and DMG are required. They are published with the unchanged Pi source package and SHA256SUMS.txt. Existing run provenance checks, prerequisite jobs, prerelease status and immutable-release behavior remain in force. PR builds only upload Actions artifacts; they do not publish releases. Version-tag Docker/Windows publishing is unchanged.

The app is ad-hoc signed for bundle integrity, **not Developer ID signed or notarized**. A quarantined internet download may be blocked by Gatekeeper; use macOS Privacy & Security approval only after verifying the source and checksum. Do not disable Gatekeeper globally. Replacing the app leaves settings and backups outside the bundle intact. Closing the window does not stop the server; use **WXCOMMAND-PRO → Quit** (⌘Q).

## Acceptance boundaries

A passing build/self-test does not verify physical Meshtastic or MeshCore USB/BLE/TCP connections, Bluetooth permission prompts, weather delivery, radio failover, or Raspberry Pi installation. It also does not establish Finder/Gatekeeper behavior or macOS Tahoe 26.7.1 compatibility unless that particular test has actually been performed and recorded. Record OS version, build SHA, launch method and tested transports when doing acceptance tests.
