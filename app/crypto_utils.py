import bcrypt
from cryptography.fernet import Fernet
from app.config import SECRET_KEY

_fernet = Fernet(SECRET_KEY)

def normalize_passcode(password: str) -> str:
    """Normalize 16-character Google app passcode by removing visual spaces."""
    cleaned = password.strip()
    no_spaces = cleaned.replace(" ", "")
    if len(no_spaces) == 16:
        return no_spaces
    return cleaned

def hash_password(password: str) -> str:
    """Hash password securely using bcrypt with auto-generated salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against stored bcrypt hash, supporting passcode variations with/without spaces."""
    try:
        # 1. Direct check
        if bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8")):
            return True
        # 2. Check normalized (spaces removed)
        norm = normalize_passcode(plain_password)
        if norm != plain_password and bcrypt.checkpw(norm.encode("utf-8"), hashed_password.encode("utf-8")):
            return True
        # 3. Check with spaces removed
        no_spaces = plain_password.replace(" ", "")
        if bcrypt.checkpw(no_spaces.encode("utf-8"), hashed_password.encode("utf-8")):
            return True
        return False
    except Exception:
        return False

def encrypt_credential(secret_text: str) -> str:
    """Encrypt sensitive string (e.g. Gmail app password) using Fernet AES-256."""
    if not secret_text:
        return ""
    encrypted = _fernet.encrypt(secret_text.encode("utf-8"))
    return encrypted.decode("utf-8")

def decrypt_credential(encrypted_text: str) -> str:
    """Decrypt sensitive string."""
    if not encrypted_text:
        return ""
    try:
        decrypted = _fernet.decrypt(encrypted_text.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception:
        return ""
