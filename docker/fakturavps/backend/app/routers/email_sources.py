from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, EmailStr, field_validator, Field

from app.database import get_db
from app.models.email_source import EmailSource, EmailMessage
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.services.email_service import encrypt_password, test_imap_connection

router = APIRouter(prefix="/email-sources", tags=["Poczta"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class EmailSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(993, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=500)
    use_ssl: bool = True
    folder: str = Field("INBOX", min_length=1, max_length=255)
    filter_senders: Optional[List[str]] = None
    processed_label: Optional[str] = Field(None, max_length=100)
    is_active: bool = True

    @field_validator("filter_senders")
    @classmethod
    def validate_senders(cls, v):
        if v is not None and len(v) > 50:
            raise ValueError("Maksymalnie 50 filtrów nadawców")
        return v


class EmailSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    host: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=1, max_length=500)
    use_ssl: Optional[bool] = None
    folder: Optional[str] = Field(None, min_length=1, max_length=255)
    filter_senders: Optional[List[str]] = None
    processed_label: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class EmailSourceOut(BaseModel):
    id: uuid.UUID
    name: str
    host: str
    port: int
    username: str
    use_ssl: bool
    folder: str
    filter_senders: Optional[List[str]]
    processed_label: Optional[str]
    is_active: bool
    last_checked_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class EmailTestRequest(BaseModel):
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(993, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=500)
    use_ssl: bool = True
    folder: str = Field("INBOX", min_length=1, max_length=255)


class EmailMessageOut(BaseModel):
    id: uuid.UUID
    email_source_id: uuid.UUID
    message_id: str
    sender_email: Optional[str]
    sender_name: Optional[str]
    subject: Optional[str]
    received_at: Optional[datetime]
    attachment_count: int
    processed_at: Optional[datetime]
    status: str
    error_message: Optional[str]
    invoices_created: int
    invoices_duplicated: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[EmailSourceOut])
def list_email_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "ksiegowy", "wlasciciel")),
):
    return db.query(EmailSource).all()


@router.get("/log/all", response_model=List[EmailMessageOut])
def get_all_email_log(
    skip: int = Query(0, ge=0, le=100000),
    limit: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "ksiegowy", "wlasciciel")),
):
    """Get email processing log across all sources."""
    q = db.query(EmailMessage)

    allowed_statuses = {"pending", "processed", "error", "duplicate", "skipped"}
    if status_filter and status_filter in allowed_statuses:
        q = q.filter(EmailMessage.status == status_filter)

    q = q.order_by(EmailMessage.created_at.desc()).offset(skip).limit(limit)
    return q.all()


@router.post("/test-connection")
def test_connection(
    body: EmailTestRequest,
    current_user: User = Depends(require_role("admin", "wlasciciel")),
):
    """Test IMAP connection without saving."""
    result = test_imap_connection(
        host=body.host,
        port=body.port,
        username=body.username,
        password=body.password,
        use_ssl=body.use_ssl,
        folder=body.folder,
    )
    return result


@router.post("", response_model=EmailSourceOut, status_code=status.HTTP_201_CREATED)
def create_email_source(
    body: EmailSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "wlasciciel")),
):
    source = EmailSource(
        id=uuid.uuid4(),
        name=body.name,
        host=body.host,
        port=body.port,
        username=body.username,
        encrypted_password=encrypt_password(body.password),
        use_ssl=body.use_ssl,
        folder=body.folder,
        filter_senders=body.filter_senders,
        processed_label=body.processed_label,
        is_active=body.is_active,
        created_by_id=current_user.id,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/{source_id}", response_model=EmailSourceOut)
def get_email_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "ksiegowy", "wlasciciel")),
):
    source = db.query(EmailSource).filter(EmailSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Źródło poczty nie istnieje")
    return source


@router.put("/{source_id}", response_model=EmailSourceOut)
def update_email_source(
    source_id: uuid.UUID,
    body: EmailSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "wlasciciel")),
):
    source = db.query(EmailSource).filter(EmailSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Źródło poczty nie istnieje")

    if body.name is not None:
        source.name = body.name
    if body.host is not None:
        source.host = body.host
    if body.port is not None:
        source.port = body.port
    if body.username is not None:
        source.username = body.username
    if body.password is not None:
        source.encrypted_password = encrypt_password(body.password)
    if body.use_ssl is not None:
        source.use_ssl = body.use_ssl
    if body.folder is not None:
        source.folder = body.folder
    if body.filter_senders is not None:
        source.filter_senders = body.filter_senders
    if body.processed_label is not None:
        source.processed_label = body.processed_label
    if body.is_active is not None:
        source.is_active = body.is_active

    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_email_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "wlasciciel")),
):
    source = db.query(EmailSource).filter(EmailSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Źródło poczty nie istnieje")
    db.delete(source)
    db.commit()


@router.post("/{source_id}/trigger")
def trigger_fetch(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "ksiegowy", "wlasciciel")),
):
    """Manually trigger email fetch for a source."""
    source = db.query(EmailSource).filter(
        EmailSource.id == source_id, EmailSource.is_active == True
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Źródło poczty nie istnieje lub jest nieaktywne")

    from app.tasks.email_tasks import fetch_single_email_source
    task = fetch_single_email_source.delay(str(source_id))
    return {"task_id": task.id, "message": "Pobieranie uruchomione"}


@router.get("/{source_id}/log", response_model=List[EmailMessageOut])
def get_email_log(
    source_id: uuid.UUID,
    skip: int = Query(0, ge=0, le=100000),
    limit: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "ksiegowy", "wlasciciel")),
):
    source = db.query(EmailSource).filter(EmailSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Źródło poczty nie istnieje")

    q = db.query(EmailMessage).filter(EmailMessage.email_source_id == source_id)

    allowed_statuses = {"pending", "processed", "error", "duplicate", "skipped"}
    if status_filter and status_filter in allowed_statuses:
        q = q.filter(EmailMessage.status == status_filter)

    q = q.order_by(EmailMessage.created_at.desc()).offset(skip).limit(limit)
    return q.all()
