import keyboard
import threading
from core.stop_controller import stop_controller
from utils.logger import warning
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

def start_esc_listener(on_escape_callback=None):
    def listen():
        keyboard.wait("esc")
        warning("ESC key pressed — stopping execution")
        stop_controller.stop()

        if on_escape_callback:
            # Ensure UI-related actions happen on the main thread
            QTimer.singleShot(0, on_escape_callback)
        
        # Force Qt to immediately process the close/stop event so the UI doesn't freeze
        QTimer.singleShot(0, lambda: QApplication.processEvents())

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()