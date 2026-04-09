"""Firebase Cloud Messaging (FCM) notification handling."""
from firebase_admin import messaging


def mask_token(token):
    """Return a partially masked token for logging."""
    if not token:
        return "<empty-token>"

    if len(token) <= 10:
        return f"{token[:2]}***{token[-2:]}"

    return f"{token[:6]}***{token[-4:]}"


def send_fcm_notification(tokens, title, body, image_url, data):
    """Send FCM notification to multiple devices with high priority settings."""
    try:
        if not tokens:
            print("ℹ️ No tokens to send.")
            return

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

        if response.failure_count:
            for index, result in enumerate(response.responses):
                if result.success:
                    continue

                token = tokens[index] if index < len(tokens) else "<unknown-token>"
                error = result.exception
                print(
                    f"❌ FCM token failed: token={mask_token(token)}, "
                    f"code={getattr(error, 'code', 'unknown')}, "
                    f"message={error}"
                )

    except Exception as e:
        print(f"❌ FCM Sending Error: {e}")
