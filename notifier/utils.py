"""Utility functions for the notifier module."""

def mask_token(token):
    """Return a partially masked token for logging."""
    if not token:
        return "<empty-token>"

    if len(token) <= 10:
        return f"{token[:2]}***{token[-2:]}"

    return f"{token[:6]}***{token[-4:]}"
