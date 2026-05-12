#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "正在修复权限，请输入开机密码..."
xattr -cr "$DIR"
codesign --deep --force --sign - "$DIR/ALOE字幕提取软件" 2>/dev/null
find "$DIR/_internal" -name "*.so" -exec codesign --force --sign - {} \; 2>/dev/null
find "$DIR/_internal" -name "*.dylib" -exec codesign --force --sign - {} \; 2>/dev/null
codesign --force --sign - "$DIR/yt-dlp" 2>/dev/null
codesign --force --sign - "$DIR/ffmpeg" 2>/dev/null
chmod +x "$DIR/ALOE字幕提取软件" "$DIR/yt-dlp" "$DIR/ffmpeg" 2>/dev/null
echo "修复完成！现在可以双击「ALOE字幕提取软件」运行了。"
read -n 1 -s -r -p "按任意键关闭..."
