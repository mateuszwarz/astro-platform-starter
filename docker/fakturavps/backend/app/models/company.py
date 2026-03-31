import uuid
from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    nip = Column(String(20), nullable=False)
    regon = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)
    postal_code = Column(String(10), nullable=True)
    city = Column(String(100), nullable=True)
    bank_account = Column(String(50), nullable=True)
    vat_rate_default = Column(Integer, default=23, nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
