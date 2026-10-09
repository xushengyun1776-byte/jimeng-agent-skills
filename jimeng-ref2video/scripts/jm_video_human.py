# -*- coding: utf-8 -*-
"""
jm_video_human.py — 即梦网页「参考图生视频」纯人手模拟工具库

设计原则（用户明令）：
  * 全程模拟人手操作：真实鼠标移动 + 真实点击 + 真实键盘/剪贴板
  * 不接管端口、不连 CDP、不用官方 CLI（标准会员无 CLI 权限）
  * 不依赖 DOM 选择器（因为原生文件对话框根本不在浏览器渲染树里）

适用：即梦 jimeng.jianying.com 网页版，标准会员套餐。

依赖：
    pip install pyautogui pyperclip pywinauto pillow opencv-python numpy

用法：
    python jm_video_human.py anchors          # 打印关键坐标锚点（自检用）
    python jm_video_human.py screenshot       # 全屏截图存到 _shots/
    python jm_video_human.py locate <模板图>   # 在屏幕上找模板图的坐标
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from dataclasses import dataclass
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# 0. DPI 适配 —— 必须在 import pyautogui 之前做，否则 150% 缩放下坐标全错
# ---------------------------------------------------------------------------

def enable_dpi_awareness() -> None:
    """让进程物理像素感知。用户屏 3840x2160 @150%，逻辑坐标 2560x1440。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE_V2
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


enable_dpi_awareness()

import pyautogui  # noqa: E402
import pyperclip  # noqa: E402

# 关闭 pyautogui 的"挪到角落就中断"保护（会把鼠标甩到 0,0，风险大）
pyautogui.FAILSAFE = False
# 手感参数：模拟人手的移动节奏，不要瞬移
pyautogui.PAUSE = 0.15

# ---------------------------------------------------------------------------
# 1. 通用工具
# ---------------------------------------------------------------------------

SHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots")

# 即梦网页关键坐标（相对 2560x1440 逻辑分辨率标定；其它分辨率按比例缩放）
_REF_W, _REF_H = 2560, 1440


def screen_size() -> Tuple[int, int]:
    return pyautogui.size()


def scale(x: float, y: float) -> Tuple[int, int]:
    """把 2560x1440 基准坐标换算到当前屏幕。"""
    w, h = screen_size()
    return int(x * w / _REF_W), int(y * h / _REF_H)


@dataclass
class Anchor:
    """关键 UI 锚点。坐标为 2560x1440 基准。

    ★ 以下锚点于 2026-10-09 在真实即梦页面实测标定（原生物理坐标 3840x2160），
      已用「十字准星 + 视觉模型二次确认」逐个验证，非估算值。
      实测物理坐标（3840x2160）→ 基准坐标（2560x1440，即物理/1.5）：
    """
    # —— 即梦首页创作入口（已实测验证）——
    upload_plus: Tuple[int, int] = (994, 380)       # 物理(1491, 570)「+」上传卡片，准星确认正中
    prompt_box: Tuple[int, int] = (1150, 403)       # 物理(1725, 605) 输入框内空白点击点
    send_btn: Tuple[int, int] = (1907, 449)         # 物理(2860, 673) 圆形发送键，距圆心偏差<4px
    agent_tag: Tuple[int, int] = (1025, 449)        # 物理(1537, 673)「Agent 模式」标签
    # —— 以下为待实测（页面改版或不同入口下需重标）——
    tab_generate: Tuple[int, int] = (1300, 264)     # 物理(1950, 396)「生成」分段按钮
    tab_canvas: Tuple[int, int] = (1453, 264)       # 物理(2180, 396)「画布」分段按钮
    tab_video: Tuple[int, int] = (1280, 90)         # 顶部「视频生成」入口（未实测）
    tail_frame_switch: Tuple[int, int] = (1900, 700)  # 「使用尾帧」开关（未实测）


# 实测原始数据（物理像素 3840x2160），便于换屏后重新换算
PHYSICAL_480 = {
    "upload_plus": (1491, 570),
    "prompt_box": (1725, 605),
    "send_btn": (2860, 673),
    "agent_tag": (1537, 673),
}
PHYSICAL_SCREEN = (3840, 2160)


ANCHOR = Anchor()


