import base64
import binascii
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import settings

ALGORITHM = "HS256"
SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 3
SCRYPT_MAX_MEMORY = 64 * 1024 * 1024


def _derive_password(password: str, salt: bytes, *, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        maxmem=SCRYPT_MAX_MEMORY,
        dklen=32,
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = _derive_password(password, salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_hash = base64.urlsafe_b64encode(derived).decode("ascii")
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${encoded_salt}${encoded_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, n, r, p, encoded_salt, encoded_hash = password_hash.split("$", 5)
        cost, block_size, parallelism = int(n), int(r), int(p)
        if (
            algorithm != "scrypt"
            or cost != SCRYPT_N
            or block_size != SCRYPT_R
            or parallelism != SCRYPT_P
        ):
            return False
        salt = base64.urlsafe_b64decode(encoded_salt)
        expected = base64.urlsafe_b64decode(encoded_hash)
        actual = _derive_password(
            password,
            salt,
            n=cost,
            r=block_size,
            p=parallelism,
        )
        return hmac.compare_digest(actual, expected)
    except (binascii.Error, ValueError, TypeError):
        return False


def create_access_token(user_id: UUID) -> str:
    issued_at = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> UUID | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        return UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        return None
