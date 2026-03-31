import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    wlasciciel = "wlasciciel"
    ksiegowy = "ksiegowy"
    pracownik = "pracownik"
    audytor = "audytor"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.pracownik.value)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
