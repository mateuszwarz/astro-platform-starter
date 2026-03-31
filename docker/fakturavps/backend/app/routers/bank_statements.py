from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from decimal import Decimal
from datetime import datetime, date
import uuid

from app.database import get_db
from app.models.bank_statement import BankStatement, BankTransaction, MatchStatus
from app.models.invoice import Invoice, InvoiceStatusHistory
from app.models.contractor import Contractor
from app.models.payment import Payment
from app.dependencies import get_current_user
from app.models.user import User
from app.services.bank_statement_service import (
    parse_bank_statement, save_statement_file, find_matches
)
from app.services.invoice_service import update_invoice_payment_status

router = APIRouter(prefix="/bank-statements", tags=["Wyciągi bankowe"])

ALLOWED_MIME = {
    "text/csv", "text/plain", "application/csv",
    "application/octet-stream", "application/vnd.ms-excel",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

UNMATCHED_INVOICE_STATUSES = {
    "oczekuje", "czesciowo_zaplacona", "przeterminowana", "szkic"
}


@router.post("/upload")
async def upload_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a bank statement (CSV or MT940), auto-parse and match to invoices."""
    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Plik zbyt duży (max 10 MB)")

    original_name = file.filename or "wyciag"
    stored_path = save_statement_file(file_bytes, original_name)
    transactions_raw, detected_format = parse_bank_statement(file_bytes, original_name)

    if not transactions_raw:
        raise HTTPException(
            status_code=422,
            detail="Nie udało się sparsować pliku. Sprawdź format (CSV z nagłówkami, MT940)."
        )

    # Determine date range from parsed transactions
    dates = [t.transaction_date for t in transactions_raw if t.transaction_date]
    date_from = min(dates) if dates else None
    date_to = max(dates) if dates else None

    # Create statement record
    statement = BankStatement(
        id=uuid.uuid4(),
        filename=original_name,
        stored_path=stored_path,
        bank_name=detected_format,
        statement_date_from=date_from,
        statement_date_to=date_to,
        transaction_count=len(transactions_raw),
        matched_count=0,
        uploaded_by_id=current_user.id,
    )
    db.add(statement)
    db.flush()

    # Load candidate invoices for matching (not paid/cancelled, ±90 days from statement)
    invoice_q = db.query(Invoice).filter(
        Invoice.is_deleted == False,
        Invoice.status.in_(UNMATCHED_INVOICE_STATUSES),
    )
    if date_from:
        from datetime import timedelta
        invoice_q = invoice_q.filter(
            Invoice.issue_date >= date_from - timedelta(days=90)
        )
    raw_invoices = invoice_q.all()
    invoices_with_contractors = []
    for inv in raw_invoices:
        contractor = db.query(Contractor).filter(
            Contractor.id == inv.contractor_id
        ).first() if inv.contractor_id else None
        invoices_with_contractors.append((inv, contractor))

    # Persist transactions + auto-match
    auto_matched = 0
    for raw_t in transactions_raw:
        bt = BankTransaction(
            id=uuid.uuid4(),
            statement_id=statement.id,
            transaction_date=raw_t.transaction_date,
            booking_date=raw_t.booking_date,
            amount=raw_t.amount,
            currency=raw_t.currency or "PLN",
            description=raw_t.description[:2000] if raw_t.description else None,
            counterparty_name=raw_t.counterparty_name[:255] if raw_t.counterparty_name else None,
            counterparty_account=raw_t.counterparty_account[:50] if raw_t.counterparty_account else None,
            reference=raw_t.reference[:100] if raw_t.reference else None,
            match_status=MatchStatus.unmatched.value,
        )

        # Only try to match credits (incoming money, amount > 0) for sales invoices
        # and debits (outgoing, amount < 0) for cost invoices
        if raw_t.amount is not None:
            matches = find_matches(raw_t, invoices_with_contractors)
            if matches and matches[0]["confidence"] >= 80:
                best = matches[0]
                bt.match_status = MatchStatus.matched.value
                bt.matched_invoice_id = uuid.UUID(best["invoice_id"])
                bt.match_confidence = best["confidence"]
                bt.match_notes = f"Auto-match, pewność: {best['confidence']}%"
                auto_matched += 1

        db.add(bt)

    statement.matched_count = auto_matched
    db.commit()
    db.refresh(statement)

    return {
        "id": str(statement.id),
        "filename": statement.filename,
        "detected_format": detected_format,
        "transaction_count": len(transactions_raw),
        "auto_matched": auto_matched,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
    }


@router.get("")
def list_statements(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total = db.query(BankStatement).count()
    statements = db.query(BankStatement).order_by(
        BankStatement.uploaded_at.desc()
    ).offset(skip).limit(limit).all()

    return {
        "items": [
            {
                "id": str(s.id),
                "filename": s.filename,
                "bank_name": s.bank_name,
                "account_number": s.account_number,
                "date_from": s.statement_date_from.isoformat() if s.statement_date_from else None,
                "date_to": s.statement_date_to.isoformat() if s.statement_date_to else None,
                "transaction_count": s.transaction_count,
                "matched_count": s.matched_count,
                "uploaded_at": s.uploaded_at.isoformat() if s.uploaded_at else None,
            }
            for s in statements
        ],
        "total": total,
    }


@router.get("/{statement_id}/transactions")
def list_transactions(
    statement_id: uuid.UUID,
    match_status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = db.query(BankStatement).filter(BankStatement.id == statement_id).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Wyciąg nie istnieje")

    q = db.query(BankTransaction).filter(BankTransaction.statement_id == statement_id)
    if match_status and match_status in ("unmatched", "matched", "ignored", "manual"):
        q = q.filter(BankTransaction.match_status == match_status)

    total = q.count()
    transactions = q.order_by(BankTransaction.transaction_date.desc()).offset(skip).limit(limit).all()

    result = []
    for t in transactions:
        matched_invoice = None
        if t.matched_invoice_id:
            inv = db.query(Invoice).filter(Invoice.id == t.matched_invoice_id).first()
            contractor = db.query(Contractor).filter(
                Contractor.id == inv.contractor_id
            ).first() if inv and inv.contractor_id else None
            if inv:
                matched_invoice = {
                    "id": str(inv.id),
                    "number": inv.number,
                    "type": inv.type,
                    "status": inv.status,
                    "gross_amount": float(inv.gross_amount),
                    "contractor_name": contractor.name if contractor else None,
                }
        result.append({
            "id": str(t.id),
            "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
            "booking_date": t.booking_date.isoformat() if t.booking_date else None,
            "amount": float(t.amount),
            "currency": t.currency,
            "description": t.description,
            "counterparty_name": t.counterparty_name,
            "counterparty_account": t.counterparty_account,
            "reference": t.reference,
            "match_status": t.match_status,
            "match_confidence": t.match_confidence,
            "match_notes": t.match_notes,
            "matched_invoice": matched_invoice,
        })

    return {"items": result, "total": total}


@router.get("/{statement_id}/transactions/{transaction_id}/suggestions")
def get_match_suggestions(
    statement_id: uuid.UUID,
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return top-5 invoice match suggestions for a transaction."""
    t = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.statement_id == statement_id,
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transakcja nie istnieje")

    from app.services.bank_statement_service import RawTransaction, find_matches as _find_matches
    raw_t = RawTransaction()
    raw_t.transaction_date = t.transaction_date
    raw_t.amount = Decimal(str(t.amount))
    raw_t.description = t.description or ""
    raw_t.counterparty_name = t.counterparty_name or ""
    raw_t.counterparty_account = t.counterparty_account or ""

    invoices = db.query(Invoice).filter(
        Invoice.is_deleted == False,
        Invoice.status.in_(UNMATCHED_INVOICE_STATUSES | {"zaplacona"}),
    ).all()
    pairs = []
    for inv in invoices:
        c = db.query(Contractor).filter(
            Contractor.id == inv.contractor_id
        ).first() if inv.contractor_id else None
        pairs.append((inv, c))

    matches = _find_matches(raw_t, pairs)
    return {"suggestions": matches}


@router.patch("/{statement_id}/transactions/{transaction_id}/match")
def manual_match(
    statement_id: uuid.UUID,
    transaction_id: uuid.UUID,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually match (or unmatch/ignore) a transaction to an invoice."""
    t = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.statement_id == statement_id,
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transakcja nie istnieje")

    action = body.get("action")  # "match", "unmatch", "ignore"

    if action == "ignore":
        t.match_status = MatchStatus.ignored.value
        t.matched_invoice_id = None
        t.match_confidence = None
        t.match_notes = body.get("notes", "Ręcznie oznaczono jako ignorowana")
        t.matched_by_id = current_user.id
        t.matched_at = datetime.utcnow()

    elif action == "unmatch":
        t.match_status = MatchStatus.unmatched.value
        t.matched_invoice_id = None
        t.match_confidence = None
        t.match_notes = None
        t.matched_by_id = None
        t.matched_at = None

    elif action == "match":
        invoice_id_str = body.get("invoice_id")
        if not invoice_id_str:
            raise HTTPException(status_code=400, detail="Wymagane pole: invoice_id")
        try:
            inv_id = uuid.UUID(invoice_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Nieprawidłowy invoice_id")

        inv = db.query(Invoice).filter(Invoice.id == inv_id, Invoice.is_deleted == False).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Faktura nie istnieje")

        t.match_status = MatchStatus.manual.value
        t.matched_invoice_id = inv_id
        t.match_confidence = 100
        t.match_notes = body.get("notes", "Ręczne dopasowanie")
        t.matched_by_id = current_user.id
        t.matched_at = datetime.utcnow()
    else:
        raise HTTPException(status_code=400, detail="Nieprawidłowe action (match/unmatch/ignore)")

    db.commit()
    return {"id": str(t.id), "match_status": t.match_status}


@router.post("/{statement_id}/transactions/{transaction_id}/confirm-payment")
def confirm_payment_from_transaction(
    statement_id: uuid.UUID,
    transaction_id: uuid.UUID,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Confirm a matched transaction as payment for its invoice.
    Creates a Payment record and updates invoice status.
    """
    t = db.query(BankTransaction).filter(
        BankTransaction.id == transaction_id,
        BankTransaction.statement_id == statement_id,
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transakcja nie istnieje")
    if not t.matched_invoice_id:
        raise HTTPException(status_code=400, detail="Transakcja nie jest dopasowana do faktury")

    inv = db.query(Invoice).filter(
        Invoice.id == t.matched_invoice_id,
        Invoice.is_deleted == False,
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Faktura nie istnieje")
    if inv.status == "anulowana":
        raise HTTPException(status_code=400, detail="Faktura jest anulowana")

    # Check no duplicate payment from this transaction
    existing = db.query(Payment).filter(
        Payment.notes == f"wyciag:{str(t.id)}"
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Płatność dla tej transakcji już istnieje")

    payment = Payment(
        id=uuid.uuid4(),
        invoice_id=inv.id,
        amount=abs(t.amount),
        payment_date=t.transaction_date or date.today(),
        method="przelew",
        notes=f"wyciag:{str(t.id)}",
        created_by_id=current_user.id,
    )
    db.add(payment)

    if inv.status == "szkic":
        inv.status = "oczekuje"
        db.add(InvoiceStatusHistory(
            id=uuid.uuid4(),
            invoice_id=inv.id,
            old_status="szkic",
            new_status="oczekuje",
            changed_by_id=current_user.id,
            source="system",
        ))

    db.flush()
    update_invoice_payment_status(db, inv, current_user.id)

    # Mark transaction as confirmed (keep match_status = matched/manual)
    t.match_notes = (t.match_notes or "") + " | Płatność potwierdzona"
    db.commit()

    return {
        "invoice_id": str(inv.id),
        "invoice_number": inv.number,
        "invoice_status": inv.status,
        "payment_amount": float(abs(t.amount)),
    }


@router.delete("/{statement_id}")
def delete_statement(
    statement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = db.query(BankStatement).filter(BankStatement.id == statement_id).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Wyciąg nie istnieje")
    db.query(BankTransaction).filter(BankTransaction.statement_id == statement_id).delete()
    db.delete(stmt)
    db.commit()
    return {"message": "Wyciąg usunięty"}
