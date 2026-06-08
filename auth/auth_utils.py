import hashlib
import os
import re


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with a random salt."""
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a plain password against a stored hash."""
    try:
        salt, hashed = stored.split("$", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == hashed
    except Exception:
        return False


def validate_email(email: str) -> bool:
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    return True, ""
