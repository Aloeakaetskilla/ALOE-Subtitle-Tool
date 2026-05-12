@echo off
chcp 65001 >nul 2>&1
title ALOE 构建脚本

echo ========================================
echo   ALOE 快捷字幕提取器 - 构建脚本
echo ========================================
echo.

:: 设置 Python 路径
set PYTHON=
for %%P in (python python3 py) do (
    where %%P >nul 2>&1 && set PYTHON=%%P && goto :found_python
)
for %%V in (312 311 310 39) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set PYTHON=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe
        goto :found_python
    )
)
echo [错误] 未找到 Python
pause
exit /b 1

:found_python
echo [1/4] 使用 Python: %PYTHON%

:: 安装依赖
echo [2/4] 安装依赖...
%PYTHON% -m pip install -q deep-translator python-docx pyinstaller

:: 检查 yt-dlp
if not exist "%USERPROFILE%\yt-dlp.exe" (
    echo [提示] 正在下载 yt-dlp...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe' -OutFile '%USERPROFILE%\yt-dlp.exe'" 2>nul
)

:: 清理旧构建
echo [3/4] 清理旧构建...
if exist "%~dp0dist" rmdir /s /q "%~dp0dist"
if exist "%~dp0build" rmdir /s /q "%~dp0build"

:: 执行 PyInstaller
echo [4/4] 正在打包...
cd /d "%~dp0"
%PYTHON% -m PyInstaller ALOE.spec --noconfirm --clean 2>&1

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

:: 复制 yt-dlp 到输出目录
echo 正在复制 yt-dlp...
copy /y "%USERPROFILE%\yt-dlp.exe" "%~dp0dist\ALOE_Subtitle\" >nul 2>&1

echo.
echo ========================================
echo   构建完成！
echo   输出目录: %~dp0dist\ALOE_Subtitle\
echo ========================================
echo.
echo 可以将 dist\ALOE_Subtitle 文件夹打包分发给其他人
echo 或运行 create_installer.iss 用 Inno Setup 创建安装包
echo.
pause
