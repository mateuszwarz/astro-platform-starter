from fastapi import APIRouter, Depends, HTTPException, status, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import redis as redis_lib
import json

from app.database import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.user import LoginRequest, Token, TokenRefresh, UserOut
from app.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Autoryzacja"])
limiter = Limiter(key_func=get_remote_address)

# Stałe blokady konta
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

# Klucze Redis dla śledzenia prób logowania
def _failed_key(email: str) -> str:
    return f"login_failed:{email}"

def _lockout_key(email: str) -> str:
    return f"login_lockout:{email}"

def _get_redis():
    try:
        r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        r.ping()
        return r
    except Exception:
        return None


def _record_failed_attempt(email: str):
    r = _get_redis()
    if not r:
        return
    key = _failed_key(email)
    attempts = r.incr(key)
    r.expire(key, LOCKOUT_MINUTES * 60)
    if attempts >= MAX_FAILED_ATTEMPTS:
        r.setex(_lockout_key(email), LOCKOUT_MINUTES * 60, "1")


def _is_locked_out(email: str) -> bool:
    r = _get_redis()
    if not r:
        return False
    return r.exists(_lockout_key(email)) == 1


def _clear_failed_attempts(email: str):
    r = _get_redis()
    if not r:
        return
    r.delete(_failed_key(email))
    r.delete(_lockout_key(email))


def _log_audit(db: Session, user_id, action: str, ip: str, details: dict = None):
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type="auth",
            entity_id=str(user_id) if user_id else None,
            new_data=details or {},
            ip_address=ip,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"

    # Sprawdź blokadę — bez ujawniania czy konto istnieje
    if _is_locked_out(body.email):
        _log_audit(db, None, "login_blocked", ip, {"email": body.email})
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Konto tymczasowo zablokowane. Spróbuj ponownie za {LOCKOUT_MINUTES} minut."
        )

    # Zawsze pobierz użytkownika i zweryfikuj hasło — stały czas odpowiedzi
    user = db.query(User).filter(User.email == body.email, User.is_active == True).first()
    password_ok = verify_password(body.password, user.hashed_password) if user else False

    if not user or not password_ok:
        _record_failed_attempt(body.email)
        _log_audit(db, None, "login_failed", ip, {"email": body.email})
        # Ten sam komunikat niezależnie od przyczyny (nie ujawniamy czy email istnieje)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy email lub hasło"
        )

    _clear_failed_attempts(body.email)
    user.last_login = datetime.utcnow()
    db.commit()

    _log_audit(db, user.id, "login_success", ip, {"role": user.role})

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh")
@limiter.limit("20/minute")
def refresh_token(request: Request, body: TokenRefresh, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nieprawidłowy token")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesja wygasła")
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    _log_audit(db, current_user.id, "logout", ip)
    return {"message": "Wylogowano pomyślnie"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
