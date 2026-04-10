"""
app/auth/password.py
--------------------
Password hashing and verification using direct bcrypt.
"""

import bcrypt

def hash_password(plain: str) -> str:
    """Return the bcrypt hash of *plain*."""
    # bcrypt requires bytes, limit length if needed to avoid ValueError
    pwd_bytes = plain.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored *hashed* password."""
    try:
        pwd_bytes = plain.encode('utf-8')[:72]
        hash_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False
