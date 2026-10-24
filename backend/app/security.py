import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_fernet = Fernet(settings.phi_encryption_key.encode())
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── PHI Encryption ────────────────────────────────────────────────────────────

def encrypt_phi(plaintext: str) -> str:
    """Encrypt PHI with Fernet (AES-128-CBC + HMAC-SHA256). Returns base64 token."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_phi(token: str) -> str:
    """Decrypt a Fernet token. Raises InvalidToken on tamper."""
    return _fernet.decrypt(token.encode()).decode()


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(subject: str, extra: Optional[dict] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── IP Hashing (HIPAA — raw IP never stored) ──────────────────────────────────

def hash_ip(ip: str) -> str:
    """HMAC-SHA256 keyed hash. Raw IP is never persisted."""
    return hmac.new(
        settings.ip_hash_salt.encode(),
        ip.encode(),
        hashlib.sha256,
    ).hexdigest()
