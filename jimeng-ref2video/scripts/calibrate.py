# -*- coding: utf-8 -*-
"""
calibrate.py — UI 坐标标定工具（准星自检法）

用途：给任何网页/软件界面标定可点击元素的精确坐标，用于人手模拟自动化。
核心思想：不靠猜，靠「裁剪放大 + 视觉模型定位 + 准星二次确认」。

用法：
    # 1) 截全屏
    python calibrate.py shot

    # 2) 裁剪某区域并放大，让视觉模型给出元素坐标
    python calibrate.py crop <x1> <y1> <x2> <y2> [放大倍数]

    # 3) 在候选坐标处画准星，生成自检图
    python calibrate.py probe <x> <y> [裁剪半径]

前提：全屏图保存在 shots/full.png；视觉模型走百炼（可用自有网关替换）。
输出：所有中间图存在脚本同级 _shots/ 或 shots/ 下，便于人工复核。

★ 关键经验：
    - 视觉模型直接标坐标会有 ±40px 误差，必须做准星二次确认
    - 裁剪放大能把等效分辨率提高 2-4 倍，精度可达 ±5px
    - 未经验证的坐标写进自动化脚本 = 埋雷
"""

from __future__ import annotations

import base64
import io
import json
import os
import sys
import urllib.request

from PIL import Image, ImageDraw

# ---- 视觉模型配置（本机百炼 token-plan 网关；可换成任意 OpenAI 兼容端点）----
VLM_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions"
VLM_KEY = os.environ.get("VLM_API_KEY", "")   # 建议用环境变量传入，不要硬编码
VLM_MODEL = os.environ.get("VLM_MODEL", "qwen3.8-flash")

HERE = os.path.dirname(os.path.abspath(__file__))
SHOT_DIR = os.path.join(HERE, "shots")


def _b64(pil: Image.Image) -> str:
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def vlm_ask(img: Image.Image, question: str, max_tokens: int = 800) -> str:
    """问视觉模型。返回文本。"""
    if not VLM_KEY:
        raise RuntimeError("未设置 VLM_API_KEY 环境变量")
    body = {
        "model": VLM_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + _b64(img)}},
        ]}],
    }
    req = urllib.request.Request(
        VLM_URL, data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "Authorization": "Bearer " + VLM_KEY})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
        m = d["choices"][0]["message"]
        return (m.get("content") or str(m.get("reasoning_content", ""))).strip()


def shot(path: str = None) -> Image.Image:
    """截全屏并保存。"""
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    import pyautogui
    os.makedirs(SHOT_DIR, exist_ok=True)
    img = pyautogui.screenshot()
    path = path or os.path.join(SHOT_DIR, "full.png")
    img.save(path)
    print(f"[shot] {img.size} -> {path}")
    return img


def crop_zoom(src: str, box, z: float = 3.0, out: str = None) -> tuple:
    """裁剪 + 放大。返回 (放大图, 相对路径)。"""
    img = Image.open(src)
    c = img.crop(box)
    big = c.resize((int(c.size[0] * z), int(c.size[1] * z)), Image.LANCZOS)
    out = out or os.path.join(SHOT_DIR, "crop.png")
    big.save(out)
    print(f"[crop] {box} -> {c.size}, x{z} -> {big.size} @ {out}")
    return big, box, z


def probe(src: str, cx: int, cy: int, radius: int = 120, z: float = 4.0, out: str = None) -> str:
    """在 (cx,cy) 画十字准星，返回自检图路径。"""
    img = Image.open(src)
    c = img.crop((cx - radius, cy - radius, cx + radius, cy + radius)).convert("RGB")
    c = c.resize((c.size[0] * z, c.size[1] * z), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    mx = my = radius * z
    d.line([(mx, 0), (mx, c.size[1])], fill=(255, 0, 0), width=3)      # 红竖线
    d.line([(0, my), (c.size[0], my)], fill=(0, 160, 255), width=3)    # 蓝横线
    d.ellipse([mx - 26, my - 26, mx + 26, my + 26], outline=(255, 255, 0), width=3)
    out = out or os.path.join(SHOT_DIR, f"probe_{cx}_{cy}.png")
    c.save(out)
    print(f"[probe] ({cx},{cy}) 准星图 @ {out}")
    return out


PROBE_Q = """图上有【红色竖线】和【蓝色横线】，交点处有黄色圆圈。
请回答：
1. 黄圈中心落在什么元素上？（加号图标 / 按钮 / 文字 / 输入框空白处 / 什么都没有）
2. 若未精确命中目标，说明偏了多少（以这张放大图的像素计，左/右/上/下）。
只描述看到的，不要猜。"""


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    src = os.path.join(SHOT_DIR, "full.png")

    if cmd == "shot":
        shot()
    elif cmd == "crop":
        if len(sys.argv) < 6:
            print("用法: python calibrate.py crop <x1> <y1> <x2> <y2> [放大倍数]")
            sys.exit(1)
        box = tuple(int(v) for v in sys.argv[2:6])
        z = float(sys.argv[6]) if len(sys.argv) > 6 else 3.0
        big, _, _ = crop_zoom(src, box, z)
        print("\n对模型提问（可自行替换问题）：")
        print(">> 请给出目标元素在这张图的坐标 (x, y)")
    elif cmd == "probe":
        if len(sys.argv) < 4:
            print("用法: python calibrate.py probe <x> <y> [半径]")
            sys.exit(1)
        cx, cy = int(sys.argv[2]), int(sys.argv[3])
        r = int(sys.argv[4]) if len(sys.argv) > 4 else 120
        p = probe(src, cx, cy, r)
        print("\n模型判断：")
        print(vlm_ask(Image.open(p), PROBE_Q))
    else:
        print(__doc__)
