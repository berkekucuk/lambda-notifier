"""Event handlers for fight notifications."""
from .supabase_client import (
    get_tokens_for_fight,
    get_fight_result_details,
    get_fight_matchup_names,
    get_next_fight_id,
)
from .notifications import send_fcm_notification


def handle_fight_result(supabase_url, headers, fight_data):
    """
    Scenario 1: Send notification for the result of the finished fight.
    """
    fight_id = fight_data.get('fight_id')
    current_tokens = get_tokens_for_fight(supabase_url, headers, fight_id)

    if current_tokens:
        winner, loser = get_fight_result_details(supabase_url, headers, fight_id)

        m_type = fight_data.get('method_type', 'Decision')
        m_detail = fight_data.get('method_detail', '')
        method_str = f"{m_type} - {m_detail}" if m_detail else m_type

        title = f"{winner} defeated {loser}" if winner and loser else "Fight Concluded! 🥊"
        message = f"by {method_str}"

        send_fcm_notification(
            tokens=current_tokens,
            title=title,
            body=message,
            image_url=None,
            data={"fight_id": fight_id, "type": "RESULT"}
        )


def handle_next_fight_starting(supabase_url, headers, fight_data):
    """
    Scenario 2: Send notification when the next fight is starting with fighter names.
    """
    event_id = fight_data.get('event_id')
    current_order = fight_data.get('fight_order')

    if current_order is not None and event_id:
        next_fight_id = get_next_fight_id(supabase_url, headers, event_id, current_order + 1)

        if next_fight_id:
            next_tokens = get_tokens_for_fight(supabase_url, headers, next_fight_id)
            if next_tokens:
                matchup = get_fight_matchup_names(supabase_url, headers, next_fight_id)

                send_fcm_notification(
                    tokens=next_tokens,
                    title="Next Fight Starting! 🔥",
                    body=f"{matchup}",
                    image_url=None,
                    data={"fight_id": next_fight_id, "type": "START"}
                )
