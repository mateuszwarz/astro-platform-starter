from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
import uuid


class InvoiceItemCreate(BaseModel):
    name: str
    quantity: Decimal
    unit: Optional[str] = "szt"
    unit_price_net: Decimal
    vat_rate: str = "23"
    position_order: int = 1


class InvoiceItemOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    name: str
    quantity: Decimal
    unit: Optional[str]
    unit_price_net: Decimal
    vat_rate: str
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    position_order: int

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    type: str = "sprzedaz"
    contractor_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    issue_date: date
    sale_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: str = "PLN"
    notes: Optional[str] = None
    source: str = "manual"
    cost_type: Optional[str] = None
    attachment_path: Optional[str] = None
    attachment_filename: Optional[str] = None
    items: List[InvoiceItemCreate] = []


class InvoiceUpdate(BaseModel):
    type: Optional[str] = None
    contractor_id: Optional[uuid.UUID] = None
    issue_date: Optional[date] = None
    sale_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: Optional[str] = None
    notes: Optional[str] = None
    cost_type: Optional[str] = None
    items: Optional[List[InvoiceItemCreate]] = None


class InvoiceStatusHistoryOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    old_status: Optional[str]
    new_status: str
    changed_at: datetime
    changed_by_id: Optional[uuid.UUID]
    source: str
    reason: Optional[str]

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    id: uuid.UUID
    number: str
    type: str
    contractor_id: Optional[uuid.UUID]
    company_id: Optional[uuid.UUID]
    issue_date: date
    sale_date: Optional[date]
    due_date: Optional[date]
    status: str
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    currency: str
    notes: Optional[str]
    source: str
    ksef_reference_number: Optional[str]
    ksef_number: Optional[str]
    upo_xml: Optional[str]
    cost_type: Optional[str]
    attachment_path: Optional[str]
    attachment_filename: Optional[str]
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[uuid.UUID]

    class Config:
        from_attributes = True
