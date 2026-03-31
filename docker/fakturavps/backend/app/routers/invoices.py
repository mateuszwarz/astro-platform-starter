from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, and_
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime, timedelta
import uuid
import io
import mimetypes

from app.database import get_db
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatusHistory
from app.models.contractor import Contractor
from app.models.company import Company
from app.models.payment import Payment
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceOut, InvoiceItemOut, InvoiceStatusHistoryOut
from app.schemas.payment import PaymentCreate, PaymentOut
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.services.invoice_service import (
    calculate_item_amounts, recalculate_invoice_totals,
    generate_invoice_number, update_invoice_payment_status
)
from app.services.pdf_service import generate_invoice_pdf
from app.services.ksef_service import send_invoice, check_status
from app.services.ocr_service import (
    extract_text, parse_invoice_fields, save_uploaded_file, load_attachment
)

router = APIRouter(prefix="/invoices", tags=["Faktury"])

ALLOWED_UPLOAD_MIME = {
    "application/pdf",
    "image/jpeg", "image/jpg", "image/png",
    "image/tiff", "image/webp", "image/bmp",
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/ocr-upload")
async def ocr_upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload a PDF or image, run OCR, and return pre-filled invoice fields."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_UPLOAD_MIME:
        raise HTTPException(status_code=415, detail="Dozwolone formaty: PDF, JPEG, PNG, TIFF, WebP, BMP")
    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Plik zbyt duży (max 20 MB)")

    original_name = file.filename or "dokument"
    stored_name = save_uploaded_file(file_bytes, original_name)
    text = extract_text(file_bytes, original_name)
    fields = parse_invoice_fields(text)

    return {
        "attachment_path": stored_name,
        "attachment_filename": original_name,
        **fields,
    }


@router.get("/{invoice_id}/attachment")
def download_attachment(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download the original uploaded file attached to an invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_deleted == False).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Faktura nie istnieje")
    if not invoice.attachment_path:
        raise HTTPException(status_code=404, detail="Brak załącznika")
    if current_user.role == "ksiegowy" and not invoice.accounting_approved:
        raise HTTPException(status_code=403, detail="Faktura nie została zatwierdzona do księgowania")

    file_bytes = load_attachment(invoice.attachment_path)
    if file_bytes is None:
        raise HTTPException(status_code=404, detail="Plik załącznika nie istnieje na serwerze")

    mime, _ = mimetypes.guess_type(invoice.attachment_filename or invoice.attachment_path)
    media_type = mime or "application/octet-stream"
    filename = invoice.attachment_filename or invoice.attachment_path

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/summary")
def get_sales_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Summary for sales invoices: totals by payment state, overdue info."""
    today = date.today()

    # Unpaid (oczekuje + czesciowo_zaplacona)
    unpaid_total = db.query(func.sum(Invoice.gross_amount)).filter(
        Invoice.is_deleted == False,
        Invoice.type == "sprzedaz",
        Invoice.status.in_(["oczekuje", "czesciowo_zaplacona"]),
    ).scalar() or 0

    # Overdue
    overdue_total = db.query(func.sum(Invoice.gross_amount)).filter(
        Invoice.is_deleted == False,
        Invoice.type == "sprzedaz",
        Invoice.status == "przeterminowana",
    ).scalar() or 0
    overdue_count = db.query(func.count(Invoice.id)).filter(
        Invoice.is_deleted == False,
        Invoice.type == "sprzedaz",
        Invoice.status == "przeterminowana",
    ).scalar() or 0

    # Due within 7 days
    due_soon_total = db.query(func.sum(Invoice.gross_amount)).filter(
        Invoice.is_deleted == False,
        Invoice.type == "sprzedaz",
        Invoice.status.in_(["oczekuje", "czesciowo_zaplacona"]),
        Invoice.due_date != None,
        Invoice.due_date >= today,
        Invoice.due_date <= today + timedelta(days=7),
    ).scalar() or 0
    due_soon_count = db.query(func.count(Invoice.id)).filter(
        Invoice.is_deleted == False,
        Invoice.type == "sprzedaz",
        Invoice.status.in_(["oczekuje", "czesciowo_zaplacona"]),
        Invoice.due_date != None,
        Invoice.due_date >= today,
        Invoice.due_date <= today + timedelta(days=7),
    ).scalar() or 0

    # Paid this month
    paid_this_month = db.query(func.sum(Invoice.gross_amount)).filter(
        Invoice.is_deleted == False,
        Invoice.type == "sprzedaz",
        Invoice.status == "zaplacona",
        Invoice.updated_at >= datetime(today.year, today.month, 1),
    ).scalar() or 0

    return {
        "unpaid_total": float(unpaid_total),
        "overdue_total": float(overdue_total),
        "overdue_count": int(overdue_count),
        "due_soon_total": float(due_soon_total),
        "due_soon_count": int(due_soon_count),
        "paid_this_month": float(paid_this_month),
        "total_expected": float(unpaid_total) + float(overdue_total),
    }


@router.patch("/{invoice_id}/quick-pay")
def quick_pay_toggle(
    invoice_id: uuid.UUID,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Quick toggle: mark invoice as paid (or revert to oczekuje).
    body: { "paid": true/false, "payment_date": "YYYY-MM-DD" (optional) }
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_deleted == False).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Faktura nie istnieje")
    if invoice.status == "anulowana":
        raise HTTPException(status_code=400, detail="Nie można zmienić statusu anulowanej faktury")

    paid: bool = bool(body.get("paid", True))
    payment_date_str = body.get("payment_date")
    try:
        pay_date = date.fromisoformat(payment_date_str) if payment_date_str else date.today()
    except ValueError:
        pay_date = date.today()

    old_status = invoice.status

    if paid:
        # Create a payment for remaining amount
        existing_payments = db.query(Payment).filter(Payment.invoice_id == invoice_id).all()
        total_paid = sum(Decimal(str(p.amount)) for p in existing_payments)
        remaining = Decimal(str(invoice.gross_amount)) - total_paid
        if remaining > 0:
            payment = Payment(
                id=uuid.uuid4(),
                invoice_id=invoice_id,
                amount=remaining,
                payment_date=pay_date,
                method="przelew",
                notes="Szybkie oznaczenie jako opłacona",
                created_by_id=current_user.id,
            )
            db.add(payment)
            db.flush()

        invoice.status = "zaplacona"
        invoice.updated_at = datetime.utcnow()
        db.add(InvoiceStatusHistory(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            old_status=old_status,
            new_status="zaplacona",
            changed_by_id=current_user.id,
            source="user",
            reason="Ręczne oznaczenie jako opłacona",
        ))
    else:
        # Revert: remove quick-pay payments, set back to oczekuje/przeterminowana
        db.query(Payment).filter(
            Payment.invoice_id == invoice_id,
            Payment.notes == "Szybkie oznaczenie jako opłacona",
        ).delete()
        db.flush()

        today = date.today()
        new_status = "przeterminowana" if (invoice.due_date and invoice.due_date < today) else "oczekuje"
        invoice.status = new_status
        invoice.updated_at = datetime.utcnow()
        db.add(InvoiceStatusHistory(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            old_status=old_status,
            new_status=new_status,
            changed_by_id=current_user.id,
            source="user",
            reason="Cofnięcie oznaczenia jako opłacona",
        ))

    db.commit()
    return {"id": str(invoice.id), "status": invoice.status}


@router.get("/stats")
def get_invoice_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    status_counts = db.query(Invoice.status, func.count(Invoice.id)).filter(
        Invoice.is_deleted == False
    ).group_by(Invoice.status).all()

    receivables = db.query(func.sum(Invoice.gross_amount)).filter(
        Invoice.is_deleted == False,
        Invoice.type == "sprzedaz",
        Invoice.status.in_(["oczekuje", "czesciowo_zaplacona", "przeterminowana"])
    ).scalar() or 0

    payables = db.query(func.sum(Invoice.gross_amount)).filter(
        Invoice.is_deleted == False,
        Invoice.type == "zakup",
        Invoice.status.in_(["oczekuje", "czesciowo_zaplacona", "przeterminowana"])
    ).scalar() or 0

    return {
        "status_counts": {s: c for s, c in status_counts},
        "receivables_total": float(receivables),
        "payables_total": float(payables),
    }


VALID_INVOICE_STATUSES = {
    "szkic", "oczekuje", "czesciowo_zaplacona", "zaplacona",
    "przeterminowana", "anulowana", "w_ksef", "zaakceptowana_ksef", "odrzucona_ksef"
}
VALID_INVOICE_TYPES = {"sprzedaz", "zakup", "korekta", "zaliczkowa", "proforma", "paragon"}
VALID_SOURCES = {"ksef", "manual", "ocr"}


@router.get("")
def list_invoices(
    status: Optional[str] = Query(None, max_length=200),
    type: Optional[str] = Query(None, max_length=20),
    contractor_id: Optional[uuid.UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    source: Optional[str] = Query(None, max_length=20),
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    skip: int = Query(0, ge=0, le=100000),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Invoice).filter(Invoice.is_deleted == False)
    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip() in VALID_INVOICE_STATUSES]
        if statuses:
            q = q.filter(Invoice.status.in_(statuses))
    if type:
        if type not in VALID_INVOICE_TYPES:
            raise HTTPException(status_code=400, detail="Nieprawidłowy typ faktury")
        q = q.filter(Invoice.type == type)
    if contractor_id:
        q = q.filter(Invoice.contractor_id == contractor_id)
    if date_from:
        q = q.filter(Invoice.issue_date >= date_from)
    if date_to:
        q = q.filter(Invoice.issue_date <= date_to)
    if source:
        q = q.filter(Invoice.source == source)
    if search:
        contractor_ids = db.query(Contractor.id).filter(
            or_(
                Contractor.name.ilike(f"%{search}%"),
                Contractor.nip.ilike(f"%{search}%")
            )
        ).all()
        cids = [c.id for c in contractor_ids]
        q = q.filter(or_(
            Invoice.number.ilike(f"%{search}%"),
            Invoice.contractor_id.in_(cids)
        ))

    total = q.count()
    invoices = q.order_by(Invoice.issue_date.desc(), Invoice.number.desc()).offset(skip).limit(limit).all()

    today = date.today()
    result = []
    for inv in invoices:
        contractor = db.query(Contractor).filter(Contractor.id == inv.contractor_id).first() if inv.contractor_id else None

        # Payment timing
        days_until_due = None
        days_overdue = None
        if inv.due_date:
            diff = (inv.due_date - today).days
            if diff >= 0:
                days_until_due = diff
            else:
                days_overdue = abs(diff)

        d = {
            "id": str(inv.id),
            "number": inv.number,
            "type": inv.type,
            "status": inv.status,
            "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "sale_date": inv.sale_date.isoformat() if inv.sale_date else None,
            "net_amount": float(inv.net_amount),
            "vat_amount": float(inv.vat_amount),
            "gross_amount": float(inv.gross_amount),
            "currency": inv.currency,
            "source": inv.source,
            "contractor_id": str(inv.contractor_id) if inv.contractor_id else None,
            "contractor_name": contractor.name if contractor else None,
            "contractor_nip": contractor.nip if contractor else None,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "cost_type": inv.cost_type,
            "has_attachment": bool(inv.attachment_path),
            "days_until_due": days_until_due,
            "days_overdue": days_overdue,
            "accounting_approved": bool(inv.accounting_approved),
        }
        result.append(d)

    return {"items": result, "total": total}


@router.post("")
def create_invoice(
    body: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "wlasciciel", "pracownik")),
):
    # Walidacja istnienia kontrahenta
    if body.contractor_id:
        contractor_exists = db.query(Contractor).filter(
            Contractor.id == body.contractor_id,
            Contractor.status != "nieaktywny"
        ).first()
        if not contractor_exists:
            raise HTTPException(status_code=404, detail="Kontrahent nie istnieje lub jest nieaktywny")

    # Walidacja istnienia firmy
    if body.company_id:
        from app.models.company import Company as CompanyModel
        company_exists = db.query(CompanyModel).filter(
            CompanyModel.id == body.company_id,
            CompanyModel.is_active == True
        ).first()
        if not company_exists:
            raise HTTPException(status_code=404, detail="Firma nie istnieje")

    from datetime import datetime as dt
    year = body.issue_date.year if body.issue_date else dt.now().year
    number = generate_invoice_number(db, body.type, year)

    # cost_type is only meaningful for zakup invoices
    cost_type = body.cost_type if body.type == "zakup" else None

    invoice = Invoice(
        id=uuid.uuid4(),
        number=number,
        type=body.type,
        contractor_id=body.contractor_id,
        company_id=body.company_id,
        issue_date=body.issue_date,
        sale_date=body.sale_date,
        due_date=body.due_date,
        currency=body.currency,
        notes=body.notes,
        source=body.source,
        status="szkic",
        created_by_id=current_user.id,
        net_amount=Decimal("0"),
        vat_amount=Decimal("0"),
        gross_amount=Decimal("0"),
        cost_type=cost_type,
        attachment_path=body.attachment_path,
        attachment_filename=body.attachment_filename,
    )
    db.add(invoice)
    db.flush()

    items = []
    for item_data in body.items:
        net, vat, gross = calculate_item_amounts(
            Decimal(str(item_data.quantity)),
            Decimal(str(item_data.unit_price_net)),
            item_data.vat_rate
        )
        item = InvoiceItem(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            name=item_data.name,
            quantity=item_data.quantity,
            unit=item_data.unit,
            unit_price_net=item_data.unit_price_net,
            vat_rate=item_data.vat_rate,
            net_amount=net,
            vat_amount=vat,
            gross_amount=gross,
            position_order=item_data.position_order,
        )
        db.add(item)
        items.append(item)

    db.flush()
    total_net, total_vat, total_gross = recalculate_invoice_totals(items)
    invoice.net_amount = total_net
    invoice.vat_amount = total_vat
    invoice.gross_amount = total_gross

    history = InvoiceStatusHistory(
        id=uuid.uuid4(),
        invoice_id=invoice.id,
        old_status=None,
        new_status="szkic",
        changed_by_id=current_user.id,
        source="user"
    )
    db.add(history)
    db.commit()
    db.refresh(invoice)
    return {"id": str(invoice.id), "number": invoice.number, "status": invoice.status}


@router.get("/{invoice_id}")
def get_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_deleted == False).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Faktura nie istnieje")

    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).order_by(InvoiceItem.position_order).all()
    payments = db.query(Payment).filter(Payment.invoice_id == invoice_id).order_by(Payment.payment_date).all()
    history = db.query(InvoiceStatusHistory).filter(
        InvoiceStatusHistory.invoice_id == invoice_id
    ).order_by(InvoiceStatusHistory.changed_at.desc()).all()

    contractor = db.query(Contractor).filter(Contractor.id == invoice.contractor_id).first() if invoice.contractor_id else None
    company = db.query(Company).filter(Company.id == invoice.company_id).first() if invoice.company_id else None

    total_paid = sum(Decimal(str(p.amount)) for p in payments)
    remaining = Decimal(str(invoice.gross_amount)) - total_paid

    return {
        "invoice": {
            "id": str(invoice.id),
            "number": invoice.number,
            "type": invoice.type,
            "status": invoice.status,
            "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "sale_date": invoice.sale_date.isoformat() if invoice.sale_date else None,
            "net_amount": float(invoice.net_amount),
            "vat_amount": float(invoice.vat_amount),
            "gross_amount": float(invoice.gross_amount),
            "currency": invoice.currency,
            "notes": invoice.notes,
            "source": invoice.source,
            "ksef_reference_number": invoice.ksef_reference_number,
            "ksef_number": invoice.ksef_number,
            "contractor_id": str(invoice.contractor_id) if invoice.contractor_id else None,
            "company_id": str(invoice.company_id) if invoice.company_id else None,
            "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
            "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None,
            "cost_type": invoice.cost_type,
            "attachment_path": invoice.attachment_path,
            "attachment_filename": invoice.attachment_filename,
            "accounting_approved": bool(invoice.accounting_approved),
        },
        "items": [
            {
                "id": str(i.id),
                "name": i.name,
                "quantity": float(i.quantity),
                "unit": i.unit,
                "unit_price_net": float(i.unit_price_net),
                "vat_rate": i.vat_rate,
                "net_amount": float(i.net_amount),
                "vat_amount": float(i.vat_amount),
                "gross_amount": float(i.gross_amount),
                "position_order": i.position_order,
            }
            for i in items
        ],
        "payments": [
            {
                "id": str(p.id),
                "amount": float(p.amount),
                "payment_date": p.payment_date.isoformat(),
                "method": p.method,
                "notes": p.notes,
            }
            for p in payments
        ],
        "history": [
            {
                "id": str(h.id),
                "old_status": h.old_status,
                "new_status": h.new_status,
                "changed_at": h.changed_at.isoformat() if h.changed_at else None,
                "source": h.source,
                "reason": h.reason,
            }
            for h in history
        ],
        "contractor": {
            "id": str(contractor.id),
            "name": contractor.name,
            "nip": contractor.nip,
            "address": contractor.address,
            "postal_code": contractor.postal_code,
            "city": contractor.city,
            "email": contractor.email,
        } if contractor else None,
        "company": {
            "id": str(company.id),
            "name": company.name,
            "nip": company.nip,
            "address": company.address,
            "city": company.city,
            "bank_account": company.bank_account,
        } if company else None,
        "total_paid": float(total_paid),
        "remaining": float(remaining),
    }


@router.put("/{invoice_id}")
def update_invoice(
    invoice_id: uuid.UUID,
    body: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "wlasciciel", "pracownik"))
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_deleted == False).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Faktura nie istnieje")
    if invoice.status not in ("szkic",) and invoice.status in ("zaakceptowana_ksef", "anulowana"):
        raise HTTPException(status_code=400, detail="Nie można edytować faktury w tym statusie")

    if body.type is not None:
        invoice.type = body.type
    if body.contractor_id is not None:
        invoice.contractor_id = body.contractor_id
    if body.issue_date is not None:
        invoice.issue_date = body.issue_date
    if body.sale_date is not None:
        invoice.sale_date = body.sale_date
    if body.due_date is not None:
        invoice.due_date = body.due_date
    if body.currency is not None:
        invoice.currency = body.currency
    if body.notes is not None:
        invoice.notes = body.notes
    if body.cost_type is not None:
        invoice.cost_type = body.cost_type if invoice.type == "zakup" else None

    if body.items is not None:
        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
        db.flush()
        new_items = []
        for item_data in body.items:
            net, vat, gross = calculate_item_amounts(
                Decimal(str(item_data.quantity)),
                Decimal(str(item_data.unit_price_net)),
                item_data.vat_rate
            )
            item = InvoiceItem(
                id=uuid.uuid4(),
                invoice_id=invoice.id,
                name=item_data.name,
                quantity=item_data.quantity,
                unit=item_data.unit,
                unit_price_net=item_data.unit_price_net,
                vat_rate=item_data.vat_rate,
                net_amount=net,
                vat_amount=vat,
                gross_amount=gross,
                position_order=item_data.position_order,
            )
            db.add(item)
            new_items.append(item)
        db.flush()
        total_net, total_vat, total_gross = recalculate_invoice_totals(new_items)
        invoice.net_amount = total_net
        invoice.vat_amount = total_vat
        invoice.gross_amount = total_gross

    invoice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(invoice)
    return {"id": str(invoice.id), "number": invoice.number, "status": invoice.status}


VALID_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "szkic":               ["oczekuje", "anulowana"],
    "oczekuje":            ["czesciowo_zaplacona", "zaplacona", "przeterminowana", "anulowana", "szkic"],
    "czesciowo_zaplacona": ["zaplacona", "przeterminowana", "anulowana"],
    "przeterminowana":     ["oczekuje", "czesciowo_zaplacona", "zaplacona", "anulowana"],
    "zaplacona":           ["anulowana"],
    "anulowana":           [],
    "w_ksef":              ["zaakceptowana_ksef", "odrzucona_ksef"],
    "zaakceptowana_ksef":  [],
    "odrzucona_ksef":      ["oczekuje"],
}


@router.patch("/{invoice_id}/status")
def change_invoice_status(
    invoice_id: uuid.UUID,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_deleted == False).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Faktura nie istnieje")

    new_status: str = body.get("status", "")
    if new_status not in VALID_INVOICE_STATUSES:
        raise HTTPException(status_code=400, detail="Nieprawidłowy status")

    allowed = VALID_STATUS_TRANSITIONS.get(invoice.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Nie można zmienić statusu z '{invoice.status}' na '{new_status}'"
        )

    old_status = invoice.status
    invoice.status = new_status
    invoice.updated_at = datetime.utcnow()

    db.add(InvoiceStatusHistory(
        id=uuid.uuid4(),
        invoice_id=invoice.id,
        old_status=old_status,
        new_status=new_status,
        changed_by_id=current_user.id,
        source="user",
        reason=body.get("reason"),
    ))
    db.commit()
    return {"id": str(invoice.id), "status": invoice.status}


@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "wlasciciel")),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_deleted == False).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Faktura nie istnieje")
    if invoice.status != "szkic":
        raise HTTPException(status_code=400, detail="Można usunąć tylko faktury w statusie szkic")
    invoice.is_deleted = True
    db.commit()
    return {"message": "Faktura usunięta"}


@router.post("/{invoice_id}/send-ksef")
def send_to_ksef(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_deleted == False).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Faktura nie istnieje")
    if invoice.status in ("anulowana", "zaakceptowana_ksef"):
        raise HTTPException(status_code=400, detail="Nie można wysłać faktury w tym statusie do KSeF")

    result = send_invoice({"invoice_id": str(invoice.id), "number": invoice.number})
    old_status = invoice.status
    invoice.status = "w_ksef"
    invoice.ksef_reference_number = result["ksef_reference"]
    invoice.updated_at = datetime.utcnow()

    history = InvoiceStatusHistory(
        id=uuid.uuid4(),
        invoice_id=invoice.id,
        old_status=old_status,
        new_status="w_ksef",
        changed_by_id=current_user.id,
        source="user",
        reason="Wysłano do KSeF"
    )
    db.add(history)

    ksef_result = check_status(result["ksef_reference"])
    invoice.status = "zaakceptowana_ksef"
    invoice.ksef_number = ksef_result["ksef_number"]
    invoice.upo_xml = ksef_result["upo_xml"]

    history2 = InvoiceStatusHistory(
        id=uuid.uuid4(),
        invoice_id=invoice.id,
        old_status="w_ksef",
        new_status="zaakceptowana_ksef",
        changed_by_id=None,
        source="system",
        reason=f"Zaakceptowano przez KSeF, numer: {ksef_result['ksef_number']}"
    )
    db.add(history2)
    db.commit()

    return {
        "status": "zaakceptowana_ksef",
        "ksef_number": invoice.ksef_number,
        "ksef_reference": invoice.ksef_reference_number
    }


@router.post("/{invoice_id}/payments")
def add_payment(
    invoice_id: uuid.UUID,
    body: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_deleted == False).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Faktura nie istnieje")
    if invoice.status == "anulowana":
        raise HTTPException(status_code=400, detail="Nie można dodać płatności do anulowanej faktury")

    payment = Payment(
        id=uuid.uuid4(),
        invoice_id=invoice_id,
        amount=body.amount,
        payment_date=body.payment_date,
        method=body.method,
        notes=body.notes,
        created_by_id=current_user.id
    )
    db.add(payment)

    if invoice.status == "szkic":
        old_status = invoice.status
        invoice.status = "oczekuje"
        history = InvoiceStatusHistory(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            old_status=old_status,
            new_status="oczekuje",
            changed_by_id=current_user.id,
            source="user"
        )
        db.add(history)

    db.flush()
    update_invoice_payment_status(db, invoice, current_user.id)
    db.commit()

    return {
        "id": str(payment.id),
        "amount": float(payment.amount),
        "invoice_status": invoice.status
    }


@router.patch("/{invoice_id}/accounting-approve")
def accounting_approve(
    invoice_id: uuid.UUID,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "wlasciciel")),
):
    """Admin/owner toggles accounting approval flag on an invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_deleted == False).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Faktura nie istnieje")
    approved: bool = bool(body.get("approved", True))
    invoice.accounting_approved = approved
    invoice.updated_at = datetime.utcnow()
    db.commit()
    return {"id": str(invoice.id), "accounting_approved": invoice.accounting_approved}


@router.get("/{invoice_id}/pdf")
def get_invoice_pdf(
    invoice_id: uuid.UUID,
    include_cost_type: bool = Query(True, description="Uwzględnij informację Towar/Usługa w PDF"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_deleted == False).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Faktura nie istnieje")

    # Accountants can only download approved invoices
    if current_user.role == "ksiegowy" and not invoice.accounting_approved:
        raise HTTPException(status_code=403, detail="Faktura nie została zatwierdzona do księgowania")

    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).order_by(InvoiceItem.position_order).all()
    contractor = db.query(Contractor).filter(Contractor.id == invoice.contractor_id).first() if invoice.contractor_id else None
    company = db.query(Company).filter(Company.id == invoice.company_id).first() if invoice.company_id else None

    pdf_bytes = generate_invoice_pdf(invoice, contractor, items, company, include_cost_type=include_cost_type)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=faktura_{invoice.number.replace('/', '_')}.pdf"}
    )
