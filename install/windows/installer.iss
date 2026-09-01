; Produces a single DevicePolicyHost-Setup.exe — download and run as Administrator.
; Bundles the agent, WinSW service wrapper, watchdog, and a config wizard.
; Build: .\install\windows\build-installer.ps1

#define RepoRoot "..\\.."
#define BuildDir RepoRoot + "\\dist\\DevicePolicyHost"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName=Device Policy Host
AppVersion=0.1.0
AppPublisher=Home LAN
DefaultDirName={autopf}\DevicePolicyAgent
DefaultGroupName=Device Policy Host
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputBaseFilename=DevicePolicyHost-Setup
OutputDir={#RepoRoot}\dist
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayName=Device Policy Host
MinVersion=10.0
SetupLogging=yes

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "vendor\WinSW-x64.exe"; DestDir: "{app}"; DestName: "DevicePolicyHostService.exe"; Flags: ignoreversion
Source: "service.xml"; DestDir: "{app}"; DestName: "DevicePolicyHostService.xml"; Flags: ignoreversion
Source: "watchdog.ps1"; DestDir: "{app}\install"; Flags: ignoreversion
Source: "install-service.ps1"; DestDir: "{app}\install"; Flags: ignoreversion

[Run]
Filename: "powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\install\install-service.ps1"" -AppDir ""{app}"" -KidId ""{code:GetKidId}"" -DisplayName ""{code:GetDisplayName}"" -ApiKey ""{code:GetApiKey}"" -ControlPlaneUrl ""{code:GetControlPlaneUrl}"" -Bedtime ""{code:GetBedtime}"""; \
    StatusMsg: "Registering Windows service..."; Flags: runhidden waituntilterminated

[UninstallRun]
Filename: "{app}\DevicePolicyHostService.exe"; Parameters: "stop"; Flags: runhidden waituntilterminated; RunOnceId: "StopService"
Filename: "{app}\DevicePolicyHostService.exe"; Parameters: "uninstall"; Flags: runhidden waituntilterminated; RunOnceId: "UninstallService"
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""Unregister-ScheduledTask -TaskName DevicePolicyWatchdog -Confirm:$false -ErrorAction SilentlyContinue"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveWatchdog"

[Icons]
Name: "{group}\Edit agent config"; Filename: "notepad.exe"; Parameters: """{app}\config\agent.yaml"""
Name: "{group}\Uninstall Device Policy Host"; Filename: "{uninstallexe}"

[Messages]
WelcomeLabel2=This installs Device Policy Host as a Windows service.%n%nNo Python install is required. You will be asked for this kid's settings on the next screens.

[Code]
var
  ConfigPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  ConfigPage := CreateInputQueryPage(wpSelectDir,
    'Kid device settings',
    'Written to agent.yaml and used by the service.',
    'Match the API key to this kid''s profile on the control plane.');
  ConfigPage.Add('Kid ID:', False);
  ConfigPage.Add('Display name:', False);
  ConfigPage.Add('API key:', False);
  ConfigPage.Add('Control plane URL:', False);
  ConfigPage.Add('Bedtime (HH:MM):', False);
  ConfigPage.Values[0] := 'emma';
  ConfigPage.Values[1] := 'Emma';
  ConfigPage.Values[2] := 'change-me-emma-device-key';
  ConfigPage.Values[3] := 'http://192.168.1.10:8080';
  ConfigPage.Values[4] := '21:00';
end;

function GetKidId(Param: String): String;
begin
  Result := ConfigPage.Values[0];
end;

function GetDisplayName(Param: String): String;
begin
  Result := ConfigPage.Values[1];
end;

function GetApiKey(Param: String): String;
begin
  Result := ConfigPage.Values[2];
end;

function GetControlPlaneUrl(Param: String): String;
begin
  Result := ConfigPage.Values[3];
end;

function GetBedtime(Param: String): String;
begin
  Result := ConfigPage.Values[4];
end;
