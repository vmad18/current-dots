#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if (( EUID != 0 )); then
    exec sudo -- bash "$PWD/install.sh"
fi
install -o root -g root -m 0755 battery-power-mode /usr/local/sbin/battery-power-mode
install -o root -g root -m 0644 battery-power-mode.service battery-power-mode.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now battery-power-mode.timer
systemctl start battery-power-mode.service
systemctl --no-pager status battery-power-mode.timer
