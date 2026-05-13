"""Firebase Cloud Messaging (FCM) notification handling."""
from firebase_admin import messaging
from .utils import mask_token


def send_fcm_notification(tokens, title, body, image_url, data):
    """Send FCM notification to multiple devices with high priority settings."""
    if not tokens:
        print("ℹ️ No FCM tokens to send.")
        return

    chunk_size = 500
    total_sent = 0
    total_failed = 0

    for i in range(0, len(tokens), chunk_size):
        chunk = tokens[i:i + chunk_size]

        msg = messaging.MulticastMessage(
            tokens=chunk,
            data=data,
            notification=messaging.Notification(
                title=title,
                body=body,
                image=image_url
            ),
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(sound='default')
            )
        )

        try:
            response = messaging.send_each_for_multicast(msg)
            total_sent += response.success_count
            total_failed += response.failure_count
            print(f"📦 FCM Chunk {i//chunk_size + 1}: {response.success_count} successful, {response.failure_count} failed.")

            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        failed_token = chunk[idx]
                        masked = mask_token(failed_token)
                        err = resp.exception
                        err_code = getattr(err, 'code', 'UNKNOWN_CODE')
                        err_msg = getattr(err, 'message', str(err))
                        print(f"   ⚠️ FCM Token: {masked} failed | Error Code: {err_code} | Reason: {err_msg}")

        except Exception as e:
            err_code = getattr(e, 'code', 'UNKNOWN_CODE')
            print(f"❌ Critical error in FCM chunk delivery: {e} | Error Code: {err_code}")

    print(f"🏁 Total Successful FCM Deliveries: {total_sent} / {len(tokens)}")
    if total_failed > 0:
        print(f"   ❌ Failed FCM Deliveries: {total_failed}")


