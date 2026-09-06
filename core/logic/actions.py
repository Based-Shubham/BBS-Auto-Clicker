import cv2
import numpy as np
import pyautogui
import os
from core.capture import get_bbs_screenshot
import time
from utils.resource_manager import get_asset_path

def _ensure_matchable(img):
    """Return a version of img safe to pass to cv2.matchTemplate: 3-channel
    BGR, uint8, contiguous in memory. Converts grayscale to BGR and strips an
    alpha channel if present; leaves an already-correct image untouched.

    NOTE: reconstructed as a stopgap — the original implementation was lost
    when actions.py was replaced earlier and isn't recoverable. Signature and
    behavior inferred from how callers use it (single image in, image out).
    """
    if img is None:
        return img
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return np.ascontiguousarray(img)

def check_image_present(template_path: str, screenshot=None, threshold: float = 0.85) -> bool:
    if screenshot is None:
        screenshot = get_bbs_screenshot()

    # Handle asset paths (e.g., "auto_off.png") or full paths
    if not os.path.isabs(template_path) and not template_path.startswith("assets/"):
        # Assume it's an asset name
        template_path = get_asset_path(template_path)
    elif template_path.startswith("assets/"):
        # Handle full asset paths
        from utils.resource_manager import get_resource_path
        template_path = get_resource_path(template_path)

    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if template is None:
        raise FileNotFoundError(f"Template not found: {template_path}")

    res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)

    return max_val >= threshold


def find_and_click_image(template_path: str, screenshot=None, threshold: float = 0.85, double_click: bool = False, top_left: bool = True) -> bool:
    from core.window_utils import get_bbs_window

    if screenshot is None:
        screenshot = get_bbs_screenshot()

    win = get_bbs_window()

    # Handle asset paths (e.g., "auto_off.png") or full paths
    if not os.path.isabs(template_path) and not template_path.startswith("assets/"):
        # Assume it's an asset name
        template_path = get_asset_path(template_path)
    elif template_path.startswith("assets/"):
        # Handle full asset paths
        from utils.resource_manager import get_resource_path
        template_path = get_resource_path(template_path)

    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    if template is None:
        raise FileNotFoundError(f"Template not found: {template_path}")

    res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    
    # Find all locations where the template matches above threshold
    locations = np.where(res >= threshold)
    locations = list(zip(*locations[::-1]))  # Convert to (x, y) format
    
    if not locations:
        return False
    
    if top_left:
        # Sort by y-coordinate first (top to bottom), then by x-coordinate (left to right)
        # This ensures we get the most top-left match
        locations.sort(key=lambda loc: (loc[1], loc[0]))
        max_loc = locations[0]
    else:
        # Find the location with the highest confidence (most accurate match)
        max_val = 0
        max_loc = None
        for loc in locations:
            val = res[loc[1], loc[0]]
            if val > max_val:
                max_val = val
                max_loc = loc
        
        if max_loc is None:
            return False
    
    max_val = res[max_loc[1], max_loc[0]]

    h, w = template.shape[:2]
    center_x = max_loc[0] + w // 2
    center_y = max_loc[1] + h // 2

    global_x = win.left + center_x
    global_y = win.top + center_y + 35  # click was landing above the button — move it down

    if double_click:
        pyautogui.click(global_x, global_y)
        time.sleep(0.5)
        # At high game speeds the screen can fully advance during this gap, so
        # blindly clicking the same coordinates again can hit an unrelated
        # button (e.g. Home) on the next screen instead of a harmless second
        # tap. Re-verify the same template is still there before clicking again.
        verify_screenshot = get_bbs_screenshot()
        verify_res = cv2.matchTemplate(verify_screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, verify_val, _, _ = cv2.minMaxLoc(verify_res)
        if verify_val >= threshold:
            pyautogui.click(global_x, global_y)
    else:
        pyautogui.click(global_x, global_y)
    return True


def check_network_error(screenshot=None) -> bool:
    """Check for and clear the network error popup if present. Can appear at
    any point in the game — menu navigation, mid-quest, or the end screen —
    so this is meant to be called at the top of every loop iteration across
    all stage modules, not just the end-menu handlers."""
    if check_image_present("assets/icons/network_error_retry.png", screenshot=screenshot):
        find_and_click_image("assets/icons/network_error_retry.png", screenshot=screenshot)
        time.sleep(1)
        return True
    return False