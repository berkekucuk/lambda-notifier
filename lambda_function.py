import json
import os
import requests
import firebase_admin
from firebase_admin import credentials, messaging

# Firebase Admin SDK initialization (performed once globally)
if not firebase_admin._apps:
    try:
        cred_json = json.loads(os.environ['FIREBASE_SERVICE_ACCOUNT'])
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"❌ Firebase Initialization Error: {e}")

def lambda_handler(event, context):
    print(">>> MMA NOTIFICATION ENGINE AWOKE <<<")

    # --- 1. SECURITY CHECK (Webhook Secret) ---
    headers = event.get('headers', {})
    incoming_token = headers.get('x-webhook-secret') or headers.get('X-Webhook-Secret')
    expected_token = os.environ.get('WEBHOOK_SECRET')

    if not expected_token or incoming_token != expected_token:
        print("🚨 SECURITY ALERT: Unauthorized Access Attempt!")
        return {"statusCode": 403, "body": "Unauthorized"}

    # Environment variables
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    HEADERS = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # Process the payload coming from Supabase
        body = json.loads(event.get('body', '{}'))
        new_fight = body.get('record', {})

        fight_id = new_fight.get('fight_id')
        event_id = new_fight.get('event_id')
        current_order = new_fight.get('fight_order')

        if not fight_id:
            return {"statusCode": 200, "body": "No fight_id found in record."}

        # ==========================================================
        # SCENARIO 1: SEND THE RESULT OF THE FINISHED FIGHT
        # ==========================================================
        current_tokens = get_tokens_for_fight(SUPABASE_URL, HEADERS, fight_id)

        if current_tokens:
            winner, loser, winner_img = get_fight_result_details(SUPABASE_URL, HEADERS, fight_id)

            m_type = new_fight.get('method_type', 'Decision')
            m_detail = new_fight.get('method_detail', '')
            method_str = f"{m_type} - {m_detail}" if m_detail else m_type

            title = f"{winner} defeated {loser}" if winner and loser else "Fight Concluded! 🥊"
            message = f"Result: {method_str}"

            send_fcm_notification(
                tokens=current_tokens,
                title=title,
                body=message,
                image_url=winner_img,
                data={"fight_id": fight_id, "type": "RESULT"}
            )

        # ==========================================================
        # SCENARIO 2: THE NEXT FIGHT IS STARTING (With fighter names!)
        # ==========================================================
        if current_order is not None and event_id:
            next_fight_id = get_next_fight_id(SUPABASE_URL, HEADERS, event_id, current_order + 1)

            if next_fight_id:
                next_tokens = get_tokens_for_fight(SUPABASE_URL, HEADERS, next_fight_id)
                if next_tokens:
                    matchup = get_fight_matchup_names(SUPABASE_URL, HEADERS, next_fight_id)

                    send_fcm_notification(
                        tokens=next_tokens,
                        title="Next Fight Starting! 🔥",
                        body=f"{matchup}",
                        image_url=None,
                        data={"fight_id": next_fight_id, "type": "START"}
                    )

        return {"statusCode": 200, "body": "Success"}

    except Exception as e:
        print(f"💥 GLOBAL ERROR: {str(e)}")
        return {"statusCode": 500, "body": "Internal Server Error"}

# --- HELPER FUNCTIONS (Supabase data fetching) ---

def get_tokens_for_fight(url, headers, fight_id):
    # Find the user_ids subscribed to notifications for this fight
    sub_url = f"{url}/rest/v1/user_fight_notifications?select=user_id&fight_id=eq.{fight_id}"
    res = requests.get(sub_url, headers=headers)
    if res.status_code != 200: return []

    u_ids = [i['user_id'] for i in res.json()]
    if not u_ids: return []

    # Fetch FCM tokens for these users
    u_str = ",".join([f"\"{uid}\"" for uid in u_ids]) # Add quotes for UUID formatting
    t_url = f"{url}/rest/v1/user_device_tokens?select=fcm_token&user_id=in.({u_str})"
    t_res = requests.get(t_url, headers=headers)

    return [t['fcm_token'] for t in t_res.json()] if t_res.status_code == 200 else []

def get_fight_result_details(url, headers, fight_id):
    query = f"{url}/rest/v1/participants?select=result,fighters(name,image_url)&fight_id=eq.{fight_id}"
    res = requests.get(query, headers=headers)
    if res.status_code == 200:
        parts = res.json()
        w_name, l_name, w_img = None, None, None
        for p in parts:
            res_val = str(p.get('result', '')).lower()
            if 'win' in res_val or res_val == 'w':
                w_name = p['fighters']['name']
                w_img = p['fighters']['image_url']
            else:
                l_name = p['fighters']['name']
        return w_name, l_name, w_img
    return None, None, None

def get_fight_matchup_names(url, headers, fight_id):
    query = f"{url}/rest/v1/participants?select=fighters(name)&fight_id=eq.{fight_id}"
    res = requests.get(query, headers=headers)
    if res.status_code == 200:
        names = [p['fighters']['name'] for p in res.json()]
        if len(names) >= 2: return f"{names[0]} vs {names[1]}"
    return "Upcoming Match"

def get_next_fight_id(url, headers, event_id, n_order):
    q = f"{url}/rest/v1/fights?select=fight_id&event_id=eq.{event_id}&fight_order=eq.{n_order}&limit=1"
    r = requests.get(q, headers=headers)
    return r.json()[0]['fight_id'] if r.status_code == 200 and r.json() else None

# --- ASIL BİLDİRİM GÖNDERME FONKSİYONU (YENİLENMİŞ) ---

def send_fcm_notification(tokens, title, body, image_url, data):
    try:
        # Message configuration, including high-priority settings
        msg = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
                image=image_url
            ),
            data=data,
            tokens=tokens,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(sound='default')
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(aps=messaging.Aps(content_available=True, sound='default')),
                headers={'apns-priority': '10'}
            )
        )

        # New function for v7+: send_each_for_multicast
        response = messaging.send_each_for_multicast(msg)
        print(f"✅ Sent {response.success_count} notifications. Errors: {response.failure_count}")

    except Exception as e:
        print(f"❌ FCM Sending Error: {e}")