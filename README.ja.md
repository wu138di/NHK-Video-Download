# NHK Video Download V2.0

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

GUI と CLI をひとつのインストーラーにまとめた NHK 動画ダウンロードツールです。

## ダウンロード

[Releases](https://github.com/wu138di/NHK-Video-Download/releases/latest) から Windows x64 用インストーラーをダウンロードしてください。インストール後は、スタートメニューからアプリと CLI を起動できます。

今回の公開版は Windows 向けです。このリポジトリには Mac 用インストーラーは含まれていません。インストーラーにはコード署名を付けていません。

## 使い方

- ダウンロードの設定に詳しくない場合は、GUI のブラウザモードを使ってください。
- メディアプレイリストの URL が分かっている場合は、一般モードまたは CLI を使えます。
- 既定の保存先は C ドライブのユーザーの「ダウンロード」フォルダーです。設定から変更できます。
- インストール時に中国語・英語・日本語を選択します。アプリと CLI は、以後その言語で表示されます。
- ダウンロード後、字幕の制御タグは自動で整理されます。確認操作は不要です。元の字幕は保存先の `.subtitle-originals` にバックアップされます。
- ライブ配信を検出した場合は処理を止め、見逃し配信の公開後に再試行するよう表示します。
- ブラウザモードは PC にある Edge / Chrome の専用プロファイルを使い、拡張機能を読み込みません。VPN は同梱せず、システムのプロキシ設定も変更しません。

作者の中国語の説明文は原文のまま収録し、英語と日本語の訳も付けています。

[中文说明](guides/guide-zh.txt) · [English guide](guides/guide-en.txt) · [日本語の説明](guides/guide-ja.txt)

CLI のヘルプ：

```text
NHK-CLI-V2.0.exe --help
NHK-CLI-V2.0.exe download --help
```

タスクファイルの例は [v2-task.example.json](v2-task.example.json) を参照してください。Cookie、キー、個人設定はリポジトリに含めないでください。

## ソースとビルド

`src/` には CLI、字幕処理、インストーラーの画面、GUI の連携コードを収録しています。提供されたフォルダーには既存の GUI 配布ファイルがありましたが、GUI 全体の元のソースコードはありませんでした。コンパイル済みのファイルをソースとして掲載することはしていません。

ビルドには Windows、Python 3.14、Inno Setup 6 と、GUI の実行ファイル・ランタイムの元になる同じ V2.0 のクリーンなインストール先が必要です。

```powershell
python -m pip install -r requirements-build.txt
powershell -File scripts/build.ps1 -BaseDirectory "C:\path\to\NHKDownloader"
```

インストーラーは `dist/` に出力されます。詳しくは [BUILD.md](BUILD.md) を参照してください。

テスト：

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
```

## ライセンス

本リポジトリで管理するコードは [MIT](LICENSE) ライセンスです。追加ツールと画像の権利はそれぞれの権利者に帰属します。[NOTICE.md](NOTICE.md) を参照してください。

NHK の公式プロジェクトではありません。違法な用途には使用しないでください。

Made by wu138di