def focus_window(title_keyword: str = "即梦", strict: bool = True) -> bool:
    """把标题含关键字的窗口拉到前台。返回是否成功。

    ★ strict=True 时会校验前台窗口确实切换成功 —— 人手模拟最大的风险是
      「以为切过去了，实际鼠标点在用户正在用的别的程序上」。
    """
    import win32gui
    import win32con
    hit = []

    def _cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if title_keyword in t:
                hit.append(hwnd)
        return True

    win32gui.EnumWindows(_cb, None)
    if not hit:
        print(f"[focus] 未找到含「{title_keyword}」的窗口")
        return False

    hwnd = hit[0]
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        # Windows 前台锁定时的兜底：模拟 Alt 键
        pyautogui.keyDown("alt")
        pyautogui.keyUp("alt")
        time.sleep(0.4)
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            print("[focus] SetForegroundWindow 失败")
            return False

    time.sleep(0.8)
    if strict:
        cur = win32gui.GetForegroundWindow()
        if cur != hwnd:
            print(f"[focus] 前台校验失败：期望 {hwnd}，实际 {cur}（{win32gui.GetWindowText(cur)[:40]}）")
            return False
    return True


def find_editor_tab(title_keyword: str = "即梦", editor_keyword: str = "Edge"):
    """枚举浏览器标签页，找到含关键字的那个，返回 (标签中心物理坐标, 浏览器hwnd)。"""
    import win32gui
    from pywinauto import Desktop

    browser = []
    def _cb(h, _):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if editor_keyword in t:
                browser.append(h)
        return True
    win32gui.EnumWindows(_cb, None)
    if not browser:
        print(f"[tab] 未找到 {editor_keyword} 窗口")
        return None, None

    hwnd = browser[0]
    try:
        app = Desktop(backend="uia").window(handle=hwnd)
        for d in app.descendants(control_type="TabItem"):
            nm = d.window_text()
            if title_keyword in nm:
                r = d.rectangle()
                cx, cy = (r.left + r.right) // 2, (r.top + r.bottom) // 2
                print(f"[tab] 找到「{nm[:40]}」标签 @ ({cx},{cy})")
                return (cx, cy), hwnd
    except Exception as e:
        print("[tab] 枚举标签页失败:", e)
    print(f"[tab] 未找到含「{title_keyword}」的标签页")
    return None, hwnd


def switch_to_tab(title_keyword: str = "即梦", editor_keyword: str = "Edge") -> bool:
    """安全切换到目标标签页：找标签 → 校验前台 → 点击。"""
    tab, hwnd = find_editor_tab(title_keyword, editor_keyword)
    if not tab:
        return False
    if not focus_window(editor_keyword, strict=True):
        print("[tab] 中止：浏览器未成功切到前台，拒绝点击（防止误点其它程序）")
        return False
    human_click(*tab)
    time.sleep(2.5)
    return True


def human_move(x: int, y: int, duration: float = 0.35) -> None:
    """带缓动的真实鼠标移动，不是瞬移。"""
    pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)


def human_click(x: int, y: int, button: str = "left", double: bool = False) -> None:
    """先移动到目标 → 微停顿 → 点击（模拟人手的"瞄准-按下"节奏）。"""
    human_move(x, y)
    time.sleep(0.12)
    if double:
        pyautogui.doubleClick(button=button)
    else:
        pyautogui.click(button=button)
    time.sleep(0.35)


def click_anchor(name: str, **kw) -> None:
    """按锚点名点击（自动 DPI 缩放）。"""
    if not hasattr(ANCHOR, name):
        raise KeyError(f"未知锚点: {name}")
    x, y = getattr(ANCHOR, name)
    x, y = scale(x, y)
    print(f"[click] {name} -> ({x}, {y})")
    human_click(x, y, **kw)


def type_text(text: str, interval: float = 0.03) -> None:
    """输入文本。中文走剪贴板粘贴（pyautogui 打不出中文）。"""
    if all(ord(c) < 128 for c in text):
        pyautogui.write(text, interval=interval)
    else:
        paste_text(text)


def paste_text(text: str) -> None:
    """剪贴板粘贴，能处理中文/emoji。"""
    backup = ""
    try:
        backup = pyperclip.paste()
    except Exception:
        pass
    pyperclip.copy(text)
    time.sleep(0.25)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.45)
    if backup:
        try:
            pyperclip.copy(backup)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 2. 图像定位（纯人手的"眼睛"）
# ---------------------------------------------------------------------------

def user_idle_seconds() -> float:
    """用户距上次键鼠输入的秒数。人手模拟抢鼠标，操作前必须检查。"""
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(lii)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    return (ctypes.windll.kernel32.GetTickCount() - lii.dwTime) / 1000


def guard_idle(min_idle: float = 30.0) -> bool:
    """用户空闲超过 min_idle 秒才允许操作。返回是否放行。"""
    idle = user_idle_seconds()
    if idle < min_idle:
        print(f"[guard] 用户 {idle:.0f}s 前还在动鼠标/键盘，暂停操作（阈值 {min_idle:.0f}s）")
        return False
    print(f"[guard] 用户已空闲 {idle:.0f}s，放行")
    return True


