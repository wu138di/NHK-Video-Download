# Building the Windows release

The source tree covers the CLI, installer and GUI integration layer. A full GUI build from source is not available: the original GUI entry point was supplied as a compiled V2.0 distribution.

## Required files

1. Windows x64 and Python 3.14.
2. Build packages from `requirements-build.txt`.
3. Inno Setup 6. Set `-InnoCompiler` if it is not installed in the usual folder.
4. A clean installation of this V2.0 release. Pass its directory as `-BaseDirectory`.

The base directory must contain `NHK-Downloader-V2.0.exe`, `_internal/nhk_v2/NHK-Video-Download-v2.0.pyc`, the Python/Qt runtime and the two executables under `tools/`. The script carries those runtime files forward, overlays the maintained Python modules and builds the CLI and installer.

Run from the repository root:

```powershell
python -m pip install -r requirements-build.txt
powershell -File scripts/build.ps1 -BaseDirectory "C:\path\to\NHKDownloader"
```

Use a fresh checkout for a new build. The script stops if `stage/` is already populated, rather than merging files from an older build.

`stage/`, `bootstrap/`, `build/` and `dist/` are local build directories and are ignored by Git. Browser profiles, cookies, download history and personal configuration are not build inputs.

The integration modules are read from `_internal/nhk_v2` by the existing GUI entry point. The original GUI bytecode needs the matching Python 3.14 runtime. Changing that base requires separate compatibility testing.

The installer shell bundles the Inno installation engine. It does not implement a second file installer. The application language is stored once during installation; the downloader then keeps that language.

Third-party notices are retained under `_internal/Additional Tools`. The root MIT license does not replace the licenses of those components or the supplied artwork.
