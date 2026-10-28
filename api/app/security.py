import hashlib
import logging
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

logger = logging.getLogger(__name__)

_hasher = PasswordHasher()
# Verified against when the email is unknown, so both failure paths take the same time
# and response timing doesn't reveal which emails exist.
_DUMMY_HASH = _hasher.hash("timing-equalizer")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerificationError:
        return False
    except InvalidHashError:
        logger.error("Stored password hash is malformed; login refused")
        return False


def burn_password_check(password: str) -> None:
    verify_password(_DUMMY_HASH, password)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
