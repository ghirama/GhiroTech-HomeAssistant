import hashlib
import hmac
import secrets

def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 310000)
    return salt.hex() + ':' + digest.hex()

def verify_password(password, stored):
    try:
        salt, expected = stored.split(':', 1)
        actual = password_hash(password, bytes.fromhex(salt)).split(':', 1)[1]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False
