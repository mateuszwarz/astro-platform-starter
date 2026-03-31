from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import decode_token
from app.models.user import User

security = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials

    # Podstawowe sanity-check długości — ochrona przed zbyt dużymi tokenami
    if not token or len(token) > 2048:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy token dostępu",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy token dostępu",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nieprawidłowy token")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesja wygasła lub konto zostało dezaktywowane",
        )
    return user


def require_role(*roles: str):
    """
    Dependency factory sprawdzająca rolę użytkownika.
    Użycie: Depends(require_role("admin", "ksiegowy"))
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Brak uprawnień do wykonania tej operacji"
                # Celowo nie ujawniamy jakich ról wymaga endpoint
            )
        return current_user
    return role_checker
