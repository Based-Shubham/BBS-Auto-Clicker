import threading
import keyboard
from PySide6.QtWidgets import QApplication

class StopController:
    def __init__(self):
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def should_stop(self):
        # Keep the GUI responsive and process pending timer/click events
        try:
            QApplication.processEvents()
        except Exception:
            pass

        # Directly check if ESC is held/pressed to stop immediately
        try:
            if keyboard.is_pressed("esc"):
                self.stop()
        except Exception:
            pass

        return self._stop_event.is_set()

    def reset(self):
        self._stop_event.clear()

stop_controller = StopController()