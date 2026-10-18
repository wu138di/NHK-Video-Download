# NHK Video Download V2.0

[中文](README.md) · [English](README.en.md) · [日本語](README.ja.md)

NHK 视频下载工具 V2.0，终于上 GitHub 啦～

[B 站视频教程](https://www.bilibili.com/video/BV1vV846VELH)（不熟悉的话，也可以先看看这篇教程）

## 下载

到 [Releases](https://github.com/wu138di/NHK-Video-Download/releases/latest) 下载 Windows x64 安装包。装好后，可以从开始菜单打开下载器或命令行。

这次发布的是 Windows 版本。Mac 包还在优化中（正在内测，有需要请联系我）。

## 使用

- 不熟悉这类工具的话，打开 GUI，切到网页模式使用就可以了。
- 已有媒体清单地址的话，可以用 GUI 的一般模式或 CLI。
- 默认保存到 C 盘用户的“下载”文件夹，保存位置可在设置里调整。
- 安装时选择中文、英文或日文，装好后界面和 CLI 跟随该语言，不再切换。
- 下载后的字幕会自动清理控制标记，无需额外确认。GUI 保留 `.subtitle-originals` 备份；CLI 下载成功后只留下成品，失败则保留工程和脱敏诊断日志。
- 检测到直播流时会提示等待回放，不会继续按点播任务下载。
- 网页模式使用本机 Edge / Chrome 的独立资料目录，不加载浏览器扩展。程序不附带 VPN，也不替你修改系统代理。

完整使用说明在这里哦~

[中文说明](guides/guide-zh.txt) · [English guide](guides/guide-en.txt) · [日本語の説明](guides/guide-ja.txt)

命令行直接打开就行：按提示填地址、请求头和密钥，KID 校验通过后再选画质、字幕和音轨。不用自己拼参数。

需要写脚本时，原来的参数用法也还在：

```text
NHK-CLI-V2.0.exe --help
NHK-CLI-V2.0.exe download --help
```

任务文件示例见 [v2-task.example.json](v2-task.example.json)。别把登录 Cookie、密钥或个人配置提交到仓库。

## 源码和构建

`src/` 里是 CLI、字幕处理、安装界面和 GUI 的集成代码。GUI 完整源码这次就不放了。大家可以基于已有的 V2.0 运行文件自行构建，也可以直接下载 [Releases](https://github.com/wu138di/NHK-Video-Download/releases/latest) 里构建好的安装包。

构建需要 Windows、Python 3.14、Inno Setup 6，以及一份同版本的干净安装目录，作为 GUI 和运行库的基础文件。

```powershell
python -m pip install -r requirements-build.txt
powershell -File scripts/build.ps1 -BaseDirectory "C:\path\to\NHKDownloader"
```

安装包输出到 `dist/`。构建说明见 [BUILD.md](BUILD.md)。

测试：

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
```

## 联系我

- X：[@wudihao138hack](https://x.com/wudihao138hack)
- QQ：3559380756
- bilibili：[wu138di](https://space.bilibili.com/514998292)

## 许可

本仓库维护的代码采用 [MIT](LICENSE) 许可。附加工具和图片保留各自的权利，详见 [NOTICE.md](NOTICE.md)。

还有，这不是 NHK 官方项目。仅供学习交流使用！请勿用于非法用途哦，出了事情，本人不负任何法律责任！

Made by wu138di
