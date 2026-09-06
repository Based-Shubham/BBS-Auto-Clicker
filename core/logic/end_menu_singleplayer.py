import time
from core.actions import find_and_click_image, check_image_present, check_network_error
from core.capture import get_bbs_screenshot
from core.stop_controller import stop_controller
from utils.logger import debug, error
from PySide6.QtWidgets import QApplication

SUB_STORY_BANNERS = [
    "banner_human_world.png",
    "banner_soul_society.png",
    "banner_hueco_mundo.png",
    "banner_side_stories.png",
    "banner_others.png"
]

def handle_end_menu_singleplayer(timeout=45.0):
    """Handles the post-quest reward screens, friend requests, and screen taps until returned to a story menu."""
    debug("[End Menu] Starting single-player end menu handler...")
    
    # 1. FAIL-SAFE: Watchdog timer to prevent infinite loops if the game freezes or gets stuck
    start_time = time.time()

    while not stop_controller.should_stop():
        # Check if we have exceeded the maximum safe duration in this menu
        if time.time() - start_time > timeout:
            error(f"[End Menu] FAIL-SAFE TRIGGERED: Stuck in end menu for over {timeout}s. Exiting loop.")
            break

        # Keep the PySide6 UI event loop responsive
        try:
            QApplication.processEvents()
        except Exception:
            pass

        screenshot = get_bbs_screenshot()
        if screenshot is None:
            time.sleep(0.05)
            continue

        if check_network_error(screenshot=screenshot):
            continue

        # 2. EXIT CONDITION: Check if we are back on a Sub Story banner screen or chapter list.
        returned_to_story_menu = False
        for banner_icon in SUB_STORY_BANNERS:
            # STRICT 0.88: Ensures it perfectly clicks the right banner without misidentifying colors!
            if check_image_present(f"assets/icons/{banner_icon}", screenshot=screenshot, threshold=0.88):
                debug(f"[End Menu] Detected Sub Story banner ({banner_icon}) — clicking to return to menu.")
                find_and_click_image(f"assets/icons/{banner_icon}", threshold=0.88)
                time.sleep(0.15) # MAX SPEED: Optimized for 4x speed mods
                returned_to_story_menu = True
                break

        if returned_to_story_menu:
            screenshot = get_bbs_screenshot()
            # Added a strict threshold of 0.85 to the back button confirmation
            if check_image_present("assets/icons/back.png", screenshot=screenshot, threshold=0.85):
                debug("[End Menu] Confirmed back on category grid — exiting end menu handler.")
                break
            else:
                continue

        # --- STRICT EXIT CONDITIONS ---
        # Fixed the sub_new trap! Bumped to 0.88 so it doesn't falsely exit when seeing "CLEAR"
        if (check_image_present("assets/icons/prepare_for_quest.png", screenshot=screenshot, threshold=0.85) or 
            check_image_present("assets/icons/sub_new.png", screenshot=screenshot, threshold=0.88) or
            check_image_present("assets/icons/human_world.png", screenshot=screenshot, threshold=0.88) or
            check_image_present("assets/icons/soul_society.png", screenshot=screenshot, threshold=0.88) or
            check_image_present("assets/icons/back.png", screenshot=screenshot, threshold=0.85)):
            debug("[End Menu] Back on Sub Story screen — exiting end menu handler.")
            break

        # 3. CLICK BUTTONS: Handle all standard end-of-quest buttons and prompts
        # Added STRICT thresholds (0.88) to all generic UI buttons so they don't misclick!
        if check_image_present("assets/icons/tap_screen.png", screenshot=screenshot, threshold=0.70): # Kept lower due to transparent text
            debug("[Game] Found 'tap_screen' icon.")
            if find_and_click_image("assets/icons/tap_screen.png", threshold=0.70):
                debug("[Game] Clicked 'tap_screen'.")
                time.sleep(0.03)
                continue

        elif check_image_present("assets/icons/tap_here_to_continue.png", screenshot=screenshot, threshold=0.70): # Kept lower due to transparent text
            debug("[Game] Found 'tap_here_to_continue' icon.")
            if find_and_click_image("assets/icons/tap_here_to_continue.png", threshold=0.70):
                debug("[Game] Clicked 'tap_here_to_continue'.")
                time.sleep(0.03)
                continue

        elif check_image_present("assets/icons/cancel.png", screenshot=screenshot, threshold=0.88):
            debug("[Game] Found 'cancel' icon (e.g., friend request prompt).")
            if find_and_click_image("assets/icons/cancel.png", threshold=0.88):
                debug("[Game] Clicked 'cancel'.")
                time.sleep(0.03)
                continue

        elif check_image_present("assets/icons/close.png", screenshot=screenshot, threshold=0.88):
            debug("[Game] Found 'close' icon.")
            if find_and_click_image("assets/icons/close.png", threshold=0.88):
                debug("[Game] Clicked 'close'.")
                time.sleep(0.03)
                continue

        elif check_image_present("assets/icons/ok.png", screenshot=screenshot, threshold=0.88):
            debug("[Game] Found 'ok' icon.")
            if find_and_click_image("assets/icons/ok.png", threshold=0.88):
                debug("[Game] Clicked 'ok'.")
                time.sleep(0.03)
                continue

        else:
            debug("[Game] No icon found.")

        # Max Speed 4x Optimization
        time.sleep(0.05)

    debug("[End Menu] Handler completed.")