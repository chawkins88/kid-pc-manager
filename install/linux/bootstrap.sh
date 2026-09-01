#!/usr/bin/env bash
# Device Policy Agent — Linux bootstrap (safe to pipe: curl ... | sudo bash)
set -euo pipefail

# Override when the GitHub remote is not the default:
#   sudo DEVICE_POLICY_REPO=https://github.com/YOU/windows-agent.git bash -c \
#     'curl -fsSL https://raw.githubusercontent.com/YOU/windows-agent/master/install/linux/bootstrap.sh | bash'
REPO_URL="${DEVICE_POLICY_REPO:-https://github.com/chawkins/windows-agent.git}"
REPO_REF="${DEVICE_POLICY_REF:-master}"
INSTALL_DIR="/opt/device-policy-agent"
CONFIG_DIR="/etc/device-policy"
CONFIG_FILE="$CONFIG_DIR/agent.yaml"
SRC_DIR="/tmp/device-policy-agent-src"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run as root: curl -fsSL <url> | sudo bash" >&2
    exit 1
fi

need_pkg() {
    command -v "$1" >/dev/null 2>&1
}

echo "Installing packages if missing (git, python3, venv, pip)..."
if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    pkgs=()
    need_pkg git || pkgs+=(git)
    need_pkg python3 || pkgs+=(python3)
    dpkg -s python3-venv >/dev/null 2>&1 || pkgs+=(python3-venv)
    dpkg -s python3-pip >/dev/null 2>&1 || pkgs+=(python3-pip)
    if ((${#pkgs[@]})); then
        apt-get update -qq
        apt-get install -y "${pkgs[@]}"
    fi
elif command -v dnf >/dev/null 2>&1; then
    dnf install -y git python3 python3-pip python3-virtualenv
elif command -v yum >/dev/null 2>&1; then
    yum install -y git python3 python3-pip
else
    echo "Install git and python3 (with venv) then re-run." >&2
    need_pkg git && need_pkg python3 || exit 1
fi

echo "Fetching $REPO_URL ($REPO_REF)..."
rm -rf "$SRC_DIR"
git clone --depth 1 --branch "$REPO_REF" "$REPO_URL" "$SRC_DIR"

echo "Installing Device Policy Agent to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$INSTALL_DIR/logs"
cp -r "$SRC_DIR/agent" "$SRC_DIR/requirements.txt" "$SRC_DIR/pyproject.toml" "$INSTALL_DIR/"

cd "$INSTALL_DIR"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

if [[ ! -f "$CONFIG_FILE" ]]; then
    cp "$SRC_DIR/config/agent.example.yaml" "$CONFIG_FILE"
    echo "Created $CONFIG_FILE — edit kid_id, api_key, and control_plane_url."
fi

cp "$SRC_DIR/install/linux/device-policy-agent.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable device-policy-agent
systemctl restart device-policy-agent

rm -rf "$SRC_DIR"

echo
echo "Installed. Status:"
systemctl status device-policy-agent --no-pager || true
echo
echo "Next: sudo nano $CONFIG_FILE"
echo "Then: sudo systemctl restart device-policy-agent"
