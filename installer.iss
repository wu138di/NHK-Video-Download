#define AppName "NHK 下载器"
#define AppVersion "2.0"
[Setup]
#ifdef TEST_INSTALL
AppId={{97EBF790-AD72-497C-A16B-707242D38AE2}
#else
AppId={{C591B6D4-4D9F-4B86-AE63-F159C27DC3B8}
#endif
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=wu138di
DefaultDirName={localappdata}\Programs\NHKDownloader
#ifdef TEST_INSTALL
DefaultGroupName=NHK 下载器-验证
#else
DefaultGroupName=NHK 下载器
#endif
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=dist
OutputBaseFilename=NHK-Video-Download-V2.0-Engine
SetupIconFile=stage\_internal\assets\app-icon.ico
UninstallDisplayIcon={app}\NHK-Downloader-V2.0.exe
Compression=lzma2/normal
SolidCompression=yes
LZMANumBlockThreads=2
LZMABlockSize=16384
WizardStyle=modern
WizardBackImageFile=installer-background.png
WizardBackImageFileDynamicDark=installer-background.png
WizardBackImageOpacity=255
WizardImageFile=
WizardSmallImageFile=
WizardKeepAspectRatio=no
WizardSizePercent=130,105
DisableWelcomePage=no
ShowLanguageDialog=no
InfoBeforeFile=stage\使用说明.txt
CloseApplications=yes
RestartApplications=no
Uninstallable=yes
UninstallDisplayName={#AppName} V{#AppVersion}

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked

[Files]
Source: "installer-glass.png"; Flags: dontcopy
Source: "language.png"; Flags: dontcopy
Source: "guides\guide-zh.txt"; Flags: dontcopy
Source: "guides\guide-en.txt"; Flags: dontcopy
Source: "guides\guide-ja.txt"; Flags: dontcopy
Source: "stage\_internal\assets\app-icon.ico"; Flags: dontcopy
#ifndef PREVIEW
Source: "stage\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.pyc.tmp,__pycache__\*,tools\Logs\*,install-settings.json"
Source: "install-profiles\zh.json"; DestDir: "{app}"; DestName: "install-settings.json"; Flags: ignoreversion; Check: IsAppLanguage('zh')
Source: "install-profiles\en.json"; DestDir: "{app}"; DestName: "install-settings.json"; Flags: ignoreversion; Check: IsAppLanguage('en')
Source: "install-profiles\ja.json"; DestDir: "{app}"; DestName: "install-settings.json"; Flags: ignoreversion; Check: IsAppLanguage('ja')
#endif

[Icons]
Name: "{group}\{code:GetAppShortcut}"; Filename: "{app}\NHK-Downloader-V2.0.exe"; WorkingDir: "{app}"
Name: "{group}\{code:GetCliShortcut}"; Filename: "{app}\NHK-CLI.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\NHK-CLI-V2.0.exe"
Name: "{group}\{code:GetGuideShortcut}"; Filename: "{app}\{code:GetGuideFilename}"
Name: "{group}\{code:GetUninstallShortcut}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\NHK 下载器"; Filename: "{app}\NHK-Downloader-V2.0.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\NHK-Downloader-V2.0.exe"; Description: "{code:GetLaunchCaption}"; Flags: nowait postinstall skipifsilent

[Code]
#include "installer-ui.iss"
