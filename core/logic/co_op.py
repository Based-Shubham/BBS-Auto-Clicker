import time
from core.state import state, GameState
from core.actions import find_and_click_image, check_image_present, check_network_error
from core.logic.gameplay import handle_gameplay
from core.logic.end_menu import handle_end_menu
from utils.logger import debug, error
from core.capture import prepare_game_execution
from core.stop_controller import stop_controller
from core.esc_listener import start_esc_listener
from utils.settings import settings
from core.logic.collect_tickets import handle_tickets
from core.capture import get_bbs_screenshot

def coop_stage():
    stop_controller.reset() 
    
    banner = prepare_game_execution(lambda: stop_controller.stop())
    if not banner:
        return
    
    start_esc_listener(lambda: (
        stop_controller.stop(),
        banner.close()
    ))
    
        
    orbs_used = 0
    tickets_used = 0
    quest_completed = False
    coop_start_tries = 0
    while should_continue(tickets_used):
        screenshot = get_bbs_screenshot()
        if check_network_error(screenshot=screenshot):
            continue
        if check_image_present("assets/icons/create_room.png", screenshot=screenshot):
            debug("[Stage] In menu creating room.")

            find_and_click_image("assets/icons/create_room.png", screenshot=screenshot)
            time.sleep(0.3)  # was 1 — tightened, local menu transition
        
        elif check_image_present("assets/icons/no_boost_coop_check.png", screenshot=screenshot):
            debug("[Stage] No boost coop check.")
            if settings["auto_set_boost_to_max"]:
                find_and_click_image("assets/icons/no_boost_coop_check.png", threshold=0.9, screenshot=screenshot)

            
        elif check_image_present("assets/icons/public.png", screenshot=screenshot):
            debug("[Stage] In menu setting room to public.")
            find_and_click_image("assets/icons/public.png", screenshot=screenshot)
            screenshot = get_bbs_screenshot()
            if (find_and_click_image("assets/icons/confirm.png", screenshot=screenshot)):
                in_menu = True
                while in_menu:
                    screenshot = get_bbs_screenshot()
                    if (not check_image_present("assets/icons/locked_coop.png", screenshot=screenshot) and not(check_image_present("assets/icons/looking_for_members.png", screenshot=screenshot))):
                        if (find_and_click_image("assets/icons/start_quest.png", screenshot=screenshot)):
                            time.sleep(0.3)  # was 0.5 — tightened
                            screenshot = get_bbs_screenshot()
                            if check_image_present("assets/icons/members_not_ready.png", screenshot=screenshot):
                                coop_start_tries += 1
                                if coop_start_tries > 3:
                                    error("[Stage] Failed to start coop.")
                                    find_and_click_image("assets/icons/ok.png", screenshot=screenshot)
                                    in_menu = False
                                    time.sleep(3)  # was 10 — still a real cooldown, not tightened as far as local transitions
                                else:
                                    find_and_click_image("assets/icons/cancel.png", screenshot=screenshot)
                            elif check_image_present("assets/icons/no_soul_tickets_co_op.png", screenshot=screenshot):
                                if (orbs_used >= settings["max_orbs"] or (orbs_used + 9) >= settings["max_orbs"]) and settings["max_orbs"] != 0:
                                    debug("[Tickets] Max orbs reached.")
                                    break
                                orbs_used = handle_tickets(orbs_used, settings["max_orbs"], True)
                            else:
                                in_menu = False
                                time.sleep(3)  # was 10 — quest-load wait, kept conservative
                    # no else here — if still locked_coop/looking_for_members, keep waiting

        # After the first quest the game keeps the room public automatically —
        # public.png never reappears, only confirm.png shows up on its own.
        # Without this branch nothing in the elif chain matches that screen
        # and the loop does nothing.
        elif check_image_present("assets/icons/confirm.png", screenshot=screenshot):
            debug("[Stage] Confirm screen without public.png — room already public, confirming directly.")
            if (find_and_click_image("assets/icons/confirm.png", screenshot=screenshot)):
                in_menu = True
                while in_menu:
                    screenshot = get_bbs_screenshot()
                    if (not check_image_present("assets/icons/locked_coop.png", screenshot=screenshot) and not(check_image_present("assets/icons/looking_for_members.png", screenshot=screenshot))):
                        if (find_and_click_image("assets/icons/start_quest.png", screenshot=screenshot)):
                            time.sleep(0.3)
                            screenshot = get_bbs_screenshot()
                            if check_image_present("assets/icons/members_not_ready.png", screenshot=screenshot):
                                coop_start_tries += 1
                                if coop_start_tries > 3:
                                    error("[Stage] Failed to start coop.")
                                    find_and_click_image("assets/icons/ok.png", screenshot=screenshot)
                                    in_menu = False
                                    time.sleep(3)
                                else:
                                    find_and_click_image("assets/icons/cancel.png", screenshot=screenshot)
                            elif check_image_present("assets/icons/no_soul_tickets_co_op.png", screenshot=screenshot):
                                if (orbs_used >= settings["max_orbs"] or (orbs_used + 9) >= settings["max_orbs"]) and settings["max_orbs"] != 0:
                                    debug("[Tickets] Max orbs reached.")
                                    break
                                orbs_used = handle_tickets(orbs_used, settings["max_orbs"], True)
                            else:
                                in_menu = False
                                time.sleep(3)
                    # no else here — if still locked_coop/looking_for_members, keep waiting

        elif check_image_present("assets/icons/start_quest_failed.png", screenshot=screenshot):
            debug("[Stage] Start quest failed.")
            find_and_click_image("assets/icons/start_quest_failed.png", screenshot=screenshot)  
                
        elif check_image_present("assets/icons/quit_icon.png", screenshot=screenshot):
            debug("[Stage] Detected in-game. Running gameplay handler.")
            handle_gameplay()
            quest_completed = handle_end_menu() 
            coop_start_tries = 0
            

        if quest_completed:
            tickets_used += 5 if settings["auto_set_boost_to_max"] else 1
        
        quest_completed = False
        debug(f"[Tracker] Tickets used: {tickets_used} | Orbs used: {orbs_used}")
        time.sleep(0.3)  # was 2 — tightened outer poll interval
   
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