import time
import cv2
import numpy as np
from core.actions import find_and_click_image, check_image_present, _ensure_matchable, check_network_error
from utils.logger import debug, error
from core.capture import prepare_game_execution
from core.stop_controller import stop_controller
from core.esc_listener import start_esc_listener
from utils.settings import settings
from core.logic.collect_tickets import handle_tickets
from core.capture import get_bbs_screenshot
from core.logic.handle_gameplay_single_player import handle_gameplay_single_player
from core.logic.end_menu_singleplayer import handle_end_menu_singleplayer
from utils.resource_manager import get_asset_path
from PySide6.QtWidgets import QApplication

CATEGORY_TILES = [
    "human_world.png",
    "soul_society.png",
    "hueco_mundo.png",
    "side_stories.png",
    "others.png"
]

SUB_STORY_BANNERS = [
    "banner_human_world.png",
    "banner_soul_society.png",
    "banner_hueco_mundo.png",
    "banner_side_stories.png",
    "banner_others.png"
]

def _safe_screenshot(retries=3, delay=0.05):
    """Safely capture a screenshot with ultra-fast retries for 4x speed."""
    for attempt in range(retries):
        try:
            QApplication.processEvents()
        except Exception:
            pass
        screenshot = get_bbs_screenshot()
        if screenshot is not None:
            return screenshot
        debug(f"[Sub Stories] Screenshot was None (attempt {attempt + 1}/{retries}), retrying...")
        time.sleep(delay)
    return None

