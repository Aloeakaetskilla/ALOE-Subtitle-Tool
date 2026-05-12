@echo off
chcp 65001 >nul 2>&1
title ALOE 快捷字幕提取器

:: 查找 Python
set PYTHON=
for %%P in (python python3 py) do (
    where %%P >nul 2>&1 && set PYTHON=%%P && goto :found
)

:: 尝试常见安装路径
for %%V in (312 311 310 39) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set PYTHON=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe
        goto :found
    )
)

echo [错误] 未找到 Python，请先安装 Python 3.9+
echo 下载地址: https://www.python.org/downloads/
pause
exit /b 1

:found
echo 使用 Python: %PYTHON%
%PYTHON% --version

:: 检查并安装依赖
echo 正在检查依赖...
%PYTHON% -m pip install -q -r "%~dp0requirements.txt" 2>nul

:: 启动程序
echo 正在启动 ALOE 快捷字幕提取器...
cd /d "%~dp0"
%PYTHON% main.py

pause
