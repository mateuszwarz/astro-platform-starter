import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=True)
    old_data = Column(JSON, nullable=True)
    new_data = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
