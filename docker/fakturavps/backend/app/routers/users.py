from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.dependencies import get_current_user, require_role
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["Użytkownicy"])


@router.get("", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    return db.query(User).all()


@router.post("", response_model=UserOut)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Użytkownik z tym emailem już istnieje")
    user = User(
        id=uuid.uuid4(),
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    if body.email is not None:
        user.email = body.email
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None and current_user.role == "admin":
        user.role = body.role
    if body.is_active is not None and current_user.role == "admin":
        user.is_active = body.is_active
    if body.password is not None:
        user.hashed_password = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def deactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    user.is_active = False
    db.commit()
    return {"message": "Użytkownik dezaktywowany"}