def screenshot(path: Optional[str] = None):
    """全屏截图。返回 PIL Image。"""
    os.makedirs(SHOT_DIR, exist_ok=True)
    if path is None:
        path = os.path.join(SHOT_DIR, time.strftime("shot_%Y%m%d_%H%M%S.png"))
    img = pyautogui.screenshot()
    img.save(path)
    return img, path


def locate_on_screen(template_path: str, confidence: float = 0.85) -> Optional[Tuple[int, int]]:
    """在屏幕上找模板图中心坐标。需要 opencv-python。"""
    try:
        import cv2
        import numpy as np
    except ImportError:
        raise RuntimeError("图像定位需要 opencv-python：pip install opencv-python numpy")

    img, _ = screenshot()
    screen = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    tmpl = cv2.imread(template_path)
    if tmpl is None:
        raise FileNotFoundError(f"模板图读不到: {template_path}")

    res = cv2.matchTemplate(screen, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val < confidence:
        print(f"[locate] 未命中（最高相似度 {max_val:.3f} < {confidence}）")
        return None
    h, w = tmpl.shape[:2]
    cx, cy = max_loc[0] + w // 2, max_loc[1] + h // 2
    print(f"[locate] 命中 {os.path.basename(template_path)} @ ({cx},{cy}) 相似度={max_val:.3f}")
    return cx, cy


# ---------------------------------------------------------------------------
# 2.5 ★ 发送按钮识别（图像法，不依赖坐标）
# ---------------------------------------------------------------------------
# 用户确认（2026-10-09）：输入框右下角【白色圆底 + 黑色向上箭头】= 发送确认键。
# 关键特性：
#   * 输入框【有内容】时按钮是白圆（激活态）→ 可点
#   * 输入框【为空】时按钮是灰圆（禁用态）→ 点了没反应
# 所以"找白圆"本身就是发送就绪的安全联锁：找到才点，找不到说明状态不对。
# 白圆在深色页面上对比度极高（亮度 ~247 vs 背景 ~22），用
# 亮度阈值 + 连通域 + 圆形度 即可稳定定位，窗口怎么移动/缩放都不怕。
# ---------------------------------------------------------------------------

def find_white_circles(img=None, min_area: int = 600, max_area: int = 20000,
                        min_lum: int = 140):
    """找画面中所有白色圆形按钮。返回 [(cx, cy, r, lum), ...]。"""
    try:
        import cv2
        import numpy as np
    except ImportError:
        raise RuntimeError("需要 opencv-python：pip install opencv-python numpy")
    if img is None:
        img, _ = screenshot()
    a = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    _, bw = cv2.threshold(gray, min_lum, 255, cv2.THRESH_BINARY)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(bw, connectivity=8)
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if not (min_area <= area <= max_area):
            continue
        if not (0.75 <= w / h <= 1.33):          # 近正方形包围盒（排除文字行/横条）
            continue
        fill = area / (w * h)
        if not (0.6 <= fill <= 0.95):            # 圆形度 ≈ π/4
            continue
        mask = labels == i
        lum = float(gray[mask].mean())
        if lum < min_lum:
            continue
        out.append((int(cents[i][0]), int(cents[i][1]), (w + h) / 4, round(lum)))
    out.sort(key=lambda c: -c[2])
    return out


def find_send_btn(img=None, hint: Optional[Tuple[int, int]] = None,
                  tol: int = 500) -> Optional[Tuple[int, int]]:
    """定位白色圆形发送按钮。

    hint: 可选的期望位置（如 Anchor.send_btn 换算后的坐标），用于在多个白圆候选里
          挑离输入框最近的那个；不给则返回最大的白圆。
    返回 (x, y) 或 None（None = 按钮未激活/页面状态不对，不要点）。
    """
    cands = find_white_circles(img)
    if hint:
        near = [c for c in cands
                if abs(c[0] - hint[0]) < tol and abs(c[1] - hint[1]) < tol]
        if near:
            cands = near
    if not cands:
        print("[send] 未找到白色发送按钮（输入框可能为空/页面状态不对）")
        return None
    cx, cy, r, lum = cands[0]
    print(f"[send] 白圆发送按钮 @ ({cx},{cy}) r={r:.0f} 亮度={lum}")
    return cx, cy


def click_send(img=None, hint: Optional[Tuple[int, int]] = None) -> bool:
    """找到白色发送按钮并点击。找不到则不点，返回 False。"""
    pos = find_send_btn(img, hint)
    if not pos:
        return False
    human_click(*pos)
    return True


# ---------------------------------------------------------------------------
# 3. ★ 原生文件对话框接管 —— 整个方案的核心
# ---------------------------------------------------------------------------
# 为什么必须走这条路：
#   点「+」上传后弹出的是 Windows 原生 GetOpenFileNameW 对话框（窗口类 #32770），
#   它【不在浏览器的 DOM/渲染树里】。所以 CDP、JS 注入、selenium 的 send_keys
#   全都够不到它。唯一可行且稳定的方式是：等它出现 → 往「文件名」框粘贴完整路径 → 回车。
#   已实测：中文路径完全可行（见 references/踩坑记录.md 的验证记录）。
# ---------------------------------------------------------------------------

DIALOG_CLASS = "#32770"


def wait_for_dialog(title_keyword: str = "", timeout: float = 15.0) -> bool:
    """等待原生文件对话框出现。"""
    from pywinauto import Desktop
    deadline = time.time() + timeout
    while time.time() < deadline:
        for w in Desktop(backend="win32").windows():
            try:
                if w.class_name() == DIALOG_CLASS and w.is_visible():
                    t = w.window_text()
                    if title_keyword and title_keyword not in t:
                        continue
                    print(f"[dialog] 已出现: {t}")
                    return True
            except Exception:
                continue
        time.sleep(0.4)
    print("[dialog] 等待超时，未发现原生对话框")
    return False


def fill_dialog_path(file_path: str, confirm: bool = True,
                     dialog_title_keyword: str = "", pre_wait: float = 0.8) -> bool:
    """
    在已打开的原生文件对话框里，把完整路径填进「文件名」框并确认。

    关键细节：
      * 必须先 Ctrl+A 全选清空 —— 文件名框可能有默认残留
      * 中文路径用剪贴板粘贴，不用 pyautogui.write（打不出中文）
      * 回车即等价于点「打开」
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"参考图不存在: {file_path}")
    abs_path = os.path.abspath(file_path)

    if not wait_for_dialog(dialog_title_keyword, timeout=15.0):
        return False

    time.sleep(pre_wait)                    # 等对话框动画稳定
    pyautogui.hotkey("ctrl", "a")           # 全选文件名框现有内容
    time.sleep(0.3)
    pyperclip.copy(abs_path)
    time.sleep(0.25)
    pyautogui.hotkey("ctrl", "v")           # 粘贴完整路径
    time.sleep(0.8)
    print(f"[dialog] 已填入路径: {abs_path}")

    if confirm:
        pyautogui.press("enter")            # = 点「打开」
        time.sleep(2.0)
        print("[dialog] 已回车确认")
    return True


def upload_reference(file_path: str, plus_anchor: str = "upload_plus") -> bool:
    """
    完整上传动作：点「+」→ 等原生对话框 → 填路径 → 确认。
    """
    click_anchor(plus_anchor)
    time.sleep(1.5)                         # 等浏览器调起原生对话框
    return fill_dialog_path(file_path)


# ---------------------------------------------------------------------------
# 4. 自检 / CLI
# ---------------------------------------------------------------------------

def print_env() -> None:
    w, h = screen_size()
    print("=" * 60)
    print("即梦人手模拟 · 环境自检")
    print("=" * 60)
    print(f"屏幕物理分辨率 : {w} x {h}")
    print(f"基准坐标       : {_REF_W} x {_REF_H}")
    print(f"缩放系数       : x{w / _REF_W:.3f} y{h / _REF_H:.3f}")
    print(f"FAILSAFE       : {pyautogui.FAILSAFE}  (已关闭，防鼠标被甩到角落)")
    print("-" * 60)
    for f in Anchor.__dataclass_fields__:
        raw = getattr(ANCHOR, f)
        print(f"  {f:20s} 基准{raw}  →  实际{scale(*raw)}")
    print("=" * 60)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "anchors"
    if cmd == "anchors":
        print_env()
    elif cmd == "screenshot":
        _, p = screenshot()
        print("已截图:", p)
    elif cmd == "locate":
        if len(sys.argv) < 3:
            print("用法: python jm_video_human.py locate <模板图路径>")
            sys.exit(1)
        print(locate_on_screen(sys.argv[2]))
    elif cmd == "dialog":
        # 调试：等一个已弹出的对话框并填入给定路径
        if len(sys.argv) < 3:
            print("用法: python jm_video_human.py dialog <文件路径>")
            sys.exit(1)
        fill_dialog_path(sys.argv[2])
    elif cmd == "tab":
        # 安全切换到即梦标签页并截图（校验前台窗口，防误点）
        if switch_to_tab():
            _, p = screenshot()
            print("已切到即梦并截图:", p)
        else:
            print("切换失败")
    elif cmd == "focus":
        ok = focus_window("即梦", strict=True)
        print("前台切换:", "成功" if ok else "失败")
    elif cmd == "findsend":
        # 只找不点：验证白色发送按钮识别
        pos = find_send_btn()
        print("发送按钮:", pos if pos else "未找到（输入框为空或状态不对）")
    else:
        print(__doc__)
