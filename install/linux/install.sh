#!/usr/bin/env bash
# Device Policy Agent — Linux install from a local clone (run as root).
# For curl | bash, use bootstrap.sh instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INSTALL_DIR="/opt/device-policy-agent"
CONFIG_DIR="/etc/device-policy"
CONFIG_FILE="$CONFIG_DIR/agent.yaml"

echo "Installing Device Policy Agent to $INSTALL_DIR"

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR"
cp -r "$REPO_ROOT/agent" "$REPO_ROOT/requirements.txt" "$REPO_ROOT/pyproject.toml" "$INSTALL_DIR/"

cd "$INSTALL_DIR"
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

if [[ ! -f "$CONFIG_FILE" ]]; then
    cp "$REPO_ROOT/config/agent.example.yaml" "$CONFIG_FILE"
    echo "Created $CONFIG_FILE — edit before relying on enforcement."
fi

cp "$SCRIPT_DIR/device-policy-agent.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable device-policy-agent
systemctl restart device-policy-agent

echo "Installed. Status:"
systemctl status device-policy-agent --no-pager || true
