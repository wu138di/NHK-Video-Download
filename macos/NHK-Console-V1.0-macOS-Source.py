#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import os
import sys
import re
import shutil
import stat
import tarfile
import platform
from datetime import datetime

# ================= 配置区域（请按需修改） =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(BASE_DIR, ".nhk-tools")
NM3U8_RE_PATH = TOOLS_DIR
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
# 随脚本安装的 FFmpeg；也可以改成自己的绝对路径。
FFMPEG_PATH = os.path.join(TOOLS_DIR, "ffmpeg")
SHAKA_PACKAGER_PATH = os.path.join(TOOLS_DIR, "shaka-packager")
# =========================================================

# ANSI 颜色码正则（用于清理子进程输出）
ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


# ============================ 工具函数 ============================ #

def print_color(text, color="white"):
    codes = {"red": "31", "green": "32", "yellow": "33", "blue": "34", "white": "37"}
    sys.stdout.write(f"\033[{codes.get(color, '37')}m{text}\033[0m\n")


def get_input(prompt, default=None):
    if default is not None:
        val = input(f"{prompt} [{default}]: ").strip()
        return val if val else default
    return input(f"{prompt}: ").strip()


def safe_filename(name):
    return re.sub(r'[\\/*?:"<>|]', '', name)


def decode_output(data):
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("gbk")
        except UnicodeDecodeError:
            return data.decode("latin-1")


def get_ffmpeg():
    return FFMPEG_PATH if os.path.exists(FFMPEG_PATH) else (shutil.which("ffmpeg") or "ffmpeg")


# ============================ 自检与安装 ============================ #

MAC_ARCH = "arm64" if platform.machine().lower() == "arm64" else "x64"
URLS = {
    "N_m3u8DL-RE": f"https://github.com/nilaoda/N_m3u8DL-RE/releases/download/v0.6.0-beta/N_m3u8DL-RE_v0.6.0-beta_osx-{MAC_ARCH}_20260629.tar.gz",
    "Shaka Packager": f"https://github.com/shaka-project/shaka-packager/releases/download/v3.9.3/packager-osx-{MAC_ARCH}",
}


