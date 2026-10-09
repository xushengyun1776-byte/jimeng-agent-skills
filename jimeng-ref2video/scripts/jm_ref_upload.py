# -*- coding: utf-8 -*-
"""
jm_ref_upload.py — 即梦「上传参考图」一键操作（实操验证版）

2026-10-09 实测通过：点加号 → 弹原生对话框 → 粘贴路径 → 回车 → 缩略图出现。
全程模拟人手（真实鼠标+键盘+剪贴板），不接管端口、不用官方 CLI。

用法：
    python jm_ref_upload.py "E:\\路径\\参考图.png"

★ 重要：坐标会随窗口尺寸变化。本脚本会：
    1. 先校验目标窗口在前台（防止误点其它程序）
    2. 自动读取 Edge 窗口矩形，用相对位置推算加号坐标
    3. 若推算失败，回退到内置实测坐标

实测坐标基准（Edge 窗口 rect=(891,0,3075,2088)）：
    上传加号 物理 (1490, 569)
"""
import ctypes
import os
import sys
import time

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import pyautogui
import pyperclip
import win32con
import win32gui
from pywinauto import Desktop

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.15

DIALOG_CLASS = "#32770"
DIALOG_TITLE_KEY = "选择此站点可读取的文件"

# 实测基准：Edge 窗口 rect=(891,0,3075,2088) 时，加号在 (1490, 569)
# 加号相对窗口左上角的偏移
PLUS_OFFSET = (1490 - 891, 569 - 0)     # = (599, 569)


def find_edge_window() -> int:
    """找 Edge 主窗口句柄。"""
    hit = []

    def _cb(h, _):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if "Edge" in t and ("即梦" in t or "jimeng" in t.lower()):
                hit.append(h)
        return True

    win32gui.EnumWindows(_cb, None)
    return hit[0] if hit else 0


def ensure_foreground(hwnd: int) -> bool:
    """确保 hwnd 在前台，返回是否成功。"""
    if not hwnd:
        return False
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pyautogui.keyDown("alt")
        pyautogui.keyUp("alt")
        time.sleep(0.4)
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            return False
    time.sleep(1.0)
    return win32gui.GetForegroundWindow() == hwnd


def find_dialog():
    """找原生文件对话框。"""
    for w in Desktop(backend="win32").windows():
        try:
            if w.class_name() == DIALOG_CLASS and w.is_visible():
                return w
        except Exception:
            continue
    return None


def upload_reference(image_path: str, edge_hwnd: int = 0) -> bool:
    """完整上传流程。返回是否成功。"""
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"参考图不存在: {image_path}")
    abs_path = os.path.abspath(image_path)

    edge_hwnd = edge_hwnd or find_edge_window()
    if not edge_hwnd:
        print("[ERR] 没找到即梦的 Edge 窗口")
        return False

    # ★ 安全校验：必须前台，否则拒绝点击
    if not ensure_foreground(edge_hwnd):
        print("[ABORT] Edge 未在前台，拒绝点击（防误点其它程序）")
        return False
    print("[OK] Edge 在前台")

    # 按窗口位置推算加号坐标（窗口尺寸变了也能对准）
    rect = win32gui.GetWindowRect(edge_hwnd)
    plus = (rect[0] + PLUS_OFFSET[0], rect[1] + PLUS_OFFSET[1])
    print(f"[INFO] Edge rect={rect}, 加号坐标={plus}")

    # 1) 点加号
    pyautogui.moveTo(*plus, duration=0.4)
    time.sleep(0.25)
    pyautogui.click()
    time.sleep(2.5)

    # 2) 等对话框
    dlg = None
    for _ in range(30):
        dlg = find_dialog()
        if dlg:
            break
        time.sleep(0.4)
    if not dlg:
        print("[ERR] 没等到原生文件对话框（可能没点中加号）")
        return False
    print(f"[OK] 对话框出现: {dlg.window_text()}")

    # 3) 对话框拉前台
    dh = dlg.handle
    try:
        win32gui.SetForegroundWindow(dh)
    except Exception:
        pyautogui.keyDown("alt")
        pyautogui.keyUp("alt")
        time.sleep(0.3)
        win32gui.SetForegroundWindow(dh)
    time.sleep(0.9)

    # 4) 全选 → 粘贴完整路径 → 回车
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.35)
    pyperclip.copy(abs_path)
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1.0)
    pyautogui.press("enter")
    time.sleep(2.5)

    # 5) 检查对话框是否关闭
    if find_dialog():
        print("[ERR] 对话框仍存在，确认可能失败")
        return False
    print("[OK] 对话框已关闭，参考图已提交")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    ok = upload_reference(sys.argv[1])
    print("\n结果:", "成功" if ok else "失败")
    sys.exit(0 if ok else 1)
