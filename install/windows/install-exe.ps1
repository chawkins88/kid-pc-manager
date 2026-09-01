# Install the PyInstaller-built agent as a Windows service (run as Administrator)
# Requires: NSSM on PATH, dist/DevicePolicyHost/ from build.ps1

param(
    [string]$SourceDir = "",
    [string]$InstallDir = "C:\Program Files\DevicePolicyAgent",
    [string]$ConfigSource = "config\agent.yaml",
    [string]$ServiceName = "DevicePolicyHost"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

if (-not $SourceDir) {
    $SourceDir = Join-Path $RepoRoot "dist\DevicePolicyHost"
}
$SourceDir = Resolve-Path $SourceDir

$AgentExe = Join-Path $SourceDir "DevicePolicyHost.exe"
if (-not (Test-Path $AgentExe)) {
    Write-Error "Agent EXE not found at $AgentExe. Run build.ps1 first."
}

Write-Host "Installing Device Policy Agent (bundled EXE) to $InstallDir"

# Stop existing service if present
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    if (Get-Command nssm -ErrorAction SilentlyContinue) {
        nssm remove $ServiceName confirm
    }
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\config" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\logs" | Out-Null

# Copy bundled runtime (onedir folder contents)
Copy-Item -Recurse -Force "$SourceDir\*" $InstallDir

if (-not (Test-Path $ConfigSource)) {
    $ConfigSource = Join-Path $RepoRoot "config\agent.example.yaml"
    Write-Host "Using example config — edit $InstallDir\config\agent.yaml after install."
}
Copy-Item $ConfigSource "$InstallDir\config\agent.yaml" -Force

$AgentExe = Join-Path $InstallDir "DevicePolicyHost.exe"
$ConfigPath = Join-Path $InstallDir "config\agent.yaml"

if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    Write-Error "NSSM not found. Download from https://nssm.cc/ and add to PATH."
}

nssm install $ServiceName $AgentExe "-c" $ConfigPath
nssm set $ServiceName AppDirectory $InstallDir
nssm set $ServiceName DisplayName "Device Policy Host"
nssm set $ServiceName Description "Device policy enforcement service"
nssm set $ServiceName Start SERVICE_AUTO_START
nssm set $ServiceName AppStdout "$InstallDir\logs\stdout.log"
nssm set $ServiceName AppStderr "$InstallDir\logs\stderr.log"

$watchdogScript = Join-Path $PSScriptRoot "watchdog.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$watchdogScript`" -ServiceName $ServiceName"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration ([TimeSpan]::MaxValue)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "DevicePolicyWatchdog" -Action $action -Trigger $trigger -Principal $principal -Force

Start-Service $ServiceName
Write-Host "Installed and started $ServiceName"
Write-Host "Config: $ConfigPath"
