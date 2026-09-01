# Restarts the agent service if it is not running
param([string]$ServiceName = "DevicePolicyHost")

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($null -eq $svc) { exit 0 }
if ($svc.Status -ne "Running") {
    Start-Service -Name $ServiceName
}
