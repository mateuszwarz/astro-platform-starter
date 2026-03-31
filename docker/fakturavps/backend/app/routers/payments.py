from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from app.database import get_db
from app.models.payment import Payment
from app.models.invoice import Invoice
from app.schemas.payment import PaymentCreate, PaymentOut
from app.dependencies import get_current_user
from app.models.user import User
from app.services.invoice_service import update_invoice_payment_status

router = APIRouter(prefix="/payments", tags=["Płatności"])


@router.get("")
def list_payments(
    invoice_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Payment)
    if invoice_id:
        q = q.filter(Payment.invoice_id == invoice_id)
    total = q.count()
    payments = q.order_by(Payment.payment_date.desc()).offset(skip).limit(limit).all()

    result = []
    for p in payments:
        invoice = db.query(Invoice).filter(Invoice.id == p.invoice_id).first()
        result.append({
            "id": str(p.id),
            "invoice_id": str(p.invoice_id),
            "invoice_number": invoice.number if invoice else None,
            "amount": float(p.amount),
            "payment_date": p.payment_date.isoformat(),
            "method": p.method,
            "notes": p.notes,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {"items": result, "total": total}


@router.post("", response_model=PaymentOut)
def create_payment(
    body: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(Invoice.id == body.invoice_id, Invoice.is_deleted == False).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Faktura nie istnieje")

    payment = Payment(
        id=uuid.uuid4(),
        invoice_id=body.invoice_id,
        amount=body.amount,
        payment_date=body.payment_date,
        method=body.method,
        notes=body.notes,
        created_by_id=current_user.id
    )
    db.add(payment)
    db.flush()
    update_invoice_payment_status(db, invoice, current_user.id)
    db.commit()
    db.refresh(payment)
    return payment


@router.delete("/{payment_id}")
def delete_payment(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Płatność nie istnieje")

    invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
    db.delete(payment)
    db.flush()

    if invoice:
        update_invoice_payment_status(db, invoice, current_user.id)

    db.commit()
    return {"message": "Płatność usunięta"}
