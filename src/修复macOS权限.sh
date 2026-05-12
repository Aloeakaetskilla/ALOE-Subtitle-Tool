#!/bin/bash
# ALOE 字幕提取软件 - macOS 权限修复脚本
# 双击运行此脚本即可解除安全限制

echo "=========================================="
echo "  ALOE 字幕提取软件 - macOS 权限修复"
echo "=========================================="
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR"

echo "正在修复权限，请输入开机密码（输入时不会显示）..."
echo ""

# 1. 移除隔离属性
echo "[1/3] 移除隔离标记..."
xattr -cr "$APP_DIR"

# 2. Ad-hoc 签名所有动态库和可执行文件（解决 macOS 代码签名强制要求）
echo "[2/3] 正在签名（可能需要 1-2 分钟）..."

# 签名主程序
codesign --deep --force --sign - "$APP_DIR/ALOE字幕提取软件" 2>/dev/null

# 递归签名所有 .so .dylib 文件
find "$APP_DIR/_internal" -name "*.so" -exec codesign --force --sign - {} \; 2>/dev/null
find "$APP_DIR/_internal" -name "*.dylib" -exec codesign --force --sign - {} \; 2>/dev/null

# 签名其他可执行文件
codesign --force --sign - "$APP_DIR/yt-dlp" 2>/dev/null
codesign --force --sign - "$APP_DIR/ffmpeg" 2>/dev/null

# 3. 确保执行权限
echo "[3/3] 修复执行权限..."
chmod +x "$APP_DIR/ALOE字幕提取软件" 2>/dev/null
chmod +x "$APP_DIR/yt-dlp" 2>/dev/null
chmod +x "$APP_DIR/ffmpeg" 2>/dev/null

echo ""
echo "=========================================="
echo "  修复完成！"
echo "  现在双击「ALOE字幕提取软件」即可运行"
echo "=========================================="
echo ""
read -p "按回车键关闭此窗口..."
