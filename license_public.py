"""
License validation for Delta-Neutral Bot.

To purchase a license key, contact: @Chepoop on Telegram
Price: $30 (lifetime)
"""

import time


def validate_key(key: str) -> tuple[bool, str]:
    """
    Validate a license key.

    Returns:
        (is_valid, message)
    """
    if not key or not key.strip():
        return False, "No license key provided"

    key = key.strip().upper()

    # Check format (PREFIX-XXXX-XXXX-XXXX)
    parts = key.split("-")
    if len(parts) != 4:
        return False, "Invalid key format"

    # Validate key (keys are validated offline)
    # Purchase a key from @Chepoop on Telegram
    return False, "Invalid license key"


def get_key_info(key: str) -> dict:
    """Get info about a license key."""
    return {"valid": False}
