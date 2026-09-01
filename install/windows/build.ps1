# Build DevicePolicyHost.exe on Windows (run from repo root in PowerShell)
# Requires: Python 3.10+, pip install -r requirements-build.txt

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

Write-Host "Building Device Policy Agent EXE..."
Push-Location $RepoRoot

python -m pip install -q -r requirements.txt -r requirements-build.txt -e .

pyinstaller `
    --noconfirm `
    --clean `
    install/windows/device-policy-agent.spec

Pop-Location

$OutDir = Join-Path $RepoRoot "dist\DevicePolicyHost"
$Exe = Join-Path $OutDir "DevicePolicyHost.exe"

if (-not (Test-Path $Exe)) {
    Write-Error "Build failed — $Exe not found"
}

Write-Host ""
Write-Host "Build complete:"
Write-Host "  $Exe"
Write-Host ""
Write-Host "Next: run install-exe.ps1 as Administrator on the kid PC"
