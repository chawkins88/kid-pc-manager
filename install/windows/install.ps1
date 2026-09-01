# Device Policy Agent — Windows install (run as Administrator)
# Requires: Python 3.11+, NSSM (https://nssm.cc/)

param(
    [string]$InstallDir = "C:\Program Files\DevicePolicyAgent",
    [string]$ConfigSource = "config\agent.yaml",
    [string]$ServiceName = "DevicePolicyHost"
)

$ErrorActionPreference = "Stop"

Write-Host "Installing Device Policy Agent to $InstallDir"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Recurse -Force agent, config, requirements.txt $InstallDir

Push-Location $InstallDir
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
Pop-Location

if (-not (Test-Path $ConfigSource)) {
    Copy-Item config\agent.example.yaml config\agent.yaml
    Write-Host "Created config\agent.yaml from example — edit before starting."
}

Copy-Item $ConfigSource "$InstallDir\config\agent.yaml" -Force

$pythonExe = "$InstallDir\venv\Scripts\python.exe"
$agentScript = "$InstallDir\agent\main.py"

# NSSM must be on PATH
if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    Write-Error "NSSM not found. Download from https://nssm.cc/ and add to PATH."
}

nssm install $ServiceName $pythonExe $agentScript "-c" "$InstallDir\config\agent.yaml"
nssm set $ServiceName AppDirectory $InstallDir
nssm set $ServiceName DisplayName "Device Policy Host"
nssm set $ServiceName Description "Device policy enforcement service"
nssm set $ServiceName Start SERVICE_AUTO_START
nssm set $ServiceName AppStdout "$InstallDir\logs\stdout.log"
nssm set $ServiceName AppStderr "$InstallDir\logs\stderr.log"
New-Item -ItemType Directory -Force -Path "$InstallDir\logs" | Out-Null

# Watchdog scheduled task — restarts service if stopped
$watchdogScript = Join-Path $PSScriptRoot "watchdog.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$watchdogScript`" -ServiceName $ServiceName"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration ([TimeSpan]::MaxValue)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "DevicePolicyWatchdog" -Action $action -Trigger $trigger -Principal $principal -Force

Start-Service $ServiceName
Write-Host "Installed and started $ServiceName"
