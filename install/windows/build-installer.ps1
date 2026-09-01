# Build DevicePolicyHost-Setup.exe (single download-and-run installer).
# Run on Windows from repo root, or: .\install\windows\build-installer.ps1
# Requires: Python 3.10+ (to rebuild the agent bundle if missing)

function Find-ISCC {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$VendorDir = Join-Path $PSScriptRoot "vendor"
$WinSwUrl = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe"
$WinSwExe = Join-Path $VendorDir "WinSW-x64.exe"
$AgentExe = Join-Path $RepoRoot "dist\DevicePolicyHost\DevicePolicyHost.exe"
$Iscc = Find-ISCC

Write-Host "==> Ensuring WinSW wrapper..."
New-Item -ItemType Directory -Force -Path $VendorDir | Out-Null
if (-not (Test-Path $WinSwExe)) {
    Invoke-WebRequest -Uri $WinSwUrl -OutFile $WinSwExe -UseBasicParsing
}

if (-not (Test-Path $AgentExe)) {
    Write-Host "==> Building agent bundle..."
    & (Join-Path $PSScriptRoot "build.ps1")
    if (-not (Test-Path $AgentExe)) {
        Write-Error "Agent EXE missing after build: $AgentExe"
    }
}

if (-not $Iscc) {
    Write-Host "==> Installing Inno Setup..."
    $choco = Get-Command choco -ErrorAction SilentlyContinue
    if ($choco) {
        choco install innosetup -y --no-progress
        $Iscc = Find-ISCC
    }
    if (-not $Iscc) {
        $innoSetup = Join-Path $env:TEMP "innosetup-install.exe"
        $url = "https://github.com/jrsoftware/issrc/releases/download/is-7_1_0/innosetup-7.1.0-x64.exe"
        Invoke-WebRequest -Uri $url -OutFile $innoSetup -UseBasicParsing
        Start-Process -FilePath $innoSetup -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/ALLUSERS" -Wait
        $Iscc = Find-ISCC
    }
    if (-not $Iscc) {
        Write-Error "Inno Setup ISCC.exe not found after install"
    }
}

Write-Host "==> Compiling installer..."
Push-Location $RepoRoot
& $Iscc "install\windows\installer.iss"
Pop-Location

$Setup = Join-Path $RepoRoot "dist\DevicePolicyHost-Setup.exe"
if (-not (Test-Path $Setup)) {
    Write-Error "Installer not produced: $Setup"
}

Write-Host ""
Write-Host "Installer ready:"
Write-Host "  $Setup"
Write-Host ""
Write-Host "Copy that one file to the kid PC and run it as Administrator."
