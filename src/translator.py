"""翻译模块 - 使用有道 API 作为主翻译引擎"""
import re
import hashlib
import uuid
import urllib.request
import urllib.parse
import json


# ─────────────────── 配置 ───────────────────

_YOUDAO_APP_KEY = '2d09ad400d8a885a'
_YOUDAO_APP_SECRET = '48sgTJ5RAE81xx4X84cKnRUmq6ckvleM'

_SILICONFLOW_API_KEY = "sk-ibljechcnueprjpeotuzuurutkgbwfvbqquvdwpowireqgub"
_SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
_HUNYUAN_MODEL = "tencent/Hunyuan-MT-7B"

_TRANSLATE_SYSTEM_PROMPT = (
    "你是一个专业的英译中翻译器。请将用户输入的英文翻译成流畅自然的中文。只输出翻译结果，不要解释。"
)


# ─────────────────── 英文文本预处理 ───────────────────

_CONTRACTIONS = {
    r'\bdont\b': "don't", r'\bcant\b': "can't", r'\bwont\b': "won't",
    r'\byoure\b': "you're", r'\btheyre\b': "they're", r'\bweve\b': "we've",
    r'\bive\b': "I've", r'\byouve\b': "you've",
    r'\bisnt\b': "isn't", r'\barent\b': "aren't", r'\bwasnt\b': "wasn't",
    r'\bwerent\b': "weren't", r'\bhasnt\b': "hasn't", r'\bhavent\b': "haven't",
    r'\bhadnt\b': "hadn't", r'\bdoesnt\b': "doesn't", r'\bdidnt\b': "didn't",
    r'\bcouldnt\b': "couldn't", r'\bwouldnt\b': "wouldn't", r'\bshouldnt\b': "shouldn't",
    r'\bthatll\b': "that'll", r'\bitll\b': "it'll", r'\btheyll\b': "they'll",
    r'\byoull\b': "you'll", r'\bim\b': "I'm", r'\bheres\b': "here's",
    r'\btheres\b': "there's", r'\bwhats\b': "what's",
    r'\bgonna\b': 'going to', r'\bwanna\b': 'want to', r'\bgotta\b': 'got to',
    r'\bkinda\b': 'kind of', r'\bsorta\b': 'sort of',
}


def _clean_english(text):
    """修复英文文法（仅修复缩写和大小写，不做语义替换）"""
    for pattern, replacement in _CONTRACTIONS.items():
        text = re.sub(pattern, replacement, text)
    text = re.sub(r'\s+', ' ', text).strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    text = re.sub(r'\bi\b(?=[\s\'])', 'I', text)
    return text.strip()


# ─────────────────── 中文文本清理 ───────────────────

def _clean_chinese_punctuation(text):
    """英文标点转中文标点"""
    replacements = {'.': '。', ',': '，', '!': '！', '?': '？',
                    ':': '：', ';': '；', '(': '（', ')': '）'}
    result = []
    for i, ch in enumerate(text):
        if ch in replacements and i > 0:
            prev = text[i - 1]
            if '\u4e00' <= prev <= '\u9fff' or prev in '）】》':
                result.append(replacements[ch])
                continue
        result.append(ch)
    return ''.join(result)


def _clean_chinese_spacing(text):
    """移除中文字符间多余空格"""
    text = re.sub(r'([\u4e00-\u9fff\u3000-\u303f]) +([\u4e00-\u9fff\u3000-\u303f])', r'\1\2', text)
    text = re.sub(r' +([，。！？、；：\u201c\u201d\u2018\u2019）】》])', r'\1', text)
    text = re.sub(r'([，。！？、；：\u201c\u201d\u2018\u2019）】》]) +', r'\1', text)
    return text


def _clean_translation(text):
    """清理翻译结果"""
    text = _clean_chinese_punctuation(text)
    text = _clean_chinese_spacing(text)
    return text.strip()


# ─────────────────── 翻译引擎 ───────────────────

def _translate_youdao_api(text):
    """使用有道智云 API 翻译（v1 签名）"""
    import requests as req_lib
    salt = str(uuid.uuid4())
    sign = hashlib.md5((_YOUDAO_APP_KEY + text + salt + _YOUDAO_APP_SECRET).encode('utf-8')).hexdigest()
    resp = req_lib.post('https://openapi.youdao.com/api', data={
        'q': text, 'from': 'en', 'to': 'zh-CHS',
        'appKey': _YOUDAO_APP_KEY, 'salt': salt,
        'sign': sign, 'signType': 'v1',
    }, timeout=30)
    result = resp.json()
    if result.get('errorCode') == '0':
        return _clean_translation(result['translation'][0])
    raise Exception(f"Youdao API error: {result.get('errorCode')}")


def _translate_hunyuan(text):
    """使用腾讯混元 MT-7B 翻译模型"""
    from openai import OpenAI
    client = OpenAI(api_key=_SILICONFLOW_API_KEY, base_url=_SILICONFLOW_BASE_URL)
    response = client.chat.completions.create(
        model=_HUNYUAN_MODEL,
        messages=[
            {'role': 'system', 'content': _TRANSLATE_SYSTEM_PROMPT},
            {'role': 'user', 'content': text},
        ],
        temperature=0.1, max_tokens=4000,
    )
    result = response.choices[0].message.content
    return _clean_translation(result) if result else ""


