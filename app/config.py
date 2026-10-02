import os
from pathlib import Path
from cryptography.fernet import Fernet

APP_NAME = "LazyMail"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Derek Richards (DerekR)"
APP_AUTHOR_ALIAS = "DerekR"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "lazymail.db"
KEY_FILE = DATA_DIR / ".secret.key"

def get_or_create_secret_key() -> bytes:
    """Generate or retrieve Fernet encryption key stored securely."""
    env_key = os.environ.get("LAZYMAIL_SECRET_KEY")
    if env_key:
        return env_key.encode("utf-8")
    
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes().strip()
    
    new_key = Fernet.generate_key()
    KEY_FILE.write_bytes(new_key)
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass
    return new_key

SECRET_KEY = get_or_create_secret_key()
SESSION_EXPIRE_HOURS = 24
MAX_SENT_EMAILS = 50
MAX_INBOX_EMAILS = 50
INBOX_DAYS_LIMIT = 7