def _download_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(100, downloaded * 100 // total_size)
        sys.stdout.write(f"\r  下载: {pct}% ({downloaded//1048576}MB/{total_size//1048576}MB)")
        sys.stdout.flush()
        if pct >= 100:
            sys.stdout.write("\n")


def _try_install(name, url, install_to):
    import urllib.request, tempfile
    try:
        os.makedirs(install_to, exist_ok=True)
        suffix = ".tar.gz" if url.endswith(".tar.gz") else ""
        archive_path = os.path.join(tempfile.gettempdir(), f"nhk_{name.replace(' ', '_')}{suffix}")
        print_color(f"  正在下载所需安装库...", "yellow")
        urllib.request.urlretrieve(url, archive_path, _download_progress)
        if suffix:
            print_color(f"  正在解压到 {install_to}...", "yellow")
            with tarfile.open(archive_path, "r:gz") as archive:
                archive.extractall(install_to)
            os.remove(archive_path)
        else:
            target = os.path.join(install_to, "解密库")
            shutil.move(archive_path, target)
            os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return True
    except Exception as e:
        print_color(f"  安装库自动安装失败：{e}", "red")
        return False


def preflight_check():
    checks = [
        ("N_m3u8DL-RE", os.path.join(NM3U8_RE_PATH, "N_m3u8DL-RE")),
        ("Shaka Packager", SHAKA_PACKAGER_PATH),
        ("FFmpeg", shutil.which("ffmpeg") or FFMPEG_PATH),
    ]
    while True:
        print_color("正在自检依赖程序...", "blue")
        missing = []
        for name, path in checks:
            if os.path.exists(path):
                print_color(f"  ✓ {name}", "green")
            else:
                print_color(f"  ✗ {name}", "red")
                missing.append(name)
        if not missing:
            print_color("自检通过！\n", "green")
            return

        if "N_m3u8DL-RE" in missing:
            ok = _try_install("N_m3u8DL-RE", URLS["N_m3u8DL-RE"], NM3U8_RE_PATH)
            if not ok:
                print_color(f"  请手动下载：{URLS['N_m3u8DL-RE']}", "yellow")
        if "Shaka Packager" in missing:
            ok = _try_install("Shaka Packager", URLS["Shaka Packager"], NM3U8_RE_PATH)
            if not ok:
                print_color(f"  请手动下载：{URLS['Shaka Packager']}", "yellow")
        if "FFmpeg" in missing:
            print_color("  请先安装 FFmpeg：brew install ffmpeg", "yellow")

        still = [n for n, p in checks if not os.path.exists(p)]
        if still:
            print_color("安装完成后按回车重新检查...", "yellow")
            input()


# ============================ 参数构建 ============================ #

def _common_args(m3u8_url, keys):
    exe = os.path.join(NM3U8_RE_PATH, "N_m3u8DL-RE")
    if not os.path.exists(exe):
        print_color(f"错误：找不到可用 m3u8 下载解析工具，请自行下载：{URLS['N_m3u8DL-RE']}", "red")
        sys.exit(1)

    args = [exe, m3u8_url, "--save-dir", OUTPUT_DIR, "--tmp-dir", OUTPUT_DIR]

    headers = [
        "CMCD-Object: ot=m",
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        'CMCD-Session: sf=h,sid="a2e998e9-9a19-4c4c-90ae-45db5440dd76"',
        "CMCD-Request: mtp=2300,su",
        "Accept: */*",
        "Origin: https://www.web.nhk",
        "Referer: https://www.web.nhk/",
    ]
    for h in headers:
        args += ["-H", h]

    for key in keys:
        args += ["--key", key]

    return args


def build_download_args(m3u8_url, keys, filename, auto_select):
    args = _common_args(m3u8_url, keys)
    args += ["--save-name", filename]
    if auto_select:
        args += ["--auto-select"]
    # simul 服务器（直播回看）没有 #EXT-X-ENDLIST，N_m3u8DL-RE 会判定为直播
    # 加 --live-perform-as-vod 强制按点播下载，不走滑动窗口录制
    if "simul" in m3u8_url:
        args += ["--live-perform-as-vod"]
    args += ["--decryption-engine", "SHAKA_PACKAGER",
             "--decryption-binary-path", SHAKA_PACKAGER_PATH,
             "-M", "format=mkv",
             "--download-retry-count", "10"]
    if auto_select:
        args += ["--force-ansi-console"]
    return args


# ============================ KID serach by wu138di ============================ #
#                  视频/音频的 KID，与用户提供的密钥 KID 做匹配，防止密钥搞混。           #
# =============================================================================#

def probe_kids(m3u8_url, keys):

    print_color("正在探查视频 KID...", "yellow")
    probe_name = f"_probe_{datetime.now().strftime('%H%M%S')}"
    args = _common_args(m3u8_url, keys)
    args += [
        "--save-name", probe_name,
        "--auto-select",
        "--custom-range", "0-0",
        "--decryption-engine", "SHAKA_PACKAGER",
        "--decryption-binary-path", SHAKA_PACKAGER_PATH,
        "--skip-merge",
        "--no-ansi-color",
    ]

    proc = subprocess.Popen(args, cwd=OUTPUT_DIR,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    import threading
    kids = set()
    stream_types = {}
    current_type = "unknown"
    _done = threading.Event()

    def _read():
        nonlocal current_type
        for line in iter(proc.stdout.readline, b""):
            text = ANSI_RE.sub("", decode_output(line))
            if "开始下载...视频文件" in text:
                current_type = "video"
            elif "开始下载...音频文件" in text:
                current_type = "audio"
            m = re.search(r"KID:\s*([0-9a-fA-F]+)", text)
            if m:
                kid = m.group(1).lower()
                kids.add(kid)
                stream_types[kid] = current_type
                print_color(f"  发现 KID ({current_type}): {kid}", "blue")
        _done.set()

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    # 直播滑动窗口 + --custom-range 可能卡死，30秒超时
    t.join(timeout=30)
    if t.is_alive():
        proc.kill()
        proc.wait()
        t.join()
        print_color("  探查超时（直播流可能不支持），跳过 KID 验证。", "yellow")
        return set(), {}
    proc.wait()

    # 清理探查临时文件和目录
    for f in os.listdir(OUTPUT_DIR):
        if f.startswith(probe_name) or f.startswith("_probe_"):
            fpath = os.path.join(OUTPUT_DIR, f)
            try:
                if os.path.isdir(fpath):
                    shutil.rmtree(fpath)
                else:
                    os.remove(fpath)
            except Exception:
                pass

    return kids, stream_types


def verify_keys(kids, keys):

    user_kids = set()
    for k in keys:
        if ":" in k:
            user_kids.add(k.split(":")[0].lower())
        elif len(k) == 32:  
            pass
    matched = kids & user_kids
    unmatched = kids - user_kids
    return matched, unmatched



def verify_mkv(mkv_path):

    ffmpeg = get_ffmpeg()
    try:
        ret = subprocess.run(
            [ffmpeg, "-i", mkv_path, "-t", "30", "-f", "null", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            timeout=120,
        )
        if ret.returncode == 0:
            return True, ""
        else:
            # quit error
            errors = [l for l in ret.stdout.split("\n")
                      if "error" in l.lower() or "corrupt" in l.lower()
                      or "concealing" in l.lower()]
            return False, "\n".join(errors[:5]) if errors else ret.stdout[-300:]
    except subprocess.TimeoutExpired:
        return False, "超时(error)"
    except Exception as e:
        return False, str(e)


# ============================ 下载执行 ============================ #

def find_latest_mkv(directory, name_hint):
    candidates = []
    try:
        for f in os.listdir(directory):
            if f.endswith(".mkv"):
                full = os.path.join(directory, f)
                candidates.append((full, os.path.getmtime(full)))
    except FileNotFoundError:
        pass
    if not candidates:
        return None
    filtered = [c for c in candidates if name_hint in os.path.basename(c[0])]
    pool = filtered if filtered else candidates
    return max(pool, key=lambda x: x[1])[0]


def auto_mode_run(args):
    print_color("Auto Bast，开始下载...", "yellow")
    proc = subprocess.Popen(args, cwd=OUTPUT_DIR)
    proc.wait()
    return proc.returncode


def manual_mode_run(args, filename):
    print_color("请直接在当前终端中完成流选择。", "yellow")
    ret = subprocess.run(args, cwd=OUTPUT_DIR).returncode

    mkv_file = find_latest_mkv(OUTPUT_DIR, filename)
    if mkv_file:
        print_color(f"检测到视频文件：{mkv_file}", "green")
        return ret, mkv_file
    print_color("未找到视频文件，下载可能失败。", "red")
    return 1, None


def convert_to_mp4(mkv_path, filename):
    ffmpeg = get_ffmpeg()
    dir_part = os.path.dirname(mkv_path)
    mp4_path = os.path.join(dir_part, f"{filename}.mp4")
    counter = 1
    while os.path.exists(mp4_path):
        mp4_path = os.path.join(dir_part, f"{filename}_{counter}.mp4")
        counter += 1

    print_color(f"开始转换....请稍等", "yellow")
    ret = subprocess.run(
        [ffmpeg, "-i", mkv_path, "-c", "copy", mp4_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )

    if ret.returncode == 0:
        print_color(f"转换成功！{mp4_path}", "green")
        if input("是否删除原始视频？(y/n): ").strip().lower() == "y":
            try:
                os.remove(mkv_path)
                print("已删除。")
            except Exception as e:
                print(f"删除失败：{e}")
    else:
        err = ret.stdout[-500:] if ret.stdout else "未知错误"
        print_color(f"转换失败：\n{err}", "red")


def cleanup_intermediate(filename):
    cleaned = []
    for item in os.listdir(OUTPUT_DIR):
        fpath = os.path.join(OUTPUT_DIR, item)

        if item == f"{filename}.mkv":
            continue

        should_delete = False

        if item.startswith(f"{filename}."):
            should_delete = True
        # probe 临时文件/目录
        elif item.startswith("_probe_"):
            should_delete = True
        # 手动模式的临时文件
        elif item.startswith(f"_nhk_manual_{filename}"):
            should_delete = True

        if should_delete:
            try:
                if os.path.isdir(fpath):
                    shutil.rmtree(fpath)
                else:
                    os.remove(fpath)
                cleaned.append(item)
            except Exception:
                pass

    if cleaned:
        print_color(f"已清理 {len(cleaned)} 个中间文件：{', '.join(cleaned)}", "blue")


# ============================ 主流程 ============================ #

def main():
    print_color("=" * 58, "blue")
    print_color("           NHK Video Download v1.0 by wu138di", "grey")
    print_color("=" * 58, "blue")

    preflight_check()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. 输入 m3u8 地址
    m3u8_url = get_input("请输入 m3u8 清单/MPD流地址")
    if not m3u8_url:
        print_color("地址不能为空！", "red")
        return

    # 2. 输入密钥
    keys_text = get_input("请输入密钥（KID：key）（多个用逗号分隔，没有回车继续）", "")
    keys = [k.strip() for k in re.split(r"[,\n]", keys_text) if k.strip()] if keys_text else []

    if keys:
        kids, stream_types = probe_kids(m3u8_url, keys)
        if kids:
            matched, unmatched = verify_keys(kids, keys)
            if matched:
                for kid in sorted(matched):
                    stype = stream_types.get(kid, "?")
                    print_color(f" KID 匹配 ...正在解析中", "green")
            if unmatched:
                print_color(f"\n  KID不匹配....解析失败！", "red")
                for kid in sorted(unmatched):
                    stype = stream_types.get(kid, "?")
                    print_color(f"    {kid} ({stype})", "red")
                print_color("\n  视频的解密即将失败，视频将无法播放！", "red")
                print_color("  请确认密钥与此视频匹配（每个视频 KID 唯一）。\n", "yellow")
                choice = input("  是否仍要继续下载？(y/n): ").strip().lower()
                if choice != "y":
                    print_color("已取消。请找到正确的KID后重试。", "yellow")
                    return
                print_color("继续下载（风险自负）...\n", "yellow")
            else:
                print_color("  所有 KID 均已匹配，可以安全下载。\n", "green")
        else:
            print_color("  未能探查到 KID，继续尝试...\n", "yellow")
    else:
        print_color("未提供密钥，跳过 KID 验证。\n", "yellow")

    default_fname = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    custom_fname = get_input("自定义文件名？(留空自动生成文件标题)", default_fname)
    filename = safe_filename(custom_fname) if custom_fname else default_fname

    # 5. 流模式
    auto_select = input("自动选择最佳视频/音频？(y/n，默认 y): ").strip().lower() != "n"

    # 总结
    print(f"\n{'='*40}")
    print(f"文件名:   {filename}")
    print(f"密钥数量: {len(keys)}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"流选择:   {'自动' if auto_select else '手动（新窗口交互）'}")
    print(f"{'='*40}\n")

    # 构建参数列表
    args = build_download_args(m3u8_url, keys, filename, auto_select)

    # 执行下载
    ret = -1
    mkv_file = None
    if auto_select:
        ret = auto_mode_run(args)
    else:
        ret, mkv_file = manual_mode_run(args, filename)

    # 后处理
    if ret == 0 or mkv_file:
        if not mkv_file:
            mkv_file = find_latest_mkv(OUTPUT_DIR, filename)
        if mkv_file:
            print_color(f"\n下载完成：{mkv_file}", "green")

            print_color("正在验证生成文件完整性...", "yellow")
            ok, err = verify_mkv(mkv_file)
            if ok:
                print_color("文件验证通过！", "green")
                # N_m3u8DL-RE 混流后会自动清理中间文件（含 SRT），需从 MKV 重新提取
                srt_path = os.path.join(OUTPUT_DIR, f"{filename}.ja.srt")
                if not os.path.exists(srt_path):
                    ffmpeg = get_ffmpeg()
                    try:
                        subprocess.run(
                            [ffmpeg, "-i", mkv_file, "-map", "0:s:0", "-c:s", "srt", srt_path],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                        if os.path.exists(srt_path):
                            print_color(f"字幕已提取：{srt_path}", "green")
                    except Exception:
                        pass
                keep = input("是否保留工程文件？(含SRT字幕等，请三思而后行) (y/n): ").strip().lower()
                if keep == "y":
                    print_color("工程文件已保留。", "yellow")
                else:
                    cleanup_intermediate(filename)
            else:
                print_color("✗ 文件验证失败！视频可能已损坏。", "red")
                print_color("  常见原因：密钥 KID 不匹配 → 解密产出垃圾数据。", "red")
                if err:
                    print_color(f"  错误详情：\n{err}", "red")
                print_color("  中间文件已保留以便排查。", "yellow")

            # 转换 MP4
            print_color("\n是否转换为可正常编辑格式？", "yellow")
            if input("(y/n): ").strip().lower() == "y":
                convert_to_mp4(mkv_file, filename)
        else:
            print_color("未找到源视频文件，请检查输出目录。", "red")
    else:
        print_color(f"下载失败，返回码：{ret}", "red")
        print_color("中间文件已保留以便排查。", "yellow")

    input("\n按回车键退出...")


if __name__ == "__main__":
    main()
