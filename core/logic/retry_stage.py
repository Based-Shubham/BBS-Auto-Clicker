import time
from core.state import state, GameState
from core.actions import find_and_click_image, check_image_present
from core.logic.gameplay import handle_gameplay
from core.logic.end_menu import handle_end_menu
from utils.logger import debug, error
from core.capture import prepare_game_execution
from core.stop_controller import stop_controller
from core.esc_listener import start_esc_listener
from utils.settings import settings
from core.logic.collect_tickets import handle_tickets
from core.capture import get_bbs_screenshot
 
def retry_stage():
    stop_controller.reset() 
    
    banner = prepare_game_execution(lambda: stop_controller.stop())
    if not banner:
        return
    
    start_esc_listener(lambda: (
        stop_controller.stop(),
        banner.close()
    ))
    
    if settings["auto_set_boost_to_max"]:
        screenshot = get_bbs_screenshot()
        debug("[Boost] Auto setting boost to max.")
        if (check_image_present("assets/icons/max_boost.png", screenshot=screenshot)):
            debug("[Boost] Boost is already max.")
        else:
            find_and_click_image("assets/icons/boost_1.png", screenshot=screenshot)
            find_and_click_image("assets/icons/boost_2.png", screenshot=screenshot)
            screenshot = get_bbs_screenshot()
            for i in range(9):
                find_and_click_image("assets/icons/boost_increase.png", double_click=True, screenshot=screenshot)
        
    orbs_used = 0
    tickets_used = 0
    quest_completed = False
    
    # NEW: The Auto-Recovery Tracker
    unknown_state_counter = 0 
    recovery_attempts = 0  # caps repeated failed recovery cycles so it can't spin forever

    while should_continue(tickets_used):
        screenshot = get_bbs_screenshot()
        if check_image_present("assets/icons/menu_check.png", screenshot=screenshot):
            unknown_state_counter = 0 # Reset tracker since we know where we are
            recovery_attempts = 0
            debug("[Stage] In menu.")
 
            if not find_and_click_image("assets/icons/start_quest.png", screenshot=screenshot):
                debug("Failed to click 'Start Quest'. Checking for blocking popups...")
                # FOOLPROOF FIX: Try to clear popups (like full inventory) that block the Start button
                if find_and_click_image("assets/icons/ok.png", screenshot=screenshot) or find_and_click_image("assets/icons/close.png", screenshot=screenshot):
                    debug("[Stage] Cleared a blocking popup in the menu.")
                time.sleep(1)
                continue
 
            time.sleep(0.3)
            screenshot = get_bbs_screenshot()
 
            find_and_click_image("assets/icons/ok.png", screenshot=screenshot)
 
            # Poll briefly instead of a single check — a one-shot check right after
            # clicking can catch the purchase screen mid-render, miss it, and wrongly
            # conclude the quest started, which is what causes start_quest.png to get
            # clicked again next loop while the purchase screen is still up.
            purchase_screen = False
            for _ in range(3):
                screenshot = get_bbs_screenshot()
                if check_image_present("assets/icons/purchase.png", screenshot=screenshot):
                    purchase_screen = True
                    break
                time.sleep(0.3)

            if purchase_screen:
                debug("[Stage] Purchase screen detected.")
                if (orbs_used >= settings["max_orbs"] or (orbs_used + 9) >= settings["max_orbs"]) and settings["max_orbs"] != 0:
                    debug("[Tickets] Max orbs reached.")
                    break
                orbs_used = handle_tickets(orbs_used, settings["max_orbs"])
                continue
            else:
                debug("[Stage] Quest started using tickets.")
            
        elif check_image_present("assets/icons/pause.png", screenshot=screenshot):
            unknown_state_counter = 0 # Reset tracker
            recovery_attempts = 0
            debug("[Stage] Detected in-game. Running gameplay handler.")
            handle_gameplay()
            quest_completed = handle_end_menu() 

        elif any(check_image_present(f"assets/icons/{icon}.png", screenshot=screenshot) for icon in ["tap_screen", "cancel", "close", "retry", "tap_here_to_continue"]):
            unknown_state_counter = 0 # Reset tracker
            recovery_attempts = 0
            debug("[Stage] Detected end menu directly (missed pause at high speed). Running end menu handler.")
            quest_completed = handle_end_menu()
            
        else:
            # FOOLPROOF FIX: The Watchdog
            unknown_state_counter += 1
            if unknown_state_counter >= 15: # If stuck looking at an unknown screen for ~4.5 seconds
                debug("[Stage] Screen state unknown. Attempting auto-recovery...")
                
                # Blindly attempt to clear network errors or rogue daily popups
                recovered = False
                for icon in ["network_error_retry", "retry", "ok", "close", "cancel"]:
                    if find_and_click_image(f"assets/icons/{icon}.png", screenshot=screenshot):
                        debug(f"[Stage] Auto-recovery: Clicked {icon}.png to clear screen.")
                        recovered = True
                        break

                unknown_state_counter = 0 # Reset the tracker to give it time to load

                # If nothing was clickable, this was a wasted recovery cycle — count it.
                # Without this cap, a genuinely stuck screen loops here forever, silently,
                # without clicking anything — which is the exact symptom being fixed.
                if recovered:
                    recovery_attempts = 0
                else:
                    recovery_attempts += 1
                    if recovery_attempts >= 5:
                        error("[Stage] Auto-recovery failed 5 times in a row. Stopping instead of looping forever.")
                        break
            
        if quest_completed:
            tickets_used += 10 if settings["auto_set_boost_to_max"] else 1
        
        quest_completed = False
        debug(f"[Tracker] Tickets used: {tickets_used} | Orbs used: {orbs_used}")
        time.sleep(0.3)
   
    stop_controller.stop()
    banner.close()
    return orbs_used, tickets_used
 
def should_continue(tickets_used: int) -> bool:
    if stop_controller.should_stop():
        return False
 
    max_tickets = settings["max_tickets"]
    boost_amount = 9 if settings["auto_set_boost_to_max"] else 0
 
    if max_tickets == -1:
        return True
 
    return (
        tickets_used < max_tickets and
        (tickets_used + boost_amount) < max_tickets
    )
