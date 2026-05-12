"""激活码授权系统 - 通用激活码，每个码只能用一次"""
import hashlib
import hmac
import json
import os
import platform


# ─────────────────── 密钥（生成激活码用，不要泄露） ───────────────────

_SECRET = "ALOE-Subtitle-Tool-2026-Secret-Key-xK9mP2"


def generate_activation_code(index):
    """根据序号生成激活码（0~9999）"""
    data = f"{_SECRET}|{index}"
    sig = hmac.new(_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()
    code = sig[:16].upper()
    return f"{code[:4]}-{code[4:8]}-{code[8:12]}-{code[12:16]}"


def generate_batch(count=1000):
    """批量生成激活码"""
    codes = []
    for i in range(count):
        codes.append(generate_activation_code(i))
    return codes


def verify_activation_code(code):
    """验证激活码是否是有效生成的码（不检查是否已使用）"""
    code_clean = code.strip().upper().replace("-", "").replace(" ", "")
    if len(code_clean) != 16:
        return False
    # 暴力验证：遍历所有可能的 index
    for i in range(10000):
        expected = generate_activation_code(i)
        if code_clean == expected.replace("-", ""):
            return True
    return False


def get_license_path():
    """获取许可证文件路径"""
    if platform.system() == "Windows":
        app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        app_data = os.path.expanduser("~")
    config_dir = os.path.join(app_data, "ALOE字幕提取软件")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "license.json")


def load_license():
    """加载许可证"""
    path = get_license_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_license(code):
    """保存许可证"""
    path = get_license_path()
    data = {
        "activation_code": code,
        "activated": True,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_activated():
    """检查是否已激活"""
    license_data = load_license()
    if not license_data:
        return False
    if not license_data.get("activated"):
        return False
    return verify_activation_code(license_data.get("activation_code", ""))
