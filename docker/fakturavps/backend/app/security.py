from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # koszt haszowania — dobry balans bezpieczeństwo/wydajność
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access", "iat": datetime.utcnow()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "iat": datetime.utcnow()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Zwraca payload lub None. Nigdy nie rzuca wyjątku.
    Weryfikuje algorytm jawnie (options["algorithms"]) — ochrona przed algorithm confusion.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],  # lista jawna — brak możliwości algorithm=none
            options={"verify_exp": True},
        )
        return payload
    except ExpiredSignatureError:
        return None
    except JWTError:
        return None
    except Exception:
        return None
