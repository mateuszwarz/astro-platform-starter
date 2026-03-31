from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class ContractorCreate(BaseModel):
    nip: Optional[str] = None
    name: str
    regon: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bank_account: Optional[str] = None
    default_payment_days: int = 14
    category: str = "klient"
    status: str = "aktywny"
    notes: Optional[str] = None


class ContractorUpdate(BaseModel):
    nip: Optional[str] = None
    name: Optional[str] = None
    regon: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bank_account: Optional[str] = None
    default_payment_days: Optional[int] = None
    category: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ContractorOut(BaseModel):
    id: uuid.UUID
    nip: Optional[str] = None
    name: str
    regon: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bank_account: Optional[str] = None
    default_payment_days: int
    category: str
    status: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
