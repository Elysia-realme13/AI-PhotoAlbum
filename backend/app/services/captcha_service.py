"""
验证码服务 — 生成图片验证码、存储与校验
"""
import io
import base64
import random
import string
import time
import uuid
from typing import Dict, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# 验证码有效期（秒）
CAPTCHA_TTL = 300

# 内存存储：{ captcha_id: { "code": str, "expires_at": float } }
_store: Dict[str, dict] = {}

# 排除易混淆字符
_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_CODE_LENGTH = 4
_IMG_WIDTH = 140
_IMG_HEIGHT = 50


def _random_color(start: int = 0, end: int = 255) -> Tuple[int, int, int]:
    return (random.randint(start, end), random.randint(start, end), random.randint(start, end))


def _random_char() -> str:
    return random.choice(_CHARS)


def _generate_image(code: str) -> Image.Image:
    """生成带干扰的验证码图片"""
    img = Image.new("RGB", (_IMG_WIDTH, _IMG_HEIGHT), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 背景噪点
    for _ in range(80):
        x, y = random.randint(0, _IMG_WIDTH), random.randint(0, _IMG_HEIGHT)
        draw.point((x, y), fill=_random_color(180, 255))

    # 干扰线
    for _ in range(3):
        x1, y1 = random.randint(0, _IMG_WIDTH // 3), random.randint(0, _IMG_HEIGHT)
        x2, y2 = random.randint(_IMG_WIDTH * 2 // 3, _IMG_WIDTH), random.randint(0, _IMG_HEIGHT)
        draw.line([(x1, y1), (x2, y2)], fill=_random_color(100, 180), width=2)

    # 绘制文字
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except OSError:
        font = ImageFont.load_default()

    char_width = _IMG_WIDTH // (_CODE_LENGTH + 1)
    for i, ch in enumerate(code):
        x = char_width * (i + 1) - 8 + random.randint(-4, 4)
        y = random.randint(3, 10)
        # 每个字符单独绘制，略有旋转
        char_img = Image.new("RGBA", (40, 40), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_img)
        color = _random_color(0, 120)
        char_draw.text((4, 2), ch, font=font, fill=color)
        # 轻微旋转
        char_img = char_img.rotate(random.randint(-20, 20), expand=False, fillcolor=(255, 255, 255, 0))
        img.paste(char_img, (x, y), char_img)

    # 模糊 + 锐化
    img = img.filter(ImageFilter.GaussianBlur(0.5))
    return img


def generate_captcha() -> Tuple[str, str]:
    """
    生成验证码，返回 (captcha_id, base64_image)
    """
    # 清理过期验证码
    _cleanup()

    code = "".join(_random_char() for _ in range(_CODE_LENGTH))
    captcha_id = uuid.uuid4().hex

    _store[captcha_id] = {
        "code": code,
        "expires_at": time.time() + CAPTCHA_TTL,
    }

    img = _generate_image(code)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    return captcha_id, f"data:image/png;base64,{b64}"


def verify_captcha(captcha_id: str, code: str) -> bool:
    """
    校验验证码，校验成功才删除；失败保留（允许重试，最多 5 次）
    """
    _cleanup()

    if not captcha_id or not code:
        return False

    entry = _store.get(captcha_id)
    if not entry:
        return False

    if "attempts" not in entry:
        entry["attempts"] = 0

    entry["attempts"] += 1

    is_match = entry["code"].upper() == code.strip().upper()

    if is_match:
        _store.pop(captcha_id, None)  # 校验成功，立即删除防止复用
        return True

    # 超过最大尝试次数，删除验证码
    if entry["attempts"] >= 5:
        _store.pop(captcha_id, None)

    return False


def _cleanup():
    """清理过期验证码"""
    now = time.time()
    expired = [k for k, v in _store.items() if v["expires_at"] < now]
    for k in expired:
        _store.pop(k, None)
