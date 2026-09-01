# Register Device Policy Host as a Windows service using bundled WinSW.
# Called by the Setup.exe; can also be run manually from the install folder.

param(
    [Parameter(Mandatory = $true)]
    [string]$AppDir,
    [string]$KidId = "emma",
    [string]$DisplayName = "Emma",
    [string]$ApiKey = "change-me-emma-device-key",
    [string]$ControlPlaneUrl = "http://192.168.1.10:8080",
    [string]$Bedtime = "21:00",
    [string]$ServiceName = "DevicePolicyHost"
)

$ErrorActionPreference = "Stop"
$AppDir = (Resolve-Path $AppDir).Path

New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "config") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "logs") | Out-Null

$configPath = Join-Path $AppDir "config\agent.yaml"
@"
kid_id: $KidId
display_name: $DisplayName
api_key: $ApiKey
control_plane_url: $ControlPlaneUrl

schedule:
  bedtime: "$Bedtime"
  timezone: America/New_York
  warnings_minutes: [15, 5, 1]

blocked_processes:
  - RobloxPlayerBeta.exe
  - steam.exe
  - steam

enforcement:
  grace_minutes: 5
  check_interval_seconds: 10

api:
  host: 0.0.0.0
  port: 8443
"@ | Set-Content -Path $configPath -Encoding utf8

$wrapper = Join-Path $AppDir "DevicePolicyHostService.exe"
if (-not (Test-Path $wrapper)) {
    Write-Error "WinSW wrapper not found: $wrapper"
}

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    & $wrapper stop
    & $wrapper uninstall
    Start-Sleep -Seconds 1
}

& $wrapper install
& $wrapper start

$watchdogScript = Join-Path $AppDir "install\watchdog.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$watchdogScript`" -ServiceName $ServiceName"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration ([TimeSpan]::MaxValue)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "DevicePolicyWatchdog" -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null

Write-Host "Service installed. Config: $configPath"
