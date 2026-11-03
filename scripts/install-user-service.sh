#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "${HOME}/.config/systemd/user"
cp "${ROOT}/systemd/prakverse.service" "${HOME}/.config/systemd/user/prakverse.service"
systemctl --user daemon-reload
echo "Installed user service. Start it with:"
echo "  systemctl --user enable --now prakverse.service"
