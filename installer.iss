; Inno Setup 脚本 —— 串口调试助手 安装程序
; 说明：用户可自选安装位置；默认按用户目录安装（无需管理员权限）。
; 用 ISCC.exe 编译本脚本，产物输出到 installer\SerialTool-Setup-*.exe

#define MyAppName "串口调试助手"
#define MyAppVersion "0.2.0"
#define MyAppExeName "SerialTool.exe"
; PyInstaller onedir 产物目录名（dist\SerialTool\ -> 安装到 {app}\SerialTool\）
#define MyAppFolder "SerialTool"

[Setup]
AppId={{B5E6F0A2-3C4D-4E5F-9A8B-1C2D3E4F5A6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=SerialTool
DefaultDirName={autopf}\SerialTool
DefaultGroupName={#MyAppName}
; 允许用户选择任意安装位置（含非管理员可写目录）
PrivilegesRequired=lowest
AllowNoIcons=yes
; 不启用 Inno 6 自带的关闭进程机制（其"自动关闭"会卡死），
; 改为在 [Code] 中用 taskkill 强制结束正在运行的 SerialTool，避免文件被占用。
CloseApplications=no
OutputDir=installer
OutputBaseFilename=SerialTool-Setup-{#MyAppVersion}
SetupIconFile=assets\logo.ico
UninstallDisplayIcon={app}\{#MyAppFolder}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; 简体中文界面
LanguageDetectionMethod=uilanguage
ShowLanguageDialog=yes

[Languages]
Name: "chinesesimplified"; MessagesFile: "langs\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#MyAppFolder}\*"; DestDir: "{app}\{#MyAppFolder}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppFolder}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppFolder}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppFolder}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  // 安装文件前，强制结束正在运行的 SerialTool，避免文件被占用（DeleteFile 拒绝访问）。
  // /F 强制终止，/T 结束其子进程；进程不存在时 taskkill 返回非 0 但无害，继续安装。
  Exec('taskkill.exe', '/F /IM SerialTool.exe /T', '', SW_HIDE,
       ewWaitUntilTerminated, ResultCode);
end;
