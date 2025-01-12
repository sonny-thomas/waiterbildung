import secrets
import string

import bcrypt


def validate_password(password: str) -> str:
    """
    Validate a password against a set of rules.
    Args:
        password: Password to validate
    Returns:
        Password if valid
    Raises:
        ValueError if password is invalid
    """
    if len(password) < 8 or len(password) > 64:
        raise ValueError("Password must be between 8 and 64 characters")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one number")
    if not any(not c.isalnum() for c in password):
        raise ValueError("Password must contain at least one special character")
    return password


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    Args:
        password: Plain text password
    Returns:
        Hashed password as string
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to check against
    Returns:
        Boolean indicating if the password matches
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def generate_password(length: int = 12) -> str:
    """
    Generate a strong random password.
    Args:
        length: Length of password (default 16)
    Returns:
        Generated password string
    """

    if length < 8:
        raise ValueError("Password length must be at least 8 characters")

    chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|"
    password = "".join(secrets.choice(chars) for _ in range(length - 4))

    # Ensure password meets requirements by adding required character types
    password += secrets.choice(string.ascii_lowercase)
    password += secrets.choice(string.ascii_uppercase)
    password += secrets.choice(string.digits)
    password += secrets.choice("!@#$%^&*()_+-=[]{}|")

    # Shuffle the password
    password_list = list(password)
    secrets.SystemRandom().shuffle(password_list)
    return "".join(password_list)
