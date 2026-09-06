import cv2
from core.capture import get_bbs_screenshot

# Run this while the game is sitting on the Chapter-clear "TAP SCREEN" screen.
# It saves a raw frame from the EXACT same capture path the bot uses
# (mss grab of win.left/top/width/height), so any crop you take from it
# will be pixel-scale-correct against future live captures.
import time

print("Capturing every 0.3s for 15s - get the game onto the TAP SCREEN screen now...")
for i in range(50):
    img = get_bbs_screenshot()
    if img is not None:
        cv2.imwrite(f"live_capture_{i}.png", img)
    time.sleep(0.3)
print("Done. Check live_capture_*.png for one that has the TAP SCREEN screen.")
