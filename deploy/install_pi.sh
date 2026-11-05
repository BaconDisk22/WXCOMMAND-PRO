#!/usr/bin/env bash
# Run from a Raspberry Pi checkout after reviewing service paths.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ "$(uname -s)" != "Linux" ]; then echo "This installer requires Linux."; exit 1; fi
if ! command -v systemctl >/dev/null; then echo "systemd is required."; exit 1; fi
if [ ! -x .venv/bin/python ]; then echo "Missing .venv. See docs/INSTALLATION.md"; exit 1; fi
USER_NAME="$(id -un)"
BACKUPS="$HOME/meshwx-backups"
mkdir -p "$BACKUPS"
chmod 700 "$BACKUPS"
SERVICE="$ROOT/deploy/meshwx.service"
echo "Installing MeshWX for $USER_NAME from $ROOT"
echo "Service will bind to the host configured in MeshWX settings."
sudo sed -e "s|^User=.*|User=$USER_NAME|" \
  -e "s|^WorkingDirectory=.*|WorkingDirectory=$ROOT|" \
  -e "s|^ExecStart=.*|ExecStart=$ROOT/.venv/bin/python -m app.main|" \
  -e "s|^Environment=MESHWX_BACKUP_DIR=.*|Environment=MESHWX_BACKUP_DIR=$BACKUPS|" \
  "$SERVICE" | sudo tee /etc/systemd/system/meshwx.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now meshwx.service
sudo systemctl --no-pager status meshwx.service
