"""Supabase database queries and data fetching."""
import requests


def get_tokens_for_fight(url, headers, fight_id):
    """Find the user_ids subscribed to notifications for this fight."""
    sub_url = f"{url}/rest/v1/user_fight_notifications?select=user_id&fight_id=eq.{fight_id}"
    res = requests.get(sub_url, headers=headers)
    if res.status_code != 200:
        return []

    u_ids = [i['user_id'] for i in res.json()]
    if not u_ids:
        return []

    # Fetch FCM tokens for these users
    u_str = ",".join([f"\"{uid}\"" for uid in u_ids])  # Add quotes for UUID formatting
    t_url = f"{url}/rest/v1/user_device_tokens?select=fcm_token&user_id=in.({u_str})"
    t_res = requests.get(t_url, headers=headers)

    return [t['fcm_token'] for t in t_res.json()] if t_res.status_code == 200 else []


def get_fight_result_details(url, headers, fight_id):
    """Get fight result details including winner and loser or draw status."""
    query = f"{url}/rest/v1/participants?select=result,is_red_corner,fighters(name)&fight_id=eq.{fight_id}"
    res = requests.get(query, headers=headers)
    if res.status_code == 200:
        parts = res.json()
        if not parts:
            return None, None, None

        winner = None
        red_name = "Unknown"
        blue_name = "Unknown"
        is_draw = False
        is_nc = False

        for p in parts:
            name = p.get('fighters', {}).get('name', 'Unknown')
            if p.get('is_red_corner'):
                red_name = name
            else:
                blue_name = name
                
            res_val = str(p.get('result', '')).lower()
            
            if res_val == 'win' or res_val == 'w':
                winner = name
            elif 'draw' in res_val:
                is_draw = True
            elif 'no_contest' in res_val or 'nc' in res_val:
                is_nc = True

        if is_draw:
            return red_name, blue_name, "DRAW"
        
        if is_nc:
            return red_name, blue_name, "NC"

        if winner:
            loser = blue_name if winner == red_name else red_name
            return winner, loser, "WIN"

    return None, None, None


def get_fight_matchup_names(url, headers, fight_id):
    """Get fighter names for the matchup."""
    query = f"{url}/rest/v1/participants?select=is_red_corner,fighters(name)&fight_id=eq.{fight_id}"
    res = requests.get(query, headers=headers)
    if res.status_code == 200:
        participants = res.json()
        participants_sorted = sorted(participants, key=lambda p: not bool(p.get('is_red_corner')))
        names = [p['fighters']['name'] for p in participants_sorted if p.get('fighters') and p['fighters'].get('name')]
        if len(names) >= 2:
            return f"{names[0]} vs {names[1]}"
    return "Upcoming Match"


def get_next_fight_id(url, headers, event_id, n_order):
    """Get the fight ID for the next fight in the event."""
    q = f"{url}/rest/v1/fights?select=fight_id&event_id=eq.{event_id}&fight_order=eq.{n_order}&limit=1"
    r = requests.get(q, headers=headers)
    return r.json()[0]['fight_id'] if r.status_code == 200 and r.json() else None
