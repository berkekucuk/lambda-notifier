"""Event handlers for fight notifications."""
import time
from .firebase_service import send_fcm_notification
from .apns_service import send_apns_notification


def handle_fight_result(db_manager, fight_data):
    """
    Scenario 1: Send notification for the result of the finished fight.
    """
    fight_id = fight_data.get('fight_id')
    current_tokens = db_manager.get_tokens_for_fight(fight_id)

    if current_tokens.get('android') or current_tokens.get('ios'):
        f1_name, f2_name, result = db_manager.get_fight_result_details(fight_id)

        # RETRY LOGIC: If result_type is not found, it might be due to a race condition with the scraper.
        # We wait for 2 seconds and try one more time.
        if not result:
            print(f"⚠️ Result data not ready for fight {fight_id}. Retrying in 2 seconds...")
            time.sleep(2)
            f1_name, f2_name, result = db_manager.get_fight_result_details(fight_id)

        method_type = fight_data.get('method_type', '')
        method_detail = fight_data.get('method_detail', '')
        method_str = f"{method_type} - {method_detail}" if method_detail else method_type

        # Customize title/body based on result type
        if result == "DRAW":
            title = f"Draw: {f1_name} vs {f2_name}"
            message = f"Result: {method_str}"
        elif result == "NC":
            title = f"No Contest: {f1_name} vs {f2_name}"
            message = f"Result: {method_str}"
        elif result == "WIN":
            title = f"{f1_name} defeated {f2_name}"
            message = f"by {method_str}"
        else:
            title = "Fight Concluded!"
            message = f"Method: {method_str}"

        if current_tokens.get('android'):
            send_fcm_notification(
                tokens=current_tokens['android'],
                title=title,
                body=message,
                image_url=None,
                data={"fight_id": fight_id, "type": "RESULT"}
            )
            
        if current_tokens.get('ios'):
            send_apns_notification(
                tokens=current_tokens['ios'],
                title=title,
                body=message,
                data={"fight_id": fight_id, "type": "RESULT"}
            )


def handle_next_fight_starting(db_manager, fight_data):
    """
    Scenario 2: Send notification when the next fight is starting with fighter names.
    """
    event_id = fight_data.get('event_id')
    current_order = fight_data.get('fight_order')

    if current_order is not None and event_id:
        next_fight_id = db_manager.get_next_fight_id(event_id, current_order + 1)

        if next_fight_id:
            next_tokens = db_manager.get_tokens_for_fight(next_fight_id)
            if next_tokens.get('android') or next_tokens.get('ios'):
                matchup = db_manager.get_fight_matchup_names(next_fight_id)

                if next_tokens.get('android'):
                    send_fcm_notification(
                        tokens=next_tokens['android'],
                        title="Next Fight Starting! 🔥",
                        body=f"{matchup}",
                        image_url=None,
                        data={"fight_id": next_fight_id, "type": "START"}
                    )
                    
                if next_tokens.get('ios'):
                    send_apns_notification(
                        tokens=next_tokens['ios'],
                        title="Next Fight Starting! 🔥",
                        body=f"{matchup}",
                        data={"fight_id": next_fight_id, "type": "START"}
                    )
