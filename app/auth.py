from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    disabled: bool = False


class UserInDB(User):
    hashed_password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a secure password hash."""
    # Argon2 is better, but bcrypt is widely supported
    
    # TRUNCATE PASSWORD: Bcrypt has a hard limit of 72 bytes.
    # If a user provides a password longer than 72 bytes (UTF-8 encoded),
    # passlib/bcrypt will raise a ValueError. We truncate it to prevent the crash.
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        # Truncate to 72 bytes and decode back to string
        # using errors="ignore" to handle potential partial character splits
        password = password_bytes[:72].decode("utf-8", errors="ignore")
    
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    now = datetime.now(timezone.utc)  # Fixed
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "iat": now, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None