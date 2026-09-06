import sys
import os

# Make the process DPI-aware so window coordinates (pygetwindow), screen
# capture (mss), and click coordinates (pyautogui) all agree on physical
# pixels. Without this, on any display scale other than 100% clicks land
# offset from the actual button — "near" but not "on" it.
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# pythonw.exe has no console, so fds 1/2 (stdout/stderr) are invalid — any
# write to them, including Qt's own native warnings, crashes the process
# before the GUI can show. Redirect the real file descriptors to a log file.
_crash_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
if sys.stdout is None or sys.stderr is None:
    _log_file = open(_crash_log_path, "a", buffering=1)
    os.dup2(_log_file.fileno(), 1)
    os.dup2(_log_file.fileno(), 2)
    sys.stdout = _log_file
    sys.stderr = _log_file

def _log_uncaught_exceptions(exc_type, exc_value, exc_tb):
    import traceback
    traceback.print_exception(exc_type, exc_value, exc_tb, file=sys.stderr)

sys.excepthook = _log_uncaught_exceptions

from gui.main_window import run
from utils.debug import open_debug_terminal
from utils.settings import settings


if __name__ == "__main__":
    if settings["debug_mode"]:
        open_debug_terminal()
    run()