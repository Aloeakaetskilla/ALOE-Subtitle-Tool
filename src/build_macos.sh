#!/bin/bash
set -e

echo "========================================"
echo "  ALOE 字幕提取软件 - macOS 构建脚本"
echo "========================================"
echo

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.10+"
    exit 1
fi

PYTHON=$(command -v python3)
echo "[1/5] 使用 Python: $PYTHON"
echo "      版本: $($PYTHON --version)"

# 安装依赖
echo "[2/5] 安装依赖..."
$PYTHON -m pip install -q --upgrade pip
$PYTHON -m pip install -q faster-whisper ctranslate2 openai requests python-docx pyinstaller

# 下载 yt-dlp (macOS 版)
if [ ! -f "$PARENT_DIR/yt-dlp" ]; then
    echo "[3/5] 下载 yt-dlp..."
    curl -L "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos" -o "$PARENT_DIR/yt-dlp"
    chmod +x "$PARENT_DIR/yt-dlp"
else
    echo "[3/5] yt-dlp 已存在"
fi

# 下载 ffmpeg (macOS universal)
if [ ! -f "$PARENT_DIR/ffmpeg" ]; then
    echo "[4/5] 下载 ffmpeg..."
    # 使用 evermeet.cx 提供的 universal ffmpeg
    FFMPEG_URL="https://evermeet.cx/ffmpeg/getrelease/zip"
    curl -L "$FFMPEG_URL" -o /tmp/ffmpeg.zip
    unzip -o /tmp/ffmpeg.zip -d "$PARENT_DIR/"
    chmod +x "$PARENT_DIR/ffmpeg"
    rm -f /tmp/ffmpeg.zip
else
    echo "[4/5] ffmpeg 已存在"
fi

# 清理旧构建
echo "[5/5] 开始打包..."
cd "$SCRIPT_DIR"
rm -rf dist build

# 使用 macOS spec 打包
$PYTHON -m PyInstaller ALOE_macOS.spec --noconfirm --clean

echo
echo "========================================"
echo "  构建完成！"
echo "  输出目录: $SCRIPT_DIR/dist/"
echo "========================================"
echo
echo "分发方式："
echo "  1. 将 dist/ALOE字幕提取软件 文件夹打包为 zip"
echo "  2. Mac 用户解压后双击 .app 即可运行"
echo "  3. 首次运行如提示安全警告，右键 -> 打开"
echo
