import time
import ctypes
from ctypes import wintypes
import pygetwindow as gw
from pywinauto import Application
from utils.logger import warning

def is_bbs_focused() -> bool:
    active = gw.getActiveWindow()
    return active and "BLEACH" in active.title

def get_bbs_window():
    windows = gw.getWindowsWithTitle("Bleach: Brave Souls")
    if not windows:
        raise Exception("BLEACH window not found!")
    return windows[0]

def get_client_area_screen(hwnd):
    """Return (left, top, width, height) of the window's CLIENT area in screen
    coordinates — i.e. just the game render surface, excluding the title bar
    and window borders that win.left/top/width/height (GetWindowRect) include.
    Templates are cropped from the client area only, so capture must match it
    exactly or matches drift/fail near edges."""
    rect = wintypes.RECT()
    ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect))
    pt = wintypes.POINT(0, 0)
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    return pt.x, pt.y, width, height

def is_fullscreen(win):
    import ctypes
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    return win.left == 0 and win.top == 0 and win.width == screen_width and win.height == screen_height

def force_focus_bbs_window():
    win = get_bbs_window()

    try:
        app = Application().connect(handle=win._hWnd)
        app_window = app.window(handle=win._hWnd)
        app_window.set_focus()
        time.sleep(0.5)
    except Exception as e:
        print(f"[!] Failed to focus window: {e}")

    return win

def is_game_window_valid():
    windows = gw.getWindowsWithTitle("Bleach: Brave Souls")
    if not windows:
        warning("BLEACH window not found!")
        return False
    return True