def _translate_google_free(text):
    """Google Translate 免费 API"""
    data = urllib.parse.urlencode({
        "client": "gtx", "sl": "en", "tl": "zh-CN", "dt": "t", "q": text,
    }).encode("utf-8")
    req = urllib.request.Request("https://translate.googleapis.com/translate_a/single", data=data, headers={
        "User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        result_data = json.loads(resp.read().decode("utf-8"))
        return _clean_translation("".join(p[0] for p in result_data[0] if p[0]))


def _translate_chunk(text):
    """翻译一段文字，优先混元MT，失败则有道API，最后 Google"""
    if not text or not text.strip():
        return ""

    # 方法1: 腾讯混元 MT-7B
    try:
        result = _translate_hunyuan(text)
        if result and len(result) > 1:
            return result
    except Exception:
        pass

    # 方法2: 有道 API
    try:
        result = _translate_youdao_api(text)
        if result and len(result) > 1:
            return result
    except Exception:
        pass

    # 方法3: Google POST
    try:
        result = _translate_google_free(text)
        if result and len(result) > 1:
            return result
    except Exception:
        pass

    return text


# ─────────────────── 分块逻辑 ───────────────────

def _split_into_chunks(text, max_chars=3000):
    """按段落边界分块"""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        segment = remaining[:max_chars]
        split_pos = -1
        for sep in ['. ', '! ', '? ', '.\n']:
            p = segment.rfind(sep)
            if p > max_chars * 0.3:
                split_pos = p + len(sep)
                break
        if split_pos <= 0:
            split_pos = segment.rfind(' ')
            if split_pos <= max_chars * 0.3:
                split_pos = max_chars
        chunks.append(remaining[:split_pos].strip())
        remaining = remaining[split_pos:].strip()
    return chunks


# ─────────────────── 主翻译类 ───────────────────

class Translator:
    def __init__(self, source_lang="en"):
        self.failed = False
        self.source_lang = source_lang

    def translate_text(self, english_text, callback=None):
        """翻译完整文本为中文"""
        self.failed = False
        if not english_text or not english_text.strip():
            return ""

        if self.source_lang == "en":
            clean_en = _clean_english(english_text)
        else:
            clean_en = english_text.strip()
        if callback:
            callback(0, 1, f"正在翻译 {len(clean_en)} 字符的英文文本...")

        chunks = _split_into_chunks(clean_en, max_chars=3000)
        if callback:
            callback(0, 1, f"分为 {len(chunks)} 段，开始翻译...")

        translated_parts = []
        for idx, chunk in enumerate(chunks):
            if callback:
                callback(0, 1, f"翻译中... ({idx + 1}/{len(chunks)})")
            try:
                zh = _translate_chunk(chunk)
                translated_parts.append(zh)
            except Exception:
                translated_parts.append(chunk)
                self.failed = True

        full_zh = "\n\n".join(translated_parts)
        if callback:
            callback(1, 1, "翻译完成")
        return full_zh

    def translate_batch(self, entries, callback=None, **kwargs):
        """翻译字幕条目列表"""
        self.failed = False
        if not entries:
            return [], 0
        all_text = " ".join(e.text.strip() for e in entries if e.text.strip())
        if not all_text:
            return entries, 0
        zh_text = self.translate_text(all_text, callback=callback)
        if not zh_text:
            return entries, 0
        return self._map_to_entries(entries, zh_text), 1.0

    def _map_to_entries(self, entries, zh_text):
        """将完整中文文本按比例映射回原始条目"""
        result = []
        total_en_len = sum(len(e.text.strip()) for e in entries)
        pos = 0
        n = len(entries)
        for j, entry in enumerate(entries):
            en_len = len(entry.text.strip())
            if j == n - 1:
                chunk = zh_text[pos:].strip()
            else:
                ratio = en_len / total_en_len if total_en_len > 0 else 1.0 / n
                remaining = n - j - 1
                max_end = len(zh_text) - remaining
                zh_len = max(1, int(ratio * len(zh_text)))
                end_pos = min(pos + zh_len, max_end)
                if end_pos < len(zh_text):
                    for punct in ['。', '，', '！', '？', '、', '；']:
                        p = zh_text.rfind(punct, pos + 1, end_pos + 5)
                        if p > pos and p < max_end:
                            end_pos = p + 1
                            break
                chunk = zh_text[pos:end_pos].strip()
                pos = end_pos
            result.append(type(entry)(entry.index, entry.start_time, entry.end_time,
                                       chunk if chunk else entry.text))
        return result


# ─────────────────── 工具函数 ───────────────────

def merge_bilingual(en_entries, zh_entries):
    """合并双语字幕"""
    merged = []
    max_len = max(len(en_entries), len(zh_entries))
    for i in range(max_len):
        en = en_entries[i] if i < len(en_entries) else None
        zh = zh_entries[i] if i < len(zh_entries) else None
        if en and zh:
            en_clean = re.sub(r'[^\w]', '', en.text.lower())
            zh_clean = re.sub(r'[^\w]', '', zh.text.lower())
            text = en.text if en_clean == zh_clean else f"{en.text}\n{zh.text}"
            merged.append(type(en)(en.index, en.start_time, en.end_time, text))
        elif en:
            merged.append(en)
        else:
            merged.append(zh)
    return merged


def subtitles_to_paragraphs(entries):
    """将字幕条目合并为完整文章段落"""
    if not entries:
        return ""
    paragraphs = []
    current_para = []
    for entry in entries:
        text = entry.text.strip()
        if not text:
            continue
        text = re.sub(r'^>>\s*', '', text)
        text = re.sub(r'^-\s*', '', text)
        current_para.append(text)
        if re.search(r'[.!?。！？…]\s*$', text) or len(" ".join(current_para)) > 200:
            paragraphs.append(" ".join(current_para))
            current_para = []
    if current_para:
        paragraphs.append(" ".join(current_para))
    return "\n\n".join(paragraphs)
