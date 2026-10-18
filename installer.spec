from pathlib import Path
W = Path(SPECPATH)
# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    [str(W/'src'/'apple_installer.py')],
    pathex=[],
    binaries=[],
    datas=[(str(W / 'bootstrap'), '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# Qt uses the unversioned ICU API provided by Windows. A Poppler installation
# on the build host PATH exports version-suffixed ICU functions; never bundle it.
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.lower() not in
              {'icuuc.dll', 'icuin.dll', 'icudt78.dll'}]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='NHK-Video-Download-V2.0-Windows-x64-Setup',
    version=str(W / 'installer-version.txt'),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(W / 'bootstrap' / 'app-icon.ico')],
)
