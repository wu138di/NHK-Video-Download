param(
 [Parameter(Mandatory=$true)][string]$BaseDirectory,
 [string]$InnoCompiler = (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe')
)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$base=(Resolve-Path -LiteralPath $BaseDirectory).Path.TrimEnd('\')
$stage=Join-Path $root 'stage'
if($base -eq $root -or $base.StartsWith($stage+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Use a separate clean installation as the base.'}
foreach($file in @('NHK-Downloader-V2.0.exe','_internal\nhk_v2\NHK-Video-Download-v2.0.pyc','tools\N_m3u8DL-RE.exe','tools\packager-win-x64.exe')){
 if(-not (Test-Path -LiteralPath (Join-Path $base $file) -PathType Leaf)){throw "Missing base file: $file"}
}
if(-not (Test-Path -LiteralPath $InnoCompiler -PathType Leaf)){throw 'Pass the path to Inno Setup 6 ISCC.exe with -InnoCompiler.'}
if((Test-Path -LiteralPath $stage) -and (Get-ChildItem -LiteralPath $stage -Force)){throw 'stage/ is already populated. Use a fresh checkout for this build.'}
[IO.Directory]::CreateDirectory($stage)|Out-Null
Copy-Item -LiteralPath (Join-Path $base '_internal') -Destination $stage -Recurse
Copy-Item -LiteralPath (Join-Path $base 'NHK-Downloader-V2.0.exe') -Destination $stage
$tools=Join-Path $stage 'tools'
[IO.Directory]::CreateDirectory($tools)|Out-Null
foreach($file in @('N_m3u8DL-RE.exe','packager-win-x64.exe')){Copy-Item -LiteralPath (Join-Path (Join-Path $base 'tools') $file) -Destination $tools}
$modules=Join-Path $stage '_internal\nhk_v2'
foreach($name in @('subtitle_cleaner.py','live_guard.py','launch.py','general_diagnostics.py','program_metadata.py','live_progress.py','preparation_errors.py','programme_binding.py','subtitle_integration.py','runtime_profile.py','app_i18n.py','gui_layout.py','gui_localization.py','browser_isolation.py','ui-locales.json')){
 Copy-Item -LiteralPath (Join-Path (Join-Path $root 'src') $name) -Destination $modules -Force
}
$notices=Join-Path $stage '_internal\Additional Tools'
[IO.Directory]::CreateDirectory($notices)|Out-Null
Copy-Item (Join-Path $root 'third_party\Additional Tools\*.txt') -Destination $notices -Force
$guides=@{'guide-zh.txt'='使用说明.txt';'guide-en.txt'='UserGuide.en.txt';'guide-ja.txt'='使い方.ja.txt'}
foreach($name in $guides.Keys){Copy-Item -LiteralPath (Join-Path (Join-Path $root 'guides') $name) -Destination (Join-Path $stage $guides[$name])}
foreach($file in @('NHK-CLI.cmd','v2-task.example.json')){Copy-Item -LiteralPath (Join-Path $root $file) -Destination $stage}
Copy-Item -LiteralPath (Join-Path $root 'install-profiles\zh.json') -Destination (Join-Path $stage 'install-settings.json')
python -m PyInstaller --noconfirm --distpath $stage --workpath (Join-Path $root 'build\cli') (Join-Path $root 'cli.spec')
if($LASTEXITCODE -ne 0){throw 'CLI build failed.'}
$bootstrap=Join-Path $root 'bootstrap'
[IO.Directory]::CreateDirectory($bootstrap)|Out-Null
Copy-Item -LiteralPath (Join-Path $root 'installer-background.png') -Destination (Join-Path $bootstrap 'background.png')
foreach($file in @('language.svg','app-icon.ico')){Copy-Item -LiteralPath (Join-Path $root $file) -Destination $bootstrap}
Copy-Item (Join-Path $root 'guides\guide-*.txt') -Destination $bootstrap
Copy-Item -LiteralPath (Join-Path $root 'third_party\Additional Tools') -Destination (Join-Path $bootstrap 'notices') -Recurse
& $InnoCompiler ('/O'+$bootstrap) '/Fengine' (Join-Path $root 'installer.iss')
if($LASTEXITCODE -ne 0){throw 'Installation engine build failed.'}
python -m PyInstaller --noconfirm --distpath (Join-Path $root 'dist') --workpath (Join-Path $root 'build\installer') (Join-Path $root 'installer.spec')
if($LASTEXITCODE -ne 0){throw 'Installer build failed.'}
Write-Output ('Installer: '+(Join-Path $root 'dist\NHK-Video-Download-V2.0-Windows-x64-Setup.exe'))
