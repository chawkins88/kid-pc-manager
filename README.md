# Device Policy Agent

Cross-platform parental control agent for home LAN use. Runs on each kid's computer (Windows or Linux), shows bedtime warnings, closes blocked apps, and reports heartbeats to a parent control plane. If an agent stops reporting, you get alerted on the dashboard.

## Architecture

- **Agent** (`agent/`) — runs on each kid PC as a background service
- **Control plane** (`control_plane/`) — runs on your PC; dashboard + heartbeat monitoring
- **Profiles** (`control_plane/profiles/`) — one YAML file per kid/device

## Quick start (development)

### 1. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### 2. Configure a kid agent

```bash
cp config/agent.example.yaml config/agent.yaml
# Edit kid_id, api_key, control_plane_url, bedtime, blocked_processes
```

Set `control_plane_url` to your PC's LAN IP (e.g. `http://192.168.1.10:8080`).

### 3. Configure control plane profiles

Edit `control_plane/profiles/*.yaml` — set `device_ip` to each kid PC's LAN IP and matching `api_key`.

Generate a parent PIN hash:

```bash
python -m control_plane.main --set-pin your-secret-pin
# Set output as PARENT_PIN_HASH env var when starting control plane
```

### 4. Run

**On your PC (control plane):**

```bash
export PARENT_PIN_HASH='<bcrypt hash from above>'
python -m control_plane.main --host 0.0.0.0 --port 8080
```

Open http://localhost:8080 for the dashboard.

**On kid PC (agent):**

```bash
python -m agent.main -c config/agent.yaml
```

## What the MVP does

| Feature | Status |
|---------|--------|
| Bedtime warnings (15/5/1 min) | Yes |
| Kill blocked apps at bedtime | Yes |
| Grace period before hard enforcement | Yes |
| Heartbeat to control plane | Yes |
| Alert when agent goes offline | Yes |
| Push bonus time from dashboard | Yes |
| Windows + Linux | Yes |
| Parent PIN for admin actions | Yes |

## Blocked apps

Match by process name (case-insensitive):

```yaml
blocked_processes:
  - RobloxPlayerBeta.exe   # Windows Roblox
  - RobloxPlayer           # Linux Roblox
  - steam.exe              # Windows Steam
  - steam                  # Linux Steam
```

## Production install

### Windows

Kid account must be **Standard User** (not Administrator).

Download **`DevicePolicyHost-Setup.exe`** and run it as Administrator. The wizard asks for kid ID, API key, control plane URL, and bedtime, then installs the Windows service and watchdog. Python is not required on the kid PC.

After GitHub releases are set up:

```text
https://github.com/chawkins/windows-agent/releases/latest/download/DevicePolicyHost-Setup.exe
```

Until then, grab the built file from `dist/DevicePolicyHost-Setup.exe` (also copied onto the Windows build machine under `C:\Users\Administrator\src\windows-agent\dist\`).

To rebuild the installer on a Windows machine:

```powershell
.\install\windows\build-installer.ps1
```

That produces one file: `dist\DevicePolicyHost-Setup.exe`.

**Code signing:** Unsigned EXEs may trigger SmartScreen. Sign with your certificate (`signtool sign`) before distributing to kid PCs.

### Linux

Kid account should not have sudo. On the kid PC (as an adult with sudo):

```bash
curl -fsSL https://raw.githubusercontent.com/chawkins/windows-agent/master/install/linux/bootstrap.sh | sudo bash
```

That clones this repo, installs the agent under `/opt/device-policy-agent`, enables the systemd service, and writes `/etc/device-policy/agent.yaml` if it does not exist.

Then:

```bash
sudo nano /etc/device-policy/agent.yaml   # kid_id, api_key, control_plane_url, bedtime
sudo systemctl restart device-policy-agent
sudo systemctl status device-policy-agent
```

If the GitHub URL is different, set it first:

```bash
curl -fsSL https://raw.githubusercontent.com/YOU/windows-agent/master/install/linux/bootstrap.sh \
  | sudo DEVICE_POLICY_REPO=https://github.com/YOU/windows-agent.git bash
```

From a local clone instead of curl:

```bash
sudo bash install/linux/install.sh
```

## Security notes

- Kid PCs should use **Standard User** accounts — this is the most important tamper control.
- Change all default `api_key` values before deploying.
- Set `PARENT_PIN_HASH` on the control plane.
- Bind services to your home LAN; use firewall rules to restrict API access to your PC's IP.
- Optional TLS: uncomment `tls_cert` / `tls_key` in agent config.

## Project layout

```
agent/                  # Kid PC service
  core/                 # Scheduler, enforcer, API, heartbeat
  platform/             # Windows/Linux adapters
  ui/                   # Warning dialogs
control_plane/          # Parent dashboard
  profiles/             # Per-kid device profiles
  static/               # Web UI
install/                # OS-specific install scripts
config/                 # Agent config templates
```

## License

Private home use. Not intended for redistribution.
