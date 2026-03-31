import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class EmailMessageStatus(str, enum.Enum):
    pending = "pending"
    processed = "processed"
    error = "error"
    duplicate = "duplicate"
    skipped = "skipped"


class EmailSource(Base):
    __tablename__ = "email_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=993)
    username = Column(String(255), nullable=False)
    encrypted_password = Column(Text, nullable=False)  # Fernet-encrypted
    use_ssl = Column(Boolean, nullable=False, default=True)
    folder = Column(String(255), nullable=False, default="INBOX")
    filter_senders = Column(JSON, nullable=True)  # list of allowed sender email patterns
    processed_label = Column(String(100), nullable=True)  # IMAP label to apply after processing
    is_active = Column(Boolean, nullable=False, default=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_source_id = Column(UUID(as_uuid=True), ForeignKey("email_sources.id"), nullable=False)
    message_id = Column(String(500), nullable=False, unique=True, index=True)  # IMAP Message-ID header
    sender_email = Column(String(255), nullable=True)
    sender_name = Column(String(255), nullable=True)
    subject = Column(String(1000), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    attachment_count = Column(Integer, nullable=False, default=0)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default=EmailMessageStatus.pending.value, index=True)
    error_message = Column(Text, nullable=True)
    invoices_created = Column(Integer, nullable=False, default=0)
    invoices_duplicated = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
