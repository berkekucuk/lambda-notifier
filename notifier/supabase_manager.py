"""Supabase database queries and data fetching."""
from supabase import create_client


class SupabaseManager:
    def __init__(self, url, key):
        self.client = create_client(url, key)

    def get_tokens_for_fight(self, fight_id):
        """Find the tokens subscribed to notifications for this fight using RPC."""
        res = self.client.rpc('get_tokens_by_fight', {'p_fight_id': fight_id}) \
            .range(0, 4999) \
            .execute()
        tokens = {'android': [], 'ios': []}
        if res.data:
            for t in res.data:
                token = t.get('fcm_token')
                platform = str(t.get('platform', '')).lower()
                if not token:
                    continue
                if platform == 'ios':
                    tokens['ios'].append(token)
                else:
                    tokens['android'].append(token)
        return tokens

    def get_fight_result_details(self, fight_id):
        """Get fight result details including winner and loser or draw status."""
        res = self.client.table("participants").select("result,is_red_corner,fighters(name)").eq("fight_id", fight_id).execute()
        parts = res.data
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


    def get_next_fight_id(self, event_id, n_order):
        """Get the fight ID for the next fight in the event."""
        res = self.client.table("fights").select("fight_id").eq("event_id", event_id).eq("fight_order", n_order).limit(1).execute()
        return res.data[0]['fight_id'] if res.data else None


    def get_fight_matchup_names(self, fight_id):
        """Get fighter names for the matchup."""
        res = self.client.table("participants").select("is_red_corner,fighters(name)").eq("fight_id", fight_id).execute()
        participants = res.data
        if participants:
            participants_sorted = sorted(participants, key=lambda p: not bool(p.get('is_red_corner')))
            names = [p['fighters']['name'] for p in participants_sorted if p.get('fighters') and p['fighters'].get('name')]
            if len(names) >= 2:
                return f"{names[0]} vs {names[1]}"
        return "Upcoming Match"


