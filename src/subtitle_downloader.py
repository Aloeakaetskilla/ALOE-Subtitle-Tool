"""字幕下载模块 - 使用 yt-dlp 从 YouTube 提取字幕/音频"""
import subprocess
import re
import os
import sys
import tempfile
from dataclasses import dataclass, field


@dataclass
class SubtitleEntry:
    """单条字幕"""
    index: int
    start_time: str
    end_time: str
    text: str


@dataclass
class SubtitleTrack:
    """字幕轨道信息"""
    lang_code: str
    lang_name: str
    is_auto: bool


@dataclass
class VideoInfo:
    """视频信息"""
    title: str = ""
    url: str = ""
    en_subtitles: list = field(default_factory=list)
    zh_subtitles: list = field(default_factory=list)
    available_tracks: list = field(default_factory=list)


def get_app_dir():
    """获取应用程序所在目录（支持 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_ytdlp():
    """查找 yt-dlp 可执行文件"""
    app_dir = get_app_dir()
    candidates = [
        os.path.join(app_dir, "yt-dlp.exe"),
        os.path.join(app_dir, "bin", "yt-dlp.exe"),
        os.path.join(os.path.expanduser("~"), "yt-dlp.exe"),
        "yt-dlp",
        "yt-dlp.exe",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    try:
        result = subprocess.run(
            ["where", "yt-dlp"] if os.name == "nt" else ["which", "yt-dlp"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0].strip()
    except Exception:
        pass
    return None


def get_video_title(ytdlp_path, url):
    """获取视频标题"""
    try:
        result = subprocess.run(
            [ytdlp_path, "--get-title", "--no-download", url],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "Unknown"


def list_available_subtitles(ytdlp_path, url):
    """列出可用的字幕轨道"""
    tracks = []
    try:
        result = subprocess.run(
            [ytdlp_path, "--list-subs", "--no-download", url],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        output = result.stdout + result.stderr
        in_auto = False
        for line in output.split("\n"):
            if "Available automatic captions" in line:
                in_auto = True
                continue
            if "Available subtitles" in line:
                in_auto = False
                continue
            match = re.match(r'^(\S+)\s+(.+?)\s+(vtt|srt|ttml|srv\d|json3)', line.strip())
            if match:
                code = match.group(1)
                name = match.group(2).strip()
                tracks.append(SubtitleTrack(
                    lang_code=code, lang_name=name, is_auto=in_auto
                ))
    except Exception:
        pass
    return tracks


def download_subtitle(ytdlp_path, url, lang_code, output_dir, video_title="subtitle"):
    """下载指定语言的字幕，返回 SRT 文件路径"""
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', video_title)
    output_template = os.path.join(output_dir, f"{safe_name}.{lang_code}")

    try:
        result = subprocess.run(
            [ytdlp_path, "--write-auto-sub", "--sub-lang", lang_code,
             "--sub-format", "srt", "--skip-download", "-o", output_template, url],
            capture_output=True, text=True, timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )

        srt_file = output_template + ".srt"
        if os.path.isfile(srt_file):
            return srt_file

        for f in os.listdir(output_dir):
            if f.startswith(safe_name) and f.endswith(".srt"):
                return os.path.join(output_dir, f)
    except Exception:
        pass
    return None


# ─────────────────── 音频下载 + Whisper 语音识别 ───────────────────

def _has_audio_stream(file_path):
    """用 ffmpeg 检测文件是否包含音频流（尝试提取一小段音频）"""
    ffmpeg_path = _find_ffmpeg()
    if not ffmpeg_path:
        return True  # 无法检测，假设有的
    try:
        # 尝试提取前1秒音频到临时文件
        import tempfile
        tmp_wav = os.path.join(tempfile.gettempdir(), "_aloe_probe.wav")
        result = subprocess.run(
            [ffmpeg_path, "-i", file_path, "-t", "1", "-vn",
             "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-y", tmp_wav],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        has = os.path.isfile(tmp_wav) and os.path.getsize(tmp_wav) > 44  # WAV header is 44 bytes
        if os.path.isfile(tmp_wav):
            os.remove(tmp_wav)
        return has
    except Exception:
        return True


def _extract_audio_with_ffmpeg(video_path, output_path):
    """用 ffmpeg 从视频中提取音频"""
    ffmpeg_path = _find_ffmpeg()
    if not ffmpeg_path:
        return False
    try:
        subprocess.run(
            [ffmpeg_path, "-i", video_path, "-vn", "-acodec", "pcm_s16le",
             "-ar", "16000", "-ac", "1", "-y", output_path],
            capture_output=True, timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        return os.path.isfile(output_path)
    except Exception:
        return False


def download_audio(ytdlp_path, url, output_dir, video_title="audio"):
    """下载视频音频，返回音频文件路径"""
    import time
    os.makedirs(output_dir, exist_ok=True)
    temp_name = f"aloe_{int(time.time())}"
    output_path = os.path.join(output_dir, f"{temp_name}.%(ext)s")
    ffmpeg_path = _find_ffmpeg()
    ffmpeg_dir = os.path.dirname(ffmpeg_path) if ffmpeg_path else None
    ffmpeg_flag = ["--ffmpeg-location", ffmpeg_dir] if ffmpeg_dir else []

    try:
        # 第一次尝试：默认格式
        result = subprocess.run(
            [ytdlp_path, "--no-playlist", "-o", output_path] + ffmpeg_flag + [url],
            capture_output=True, text=True, timeout=300,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )

        downloaded = None
        for f in os.listdir(output_dir):
            if f.startswith(temp_name):
                ext = os.path.splitext(f)[1].lower()
                if ext in ('.m4a', '.mp4', '.webm', '.opus', '.mp3', '.wav', '.mkv'):
                    downloaded = os.path.join(output_dir, f)
                    break

        if not downloaded:
            return None

        # 如果是纯音频格式，直接返回
        ext = os.path.splitext(downloaded)[1].lower()
        if ext in ('.m4a', '.opus', '.mp3', '.wav'):
            return downloaded

        # 检测视频是否包含音频流
        if _has_audio_stream(downloaded):
            # 有音频，用 ffmpeg 提取
            audio_path = os.path.join(output_dir, f"{temp_name}.wav")
            if _extract_audio_with_ffmpeg(downloaded, audio_path):
                os.remove(downloaded)
                return audio_path
            return downloaded

        # 没有音频流，删除文件，用 h264 格式重试
        os.remove(downloaded)

        # 查找 h264 格式（通常包含音频）
        list_result = subprocess.run(
            [ytdlp_path, "--list-formats", "--no-download", url],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        h264_format = None
        for line in (list_result.stdout + list_result.stderr).split("\n"):
            if "h264" in line and "aac" in line:
                parts = line.strip().split()
                if parts:
                    h264_format = parts[0]
                    break

        if not h264_format:
            return None

        result = subprocess.run(
            [ytdlp_path, "-f", h264_format, "--no-playlist",
             "-o", output_path] + ffmpeg_flag + [url],
            capture_output=True, text=True, timeout=300,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )

        for f in os.listdir(output_dir):
            if f.startswith(temp_name):
                ext = os.path.splitext(f)[1].lower()
                if ext in ('.m4a', '.mp4', '.webm', '.opus', '.mp3', '.wav', '.mkv'):
                    downloaded = os.path.join(output_dir, f)
                    break

        if not downloaded:
            return None

        if ext in ('.m4a', '.opus', '.mp3', '.wav'):
            return downloaded

        audio_path = os.path.join(output_dir, f"{temp_name}.wav")
        if _extract_audio_with_ffmpeg(downloaded, audio_path):
            os.remove(downloaded)
            return audio_path

        return downloaded
    except Exception:
        pass
    return None


def _find_ffmpeg():
    """查找 ffmpeg 可执行文件"""
    app_dir = get_app_dir()
    candidates = [
        os.path.join(app_dir, "ffmpeg.exe"),
        os.path.join(app_dir, "bin", "ffmpeg.exe"),
        "ffmpeg",
        "ffmpeg.exe",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    try:
        result = subprocess.run(
            ["where", "ffmpeg"] if os.name == "nt" else ["which", "ffmpeg"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0].strip()
    except Exception:
        pass
    return None


def transcribe_audio(audio_path, callback=None, model_size="small", language=None):
    """
    用 faster-whisper 进行语音识别，生成完整字幕。

    Args:
        audio_path: 音频文件路径
        callback: 进度回调 callback(message)
        model_size: 模型大小 (tiny/base/small/medium/large-v3)
        language: 语言代码 (en/zh/ja/ko/fr/de/es/ru/pt/ar/vi)，None 为自动检测

    Returns:
        (entries, full_text): SubtitleEntry列表, 完整文本
    """
    from faster_whisper import WhisperModel

    if callback:
        callback(f"正在加载语音识别模型 ({model_size})...")

    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
    except Exception as e:
        if callback:
            callback(f"模型加载失败: {e}")
        return [], ""

    if callback:
        if language:
            callback(f"正在识别语音（语言: {language}），请稍候...")
        else:
            callback("正在识别语音（自动检测语言），请稍候...")

    try:
        result = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=False,
        )
    except Exception as e:
        if callback:
            callback(f"语音识别出错: {e}")
        return [], ""

    if not result or len(result) < 2:
        if callback:
            callback("语音识别返回结果为空")
        return [], ""

    segments, info = result[0], result[1]

    if callback and hasattr(info, 'language'):
        callback(f"检测到语言: {info.language}")

    entries = []
    full_text_parts = []
    idx = 1

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue

        # 格式化时间
        start = _seconds_to_srt_time(segment.start)
        end = _seconds_to_srt_time(segment.end)

        entries.append(SubtitleEntry(
            index=idx, start_time=start, end_time=end, text=text
        ))
        full_text_parts.append(text)
        idx += 1

        if callback and idx % 10 == 0:
            callback(f"已识别 {idx} 条...")

    if callback:
        callback(f"语音识别完成，共 {len(entries)} 条")

    full_text = " ".join(full_text_parts)
    return entries, full_text


def _seconds_to_srt_time(seconds):
    """秒数转 SRT 时间格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def parse_srt(srt_content):
    """解析 SRT 内容为字幕条目列表"""
    entries = []
    blocks = re.split(r'\n\s*\n', srt_content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue

        try:
            index = int(lines[0].strip())
        except ValueError:
            continue

        time_match = re.match(
            r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})',
            lines[1].strip()
        )
        if not time_match:
            continue

        start_time = time_match.group(1).replace('.', ',')
        end_time = time_match.group(2).replace('.', ',')

        text = '\n'.join(lines[2:]).strip()
        text = re.sub(r'<[^>]+>', '', text)

        if text:
            entries.append(SubtitleEntry(
                index=index, start_time=start_time,
                end_time=end_time, text=text
            ))

    return entries


