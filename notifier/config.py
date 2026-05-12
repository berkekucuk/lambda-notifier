"""Firebase Admin SDK initialization and configuration."""
import json
import os
import firebase_admin
from firebase_admin import credentials


def initialize_firebase():
    """Initialize Firebase Admin SDK using the professional method."""
    try:
        firebase_admin.get_app()

    except ValueError:
        try:
            raw_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT', '').strip()

            if not raw_json:
                print("❌ ERROR: FIREBASE_SERVICE_ACCOUNT environment variable is empty!")
                return

            cred_json = json.loads(raw_json)

            print(f"DEBUG: Lambda Project ID: {cred_json.get('project_id')}")
            private_key = cred_json.get('private_key', '')
            print(f"DEBUG: Private Key Prefix: {private_key[:30]}...")

            cred = credentials.Certificate(cred_json)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK successfully initialized.")

        except json.JSONDecodeError as je:
            print(f"❌ JSON Format Error: Environment variable is not a valid JSON! {je}")
        except Exception as e:
            print(f"❌ Unexpected error during Firebase initialization: {e}")


def get_supabase_config():
    """Get Supabase configuration from environment variables."""
    return {
        "url": os.environ.get('SUPABASE_URL'),
        "service_key": os.environ.get('SUPABASE_SERVICE_ROLE_KEY'),
    }


def get_webhook_secret():
    """Get the webhook security token from environment variables."""
    return os.environ.get('WEBHOOK_SECRET')


def verify_webhook_secret(headers, expected_token):
    """Verify webhook authenticity using secret token."""
    incoming_token = headers.get('x-webhook-secret') or headers.get('X-Webhook-Secret')

    if not expected_token or incoming_token != expected_token:
        print("Unauthorized Access!")
        return False

    return True