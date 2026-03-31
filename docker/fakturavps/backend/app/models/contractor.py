import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ContractorCategory(str, enum.Enum):
    klient = "klient"
    dostawca = "dostawca"
    oba = "oba"


class ContractorStatus(str, enum.Enum):
    aktywny = "aktywny"
    nieaktywny = "nieaktywny"
    ryzykowny = "ryzykowny"


class Contractor(Base):
    __tablename__ = "contractors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nip = Column(String(20), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    regon = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)
    postal_code = Column(String(10), nullable=True)
    city = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=True)
    bank_account = Column(String(50), nullable=True)
    default_payment_days = Column(Integer, default=14, nullable=False)
    category = Column(String(20), default=ContractorCategory.klient.value, nullable=False)
    status = Column(String(20), default=ContractorStatus.aktywny.value, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
