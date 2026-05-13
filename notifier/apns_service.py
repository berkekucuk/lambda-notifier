"""Apple Push Notification service (APNs) handling."""
import os
import time
import httpx
import jwt
from .utils import mask_token

def get_apns_jwt(private_key, key_id, team_id):
    """Generate a JWT token for APNs authentication."""
    # Ensure newlines are correctly formatted if they come from a single-line env var
    private_key = private_key.replace('\\n', '\n')

    headers = {
        'alg': 'ES256',
        'kid': key_id
    }
    
    payload = {
        'iss': team_id,
        'iat': int(time.time())
    }
    
    try:
        token = jwt.encode(payload, private_key, algorithm='ES256', headers=headers)
        return token
    except Exception as e:
        print(f"⚠️ Failed to generate JWT token: {e}")
        return None

def build_apns_payload(title, body, data):
    """Construct the JSON payload for APNs."""
    apns_payload = {
        "aps": {
            "alert": {
                "title": title,
                "body": body
            },
            "sound": "default"
        }
    }
    
    if data:
        apns_payload.update(data)
        
    return apns_payload

def get_apns_headers(topic, jwt_token):
    """Construct the HTTP headers for APNs request."""
    return {
        "apns-topic": topic,
        "apns-push-type": "alert",
        "authorization": f"bearer {jwt_token}"
    }

def get_apns_base_url():
    """Determine the APNs base URL based on environment."""
    use_sandbox = os.getenv("APNS_USE_SANDBOX", "false").lower() == "true"
    return "https://api.sandbox.push.apple.com" if use_sandbox else "https://api.push.apple.com"

def send_apns_notification(tokens, title, body, data):
    """Send APNs notification to multiple iOS devices using HTTP/2."""
    if not tokens:
        print("ℹ️ No APN tokens to send.")
        return

    # Load credentials
    private_key = os.getenv("APNS_PRIVATE_KEY")
    key_id = os.getenv("APNS_KEY_ID")
    team_id = os.getenv("APNS_TEAM_ID")
    topic = os.getenv("APNS_TOPIC")

    if not all([private_key, key_id, team_id, topic]):
        print("⚠️ APNs credentials missing in environment variables. Skipping APN delivery.")
        return

    # Generate JWT
    jwt_token = get_apns_jwt(private_key, key_id, team_id)
    if not jwt_token:
        return

    # Build Request parameters
    apns_payload = build_apns_payload(title, body, data)
    headers = get_apns_headers(topic, jwt_token)
    base_url = get_apns_base_url()

    total_sent = 0
    total_failed = 0

    try:
        # Deliver via HTTP/2
        with httpx.Client(http2=True) as client:
            for token in tokens:
                url = f"{base_url}/3/device/{token}"
                try:
                    response = client.post(url, headers=headers, json=apns_payload)
                    if response.status_code == 200:
                        total_sent += 1
                    else:
                        total_failed += 1
                        masked = mask_token(token)
                        print(f"   ⚠️ APN Token: {masked} failed | Status: {response.status_code} | Reason: {response.text}")
                except Exception as e:
                    total_failed += 1
                    masked = mask_token(token)
                    print(f"   ⚠️ APN Token: {masked} exception | Reason: {e}")

        print(f"🏁 Total Successful APN Deliveries: {total_sent} / {len(tokens)}")
        if total_failed > 0:
            print(f"   ❌ Failed APN Deliveries: {total_failed}")

    except Exception as e:
        print(f"❌ Critical error in APN delivery: {e}")
