import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, Date, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class InvoiceType(str, enum.Enum):
    sprzedaz = "sprzedaz"
    zakup = "zakup"
    korekta = "korekta"
    zaliczkowa = "zaliczkowa"
    proforma = "proforma"
    paragon = "paragon"


class InvoiceStatus(str, enum.Enum):
    szkic = "szkic"
    oczekuje = "oczekuje"
    czesciowo_zaplacona = "czesciowo_zaplacona"
    zaplacona = "zaplacona"
    przeterminowana = "przeterminowana"
    anulowana = "anulowana"
    w_ksef = "w_ksef"
    zaakceptowana_ksef = "zaakceptowana_ksef"
    odrzucona_ksef = "odrzucona_ksef"


class InvoiceSource(str, enum.Enum):
    ksef = "ksef"
    manual = "manual"
    ocr = "ocr"
    email = "email"


class CostType(str, enum.Enum):
    towar = "towar"
    usluga = "usluga"


class VatRate(str, enum.Enum):
    vat_23 = "23"
    vat_8 = "8"
    vat_5 = "5"
    vat_0 = "0"
    zw = "zw"
    np = "np"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number = Column(String(50), nullable=False, unique=True, index=True)
    type = Column(String(20), nullable=False, default=InvoiceType.sprzedaz.value)
    contractor_id = Column(UUID(as_uuid=True), ForeignKey("contractors.id"), nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    issue_date = Column(Date, nullable=False)
    sale_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String(30), nullable=False, default=InvoiceStatus.szkic.value, index=True)
    net_amount = Column(Numeric(12, 2), nullable=False, default=0)
    vat_amount = Column(Numeric(12, 2), nullable=False, default=0)
    gross_amount = Column(Numeric(12, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="PLN")
    notes = Column(Text, nullable=True)
    source = Column(String(20), nullable=False, default=InvoiceSource.manual.value)
    ksef_reference_number = Column(String(100), nullable=True)
    ksef_number = Column(String(100), nullable=True)
    upo_xml = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    # Email import fields
    email_message_id = Column(UUID(as_uuid=True), ForeignKey("email_messages.id"), nullable=True)
    duplicate_of_invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    pdf_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hex of original PDF bytes
    # Cost invoice classification (zakup only)
    cost_type = Column(String(10), nullable=True)  # "towar" or "usluga"
    # Attachment (original uploaded file: photo or PDF)
    attachment_path = Column(String(500), nullable=True)
    attachment_filename = Column(String(255), nullable=True)
    # Accounting approval — admin marks invoice as ready for accounting;
    # ksiegowy role cannot download PDF until this is True
    accounting_approved = Column(Boolean, default=False, nullable=False)


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    name = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 4), nullable=False)
    unit = Column(String(20), nullable=True)
    unit_price_net = Column(Numeric(12, 4), nullable=False)
    vat_rate = Column(String(5), nullable=False)
    net_amount = Column(Numeric(12, 2), nullable=False)
    vat_amount = Column(Numeric(12, 2), nullable=False)
    gross_amount = Column(Numeric(12, 2), nullable=False)
    position_order = Column(Integer, default=1, nullable=False)


class InvoiceStatusHistory(Base):
    __tablename__ = "invoice_status_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    changed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    changed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    source = Column(String(20), nullable=False, default="user")
    reason = Column(Text, nullable=True)
