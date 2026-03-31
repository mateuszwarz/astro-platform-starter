from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
import uuid


class PaymentCreate(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal
    payment_date: date
    method: str = "przelew"
    notes: Optional[str] = None


class PaymentOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    payment_date: date
    method: str
    notes: Optional[str]
    created_at: datetime
    created_by_id: Optional[uuid.UUID]

    class Config:
        from_attributes = True
