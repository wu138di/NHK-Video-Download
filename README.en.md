# NHK Video Download V2.0

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

NHK Video Download V2.0 — finally on GitHub!

[bilibili video tutorial](https://www.bilibili.com/video/BV1vV846VELH) — if you are new to the tool, you can start here.

## Download

Get the Windows x64 installer from [Releases](https://github.com/wu138di/NHK-Video-Download/releases/latest). The Start menu has shortcuts for the app and CLI.

This release is for Windows. The Mac version is still being refined and is currently in private testing. Get in touch if you would like to try it.

## Using the app

- If you are not familiar with download options, use browser mode in the GUI.
- If you already have a media playlist URL, use general mode or the CLI.
- Downloads go to your C-drive user Downloads folder by default. You can choose another folder in Settings.
- Choose Chinese, English or Japanese during installation. The app and CLI keep that language afterward.
- Subtitle control tags are cleaned automatically after download. The original files are backed up in `.subtitle-originals` inside the output folder.
- Live streams are stopped with a message asking you to wait for the replay.
- Browser mode uses a separate profile in your local Edge / Chrome and does not load browser extensions. There is no bundled VPN, and the app does not change your system proxy.

The full instructions are here:

[中文说明](guides/guide-zh.txt) · [English guide](guides/guide-en.txt) · [日本語の説明](guides/guide-ja.txt)

CLI help:

```text
NHK-CLI-V2.0.exe --help
NHK-CLI-V2.0.exe download --help
```

See [v2-task.example.json](v2-task.example.json) for a task file example. Keep cookies, keys and personal configuration out of the repository.

## Source and builds

`src/` contains the CLI, subtitle processing, installer UI and GUI integration code. I'm not publishing the full GUI source here. You can build using the existing V2.0 runtime files, or download the ready-made installer from [Releases](https://github.com/wu138di/NHK-Video-Download/releases/latest).

Building needs Windows, Python 3.14, Inno Setup 6 and a clean installation of the same V2.0 release for the GUI runtime files.

```powershell
python -m pip install -r requirements-build.txt
powershell -File scripts/build.ps1 -BaseDirectory "C:\path\to\NHKDownloader"
```

The installer is written to `dist/`. See [BUILD.md](BUILD.md) for the build layout.

Tests:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
```

## Contact

- X: [@wudihao138hack](https://x.com/wudihao138hack)
- QQ: 3559380756
- bilibili: [wu138di](https://space.bilibili.com/514998292)

## License

Project-maintained code is licensed under [MIT](LICENSE). Additional tools and artwork retain their own rights; see [NOTICE.md](NOTICE.md).

Also, this is not an official NHK project. It is for learning and discussion only. Please do not use it for anything illegal; I accept no legal liability for misuse.

Made by wu138di
