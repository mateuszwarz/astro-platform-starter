import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Date, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    method = Column(String(20), nullable=False, default="przelew")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
