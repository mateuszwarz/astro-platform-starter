import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, Date, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class MatchStatus(str, enum.Enum):
    unmatched = "unmatched"
    matched = "matched"
    ignored = "ignored"
    manual = "manual"


class BankStatement(Base):
    __tablename__ = "bank_statements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=True)
    bank_name = Column(String(100), nullable=True)          # detected bank name
    account_number = Column(String(50), nullable=True)
    statement_date_from = Column(Date, nullable=True)
    statement_date_to = Column(Date, nullable=True)
    transaction_count = Column(Integer, default=0, nullable=False)
    matched_count = Column(Integer, default=0, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id = Column(UUID(as_uuid=True), ForeignKey("bank_statements.id"), nullable=False)
    transaction_date = Column(Date, nullable=False)
    booking_date = Column(Date, nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)          # positive = credit (wpływ), negative = debit
    currency = Column(String(3), nullable=False, default="PLN")
    description = Column(Text, nullable=True)
    counterparty_name = Column(String(255), nullable=True)
    counterparty_account = Column(String(50), nullable=True)
    reference = Column(String(100), nullable=True)           # numer referencyjny transakcji
    # Matching
    match_status = Column(String(20), nullable=False, default=MatchStatus.unmatched.value, index=True)
    matched_invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    match_confidence = Column(Integer, nullable=True)        # 0-100
    match_notes = Column(Text, nullable=True)
    matched_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    matched_at = Column(DateTime(timezone=True), nullable=True)
