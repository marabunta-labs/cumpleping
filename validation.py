"""Validation and cleaning of user input."""

MAX_NAME_LENGTH = 50
MIN_PHONE_DIGITS = 8
MAX_PHONE_DIGITS = 15


def clean_name(text):
    """Collapse whitespace. Returns None if empty or too long."""
    name = " ".join(str(text).split())
    return name if 1 <= len(name) <= MAX_NAME_LENGTH else None


def normalize_phone(text):
    """Keep digits only (international format without '+'). None if it doesn't look like a phone."""
    digits = "".join(c for c in str(text) if c.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if MIN_PHONE_DIGITS <= len(digits) <= MAX_PHONE_DIGITS:
        return digits
    return None