def _find_new_category_tile(screenshot, ignored_categories=None):
    """Return the tile asset name that currently has a NEW ribbon on it, checking all badge matches on screen."""
    if ignored_categories is None:
        ignored_categories = set()

    badge_path = get_asset_path("sub_new.png")
    badge = cv2.imread(badge_path, cv2.IMREAD_COLOR)
    screenshot = _ensure_matchable(screenshot)
    if badge is None:
        debug(f"[Sub Stories] Could not load sub_new.png at: {badge_path}")
        return None
    badge = _ensure_matchable(badge)
    bh, bw = badge.shape[:2]
    screen_res = cv2.matchTemplate(screenshot, badge, cv2.TM_CCOEFF_NORMED)
    
    locations = np.where(screen_res >= 0.78)
    badge_locs = list(zip(*locations[::-1]))
    if not badge_locs:
        debug("[Sub Stories] No sub_new.png badges detected on screen.")
        return None

    margin = 45  # 45px margin guarantees ribbons overhanging card corners are never missed

    for tile_name in CATEGORY_TILES:
        if tile_name in ignored_categories:
            continue

        tile_path = get_asset_path(tile_name)
        tile = cv2.imread(tile_path, cv2.IMREAD_COLOR)
        if tile is None:
            continue
        tile = _ensure_matchable(tile)
        tile_res = cv2.matchTemplate(screenshot, tile, cv2.TM_CCOEFF_NORMED)
        _, tile_val, _, tile_loc = cv2.minMaxLoc(tile_res)
        
        # 0.70 threshold ensures card glow/lighting animations don't skip Human World
        if tile_val < 0.70:
            debug(f"[Sub Stories] {tile_name} match score too low ({tile_val:.2f} < 0.70)")
            continue

        tw, th = tile.shape[1], tile.shape[0]
        for bloc in badge_locs:
            badge_center = (bloc[0] + bw // 2, bloc[1] + bh // 2)
            in_bounds = (
                tile_loc[0] - margin <= badge_center[0] <= tile_loc[0] + tw + margin and
                tile_loc[1] - margin <= badge_center[1] <= tile_loc[1] + th + margin
            )
            if in_bounds:
                debug(f"[Sub Stories] {tile_name} matched (score={tile_val:.2f}) and contains NEW badge center")
                return tile_name

    debug("[Sub Stories] NEW badges found, but none fell inside an un-ignored category card boundary.")
    return None

def sub_stories():
    stop_controller.reset() 
    
    banner = prepare_game_execution(lambda: stop_controller.stop())
    if not banner:
        return "Game window not found. Please make sure the game is open and properly positioned."
    
    start_esc_listener(lambda: (
        stop_controller.stop(),
        banner.close()
    ))
    
    time.sleep(0.15)
    screenshot = _safe_screenshot()
    if screenshot is None:
        debug("[Sub Stories] Could not capture a valid screenshot (window minimized/hidden?)")
        stop_controller.stop()
        banner.close()
        return "Could not capture game window. Please make sure it's open and not minimized."

    if check_image_present("assets/icons/sub_stories_title.png", screenshot=screenshot):
        debug("[Sub Stories] On main menu - looking for NEW icon")

        if not check_image_present("assets/icons/new.png", screenshot=screenshot):
            debug("[Sub Stories] No NEW sub stories found")
            stop_controller.stop()
            banner.close()
            return "No NEW sub stories found to complete"

        debug("[Sub Stories] Found NEW icon, clicking on sub story")

        entered = False
        for attempt in range(5):
            if not find_and_click_image("assets/icons/sub_stories_title.png"):
                debug(f"[Sub Stories] Click attempt {attempt + 1} - button not found")
                break

            found_this_attempt = False
            poll_deadline = time.time() + 2.0
            while time.time() < poll_deadline:
                time.sleep(0.08)
                screenshot = get_bbs_screenshot()
                if check_image_present("assets/icons/back.png", screenshot=screenshot):
                    debug(f"[Sub Stories] Entered category grid (confirmed on attempt {attempt + 1})")
                    entered = True
                    found_this_attempt = True
                    break

            if found_this_attempt:
                break
            debug(f"[Sub Stories] Still on main menu after attempt {attempt + 1}, retrying click")

        if not entered:
            debug("[Sub Stories] Could not enter category grid after 5 attempts")
            stop_controller.stop()
            banner.close()
            return "Found NEW sub story but could not enter category grid after multiple attempts"
    else:
        debug("[Sub Stories] Not on main sub stories menu")
        stop_controller.stop()
        banner.close()
        return "Not on main sub stories menu"

    ignored_categories = set()

    while not stop_controller.should_stop():
        screenshot = _safe_screenshot()
        if screenshot is None:
            debug("[Sub Stories] Could not capture a valid screenshot, skipping this cycle")
            time.sleep(0.05)
            continue

        if check_network_error(screenshot=screenshot):
            continue

        tile_name = _find_new_category_tile(screenshot, ignored_categories=ignored_categories)

        if tile_name:
            debug(f"[Sub Stories] Found NEW category ({tile_name}), clicking it")

            if find_and_click_image(f"assets/icons/{tile_name}"):
                
                time.sleep(1.5)

                debug("[Sub Stories] Entered category, checking all pages")

                page = 1
                max_pages = 5
                found_any_story_in_category = False

                while page <= max_pages and not stop_controller.should_stop():
                    screenshot = get_bbs_screenshot()

                    if _is_real_close_button_present(screenshot, threshold=0.70):
                        debug("[Sub Stories] Chapter list modal detected — switching to gatekeeper!")
                        handle_sub_story_quest()
                        found_any_story_in_category = True
                        continue

                    debug(f"[Sub Stories] Checking page {page}")
                    
                    if check_image_present("assets/icons/sub_new.png", screenshot=screenshot, threshold=0.88):
                        debug(f"[Sub Stories] Found NEW story on page {page}")

                        if find_and_click_image("assets/icons/sub_new.png", threshold=0.88):
                            found_any_story_in_category = True
                            time.sleep(0.05) 
                            handle_sub_story_quest()
                            time.sleep(0.05) 
                            continue
                        else:
                            debug("[Sub Stories] Could not click on NEW story")
                            stop_controller.stop()
                            banner.close()
                            return "Found NEW story but could not click on it"
                    else:
                        debug(f"[Sub Stories] No NEW stories on page {page}")

                        if page < max_pages:
                            if find_and_click_image(f"assets/icons/sub_{page + 1}.png", threshold=0.65):
                                page += 1
                                time.sleep(0.15)
                                debug(f"[Sub Stories] Moved to page {page}")
                            else:
                                debug("[Sub Stories] No more pages in this category")
                                break
                        else:
                            debug("[Sub Stories] Reached max pages limit")
                            break

                    if stop_controller.should_stop():
                        break

                if not found_any_story_in_category:
                    debug(f"[Sub Stories] No valid stories found in {tile_name}. Adding to ignore list.")
                    ignored_categories.add(tile_name)

                screenshot = get_bbs_screenshot()
                find_and_click_image("assets/icons/back.png", screenshot=screenshot)
                time.sleep(0.08)
                screenshot = get_bbs_screenshot()
                find_and_click_image("assets/icons/back.png", screenshot=screenshot)
                time.sleep(0.10)
                debug("[Sub Stories] Back to category grid, rechecking for more NEW categories")
            else:
                debug("[Sub Stories] Could not click on NEW category")
                stop_controller.stop()
                banner.close()
                return "Found NEW category but could not click on it"
        else:
            debug("[Sub Stories] No more NEW categories found (or all remaining are ignored)")
            break

        if stop_controller.should_stop():
            break

        time.sleep(0.05)
   
    stop_controller.stop()
    banner.close()
    return True

def _is_real_close_button_present(screenshot, threshold=0.72):
    close_path = get_asset_path("close.png")
    close_img = cv2.imread(close_path, cv2.IMREAD_COLOR)
    if close_img is None or screenshot is None:
        return False
    close_img = _ensure_matchable(close_img)
    screenshot_m = _ensure_matchable(screenshot)
    res = cv2.matchTemplate(screenshot_m, close_img, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    
    sh, sw = screenshot_m.shape[:2]
    is_at_lower_half = max_loc[1] > (sh * 0.65) 
    is_centered = (sw * 0.30) < max_loc[0] < (sw * 0.70)
    
    return max_val >= threshold and is_at_lower_half and is_centered

def _is_valid_modal_new_badge_present(screenshot, threshold=0.78):
    new_path = get_asset_path("sub_new.png")
    new_img = cv2.imread(new_path, cv2.IMREAD_COLOR)
    if new_img is None or screenshot is None:
        return False
    new_img = _ensure_matchable(new_img)
    screenshot_m = _ensure_matchable(screenshot)
    res = cv2.matchTemplate(screenshot_m, new_img, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    
    sh = screenshot_m.shape[0]
    is_inside_modal_area = max_loc[1] < (sh * 0.70)
    
    return max_val >= threshold and is_inside_modal_area

def handle_sub_story_quest():
    debug("[Sub Story Quest] Entering state-based quest handler...")
    
    poll_end = time.time() + 1.2
    while time.time() < poll_end:
        if _is_real_close_button_present(get_bbs_screenshot(), threshold=0.70):
            break
        time.sleep(0.05)
    
    played_any_quest = False
    
    while not stop_controller.should_stop():
        screenshot = get_bbs_screenshot()

        if check_network_error(screenshot=screenshot):
            continue

        # --- STATE 1: VICTORY SCREEN DIRECT CLICK ---
        direct_tap_triggers = [
            ("sub_story_end", 0.70),
            ("new_record", 0.70), 
            ("tap_screen", 0.60)
        ]
        
        victory_screen_detected = False
        for trigger, thresh in direct_tap_triggers:
            if check_image_present(f"assets/icons/{trigger}.png", screenshot=screenshot, threshold=thresh):
                debug(f"[Sub Story Quest] Victory screen detected via {trigger}! Tapping screen...")
                find_and_click_image(f"assets/icons/{trigger}.png", screenshot=screenshot, threshold=thresh)
                played_any_quest = True
                victory_screen_detected = True
                time.sleep(0.15)
                break 

        if victory_screen_detected:
            handle_end_menu_singleplayer()
            continue

        # --- STRICT POPUP DETECTION ---
        # Increased standard buttons to 0.85 to prevent falsely detecting blue UI elements as 'Retry'
        end_menu_triggers = [
            ("cancel", 0.85),
            ("retry", 0.85),
            ("ok", 0.85),
            ("tap_here_to_continue", 0.70) # Kept at 0.70 due to background transparency
        ]
        
        popup_detected = False
        for icon, thresh in end_menu_triggers:
            if check_image_present(f"assets/icons/{icon}.png", screenshot=screenshot, threshold=thresh):
                debug(f"[Sub Story Quest] Detected end-menu popup via {icon}. Running cleanup...")
                handle_end_menu_singleplayer()
                played_any_quest = True
                popup_detected = True
                time.sleep(0.15)
                break
                
        if popup_detected:
            continue

        # --- STATE 2: CHAPTER LIST / PREPARATION ---
        if check_image_present("assets/icons/sub_empty_stars.png", screenshot=screenshot, threshold=0.94):
            debug("[Sub Story Quest] Found uncompleted chapter (empty stars) — selecting it!")
            if find_and_click_image("assets/icons/sub_empty_stars.png", screenshot=screenshot, threshold=0.94):
                played_any_quest = True
                time.sleep(0.20)
            continue

        elif check_image_present("assets/icons/prepare_for_quest.png", screenshot=screenshot):
            debug("[Sub Story Quest] Clicking Prepare for Quest")
            find_and_click_image("assets/icons/prepare_for_quest.png", screenshot=screenshot)
            time.sleep(0.20)
            continue

        elif check_image_present("assets/icons/start_quest.png", screenshot=screenshot):
            debug("[Sub Story Quest] Clicking Start Quest")
            find_and_click_image("assets/icons/start_quest.png", screenshot=screenshot)
            time.sleep(0.20)
            continue

        # --- STATE 3: GATEKEEPER CLOSE RULE ---
        elif _is_real_close_button_present(screenshot, threshold=0.72):
            time.sleep(0.10)
            screenshot = get_bbs_screenshot()
            
            if check_image_present("assets/icons/sub_empty_stars.png", screenshot=screenshot, threshold=0.94):
                debug("[Sub Story Quest] Close detected, but empty stars remain — prioritizing quest!")
                continue
                
            debug("[Sub Story Quest] Close detected and NO uncompleted chapters remain — safe to close!")
            if find_and_click_image("assets/icons/close.png", screenshot=screenshot, threshold=0.72):
                time.sleep(0.20)
                return played_any_quest

        time.sleep(0.05)

    return False