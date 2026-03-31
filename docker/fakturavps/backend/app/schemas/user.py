from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import uuid
import re


def _validate_password_strength(v: str) -> str:
    if len(v) < 12:
        raise ValueError("Hasło musi mieć minimum 12 znaków")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Hasło musi zawierać co najmniej jedną wielką literę")
    if not re.search(r"[a-z]", v):
        raise ValueError("Hasło musi zawierać co najmniej jedną małą literę")
    if not re.search(r"\d", v):
        raise ValueError("Hasło musi zawierać co najmniej jedną cyfrę")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=/\\]", v):
        raise ValueError("Hasło musi zawierać co najmniej jeden znak specjalny")
    return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def email_max_length(cls, v: str) -> str:
        if len(v) > 254:
            raise ValueError("Adres email jest za długi")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def password_max_length(cls, v: str) -> str:
        if len(v) > 128:
            raise ValueError("Hasło jest za długie")
        return v


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str

    @field_validator("refresh_token")
    @classmethod
    def token_max_length(cls, v: str) -> str:
        if len(v) > 1024:
            raise ValueError("Token jest nieprawidłowy")
        return v


VALID_ROLES = {"admin", "wlasciciel", "ksiegowy", "pracownik", "audytor"}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "pracownik"

    @field_validator("email")
    @classmethod
    def email_normalize(cls, v: str) -> str:
        if len(v) > 254:
            raise ValueError("Adres email jest za długi")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) < 2:
            raise ValueError("Imię i nazwisko musi mieć co najmniej 2 znaki")
        if len(v) > 100:
            raise ValueError("Imię i nazwisko jest za długie")
        return v

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Nieprawidłowa rola. Dozwolone: {', '.join(VALID_ROLES)}")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_password_strength(v)

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in VALID_ROLES:
            raise ValueError(f"Nieprawidłowa rola. Dozwolone: {', '.join(VALID_ROLES)}")
        return v


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}