def read_srt_file(srt_path):
    """读取 SRT 文件并解析"""
    encodings = ['utf-8', 'utf-8-sig', 'gbk', 'latin-1']
    for enc in encodings:
        try:
            with open(srt_path, 'r', encoding=enc) as f:
                content = f.read()
            return parse_srt(content)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return []


def _is_actually_chinese(entries):
    """验证字幕是否真的包含中文字符"""
    sample_size = min(20, len(entries))
    total_chars = 0
    chinese_chars = 0
    for entry in entries[:sample_size]:
        for ch in entry.text:
            if ch.isalpha():
                total_chars += 1
                if '\u4e00' <= ch <= '\u9fff':
                    chinese_chars += 1
    if total_chars == 0:
        return False
    return chinese_chars / total_chars > 0.15


def download_subtitles(ytdlp_path, url, output_dir, callback=None):
    """
    下载视频的英文字幕（备用方案）。
    推荐使用 download_audio + transcribe_audio 获得更好质量。
    """
    info = VideoInfo(url=url)

    if callback:
        callback("正在获取视频信息...")
    info.title = get_video_title(ytdlp_path, url)
    if callback:
        callback(f"视频标题: {info.title}")

    if callback:
        callback("正在检查可用字幕...")
    info.available_tracks = list_available_subtitles(ytdlp_path, url)

    en_langs = ['en', 'a.en']
    en_srt = None
    for lang in en_langs:
        if callback:
            callback(f"正在下载英文字幕 ({lang})...")
        en_srt = download_subtitle(ytdlp_path, url, lang, output_dir, info.title)
        if en_srt:
            break

    if en_srt:
        info.en_subtitles = read_srt_file(en_srt)
        if callback:
            callback(f"英文字幕下载成功，共 {len(info.en_subtitles)} 条")
    else:
        if callback:
            callback("英文字幕下载失败")

    return info
