; Inno Setup 脚本 —— 串口调试助手 安装程序
; 说明：用户可自选安装位置；默认按用户目录安装（无需管理员权限）。
; 用 ISCC.exe 编译本脚本，产物输出到 installer\SerialTool-Setup-*.exe

#define MyAppName "串口调试助手"
#define MyAppVersion "0.1.1"
#define MyAppExeName "SerialTool.exe"

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
OutputDir=installer
OutputBaseFilename=SerialTool-Setup-{#MyAppVersion}
SetupIconFile=assets\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
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
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
