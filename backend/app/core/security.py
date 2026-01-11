from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt
from .settings import settings
import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

# Use bcrypt directly to avoid passlib version issues
def hash_password(password: str) -> str:
    """Hash password using bcrypt directly."""
    # Ensure password is bytes and not longer than 72 bytes
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    hashed_bytes = hashed.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def create_access_token(payload: dict) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MIN)
    to_encode = {**payload, "exp": exp}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALG)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])

def _get_fernet_key() -> bytes:
    """Get or generate Fernet encryption key from settings."""
    key_str = settings.TEMP_PASSWORD_ENCRYPTION_KEY
    # Fernet requires a URL-safe base64-encoded 32-byte key
    # Try to use it directly if it's already a valid Fernet key
    try:
        # Try to decode as base64 to validate
        decoded = base64.urlsafe_b64decode(key_str)
        if len(decoded) == 32:
            # It's a valid Fernet key
            return key_str.encode('utf-8')
    except:
        pass
    
    # If not a valid Fernet key, derive one from the string
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'manage_network_temp_pwd',  # Fixed salt for consistency
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(key_str.encode('utf-8')))
    return key

def encrypt_temp_password(password: str) -> str:
    """Encrypt a temporary password for storage in database."""
    if not password:
        return ""
    fernet = Fernet(_get_fernet_key())
    encrypted = fernet.encrypt(password.encode('utf-8'))
    return encrypted.decode('utf-8')

def decrypt_temp_password(encrypted_password: str) -> str | None:
    """Decrypt a temporary password from database."""
    if not encrypted_password:
        return None
    try:
        fernet = Fernet(_get_fernet_key())
        decrypted = fernet.decrypt(encrypted_password.encode('utf-8'))
        return decrypted.decode('utf-8')
    except Exception:
        # If decryption fails, return None
        return None

