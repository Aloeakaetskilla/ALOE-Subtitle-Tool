# -*- mode: python ; coding: utf-8 -*-
"""ALOE 字幕提取软件 - macOS PyInstaller 打包配置"""

import os
import sys

block_cipher = None
app_dir = os.path.dirname(os.path.abspath(SPEC))
parent_dir = os.path.dirname(app_dir)

a = Analysis(
    ['main.py'],
    pathex=[app_dir],
    binaries=[],
    datas=[
        (os.path.join(parent_dir, 'yt-dlp'), '.'),
        (os.path.join(parent_dir, 'ffmpeg'), '.'),
        (os.path.join(sys.prefix, 'Lib', 'site-packages', 'faster_whisper', 'assets'), 'faster_whisper/assets'),
    ],
    hiddenimports=[
        'translators',
        'docx',
        'lxml',
        'lxml.etree',
        'lxml._elementpath',
        'faster_whisper',
        'ctranslate2',
        'onnxruntime',
        'av',
        'av.codec',
        'av.format',
        'huggingface_hub',
        'tokenizers',
        'tqdm',
        'numpy',
        'openai',
        'httpx',
        'pydantic',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'pandas', 'PIL',
        'tkinter.test', 'unittest', 'test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ALOE字幕提取软件',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='universal2',
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ALOE字幕提取软件',
)
