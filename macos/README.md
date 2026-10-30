# macOS 命令行源码 · V1.0

[中文](#中文) · [English](#english) · [日本語](#日本語)

## 中文

把手头的 Mac 命令行源码先放上来，原文件没有改：

[NHK-Console-V1.0-macOS-Source.py](NHK-Console-V1.0-macOS-Source.py)

这是 V1.0，不是 Windows V2.0 的同版移植，也不是安装包。运行需要 Python 3，以及对应 Mac 架构的 N_m3u8DL-RE、Shaka Packager 和 FFmpeg。

```sh
cd macos
python3 NHK-Console-V1.0-macOS-Source.py
```

脚本把工具放在旁边的 `.nhk-tools`，下载结果放在 `output`。密钥由使用者自己提供，没有附带密钥或视频。

原版有个已知的依赖路径问题：检查时找 `.nhk-tools/shaka-packager`，自动下载分支却保存成 `解密库`。使用前需要把相应可执行文件放到正确的路径；这次只同步原源码，没有偷偷改掉原版逻辑。

这次在 arm64 Mac、Python 3.9.6 上做了语法、模块加载、文件名处理、文本解码和 KID 匹配检查，记录在 [verification.json](verification.json)。没有做实际媒体下载验收。原版的提示和清理方式也与 Windows V2.0 不同，暂时别把它当成同版本的完整替代。

上传问题日志前请检查并去掉密钥、Cookie 和个人信息。仓库根目录的 [MIT 许可](../LICENSE)适用于项目代码，附加工具各自遵循原许可证。

## English

Here is the existing Mac command-line source, unchanged:

[NHK-Console-V1.0-macOS-Source.py](NHK-Console-V1.0-macOS-Source.py)

This is V1.0, not a port of Windows V2.0 or a Mac installer. It needs Python 3, N_m3u8DL-RE, Shaka Packager and FFmpeg for your Mac's architecture. Run the two commands above from the repository root.

Tools go in `.nhk-tools` next to the script; downloads go in `output`. Users supply their own keys. No keys or videos are included.

The original has a known dependency-path mismatch: it checks for `.nhk-tools/shaka-packager`, but its download branch saves that executable as `解密库`. Put the executable at the expected path before use. This upload preserves the original rather than changing its behavior.

Syntax, module loading, filename handling, decoding and KID matching were checked on an arm64 Mac with Python 3.9.6; see [verification.json](verification.json). Actual media downloading was not tested. Its prompts and cleanup behavior also differ from Windows V2.0, so it is not a drop-in replacement.

Remove keys, cookies and personal information before sharing logs. Project code uses the root [MIT license](../LICENSE); bundled or downloaded tools retain their own licenses.

## 日本語

手元にある Mac 向け CLI のソースを、変更せずに公開しました。

[NHK-Console-V1.0-macOS-Source.py](NHK-Console-V1.0-macOS-Source.py)

これは V1.0 です。Windows V2.0 の移植版でも、Mac 用インストーラーでもありません。Python 3 と、Mac のアーキテクチャに合った N_m3u8DL-RE・Shaka Packager・FFmpeg が必要です。リポジトリのルートで上記の2行のコマンドを実行してください。

ツールの保存先はスクリプトの横の `.nhk-tools`、ダウンロード先は `output` です。鍵は利用者自身で入力します。鍵や動画は含めていません。

原版には依存ツールのパスの不一致があります。チェック時は `.nhk-tools/shaka-packager` を探しますが、自動ダウンロードでは `解密库` という名前で保存します。使用前に実行ファイルを正しいパスへ配置してください。今回は原版の動作を変更せず、ソースを同期しています。

arm64 Mac・Python 3.9.6 で構文、モジュールの読み込み、ファイル名処理、テキストのデコード、KID の照合を確認しました。[verification.json](verification.json) に記録しています。実際のメディアのダウンロードは未検証です。操作手順や作業ファイルの削除方法も Windows V2.0 と異なるため、そのまま置き換えるものではありません。

ログを共有する前に、鍵・Cookie・個人情報を取り除いてください。プロジェクトのコードにはルートの [MIT ライセンス](../LICENSE)、各ツールにはそれぞれのライセンスが適用されます。

Made by wu138di
