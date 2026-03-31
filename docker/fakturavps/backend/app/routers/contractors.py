from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List
from decimal import Decimal
import uuid
from app.database import get_db
from app.models.contractor import Contractor
from app.models.invoice import Invoice
from app.schemas.contractor import ContractorCreate, ContractorUpdate, ContractorOut
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/contractors", tags=["Kontrahenci"])


@router.get("")
def list_contractors(
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Contractor).filter(Contractor.is_deleted == False)
    if search:
        q = q.filter(or_(
            Contractor.name.ilike(f"%{search}%"),
            Contractor.nip.ilike(f"%{search}%"),
            Contractor.email.ilike(f"%{search}%"),
        ))
    if category:
        q = q.filter(Contractor.category == category)
    if status:
        q = q.filter(Contractor.status == status)
    total = q.count()
    contractors = q.order_by(Contractor.name).offset(skip).limit(limit).all()
    return {"items": contractors, "total": total}


@router.post("", response_model=ContractorOut)
def create_contractor(
    body: ContractorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contractor = Contractor(
        id=uuid.uuid4(),
        created_by_id=current_user.id,
        **body.model_dump()
    )
    db.add(contractor)
    db.commit()
    db.refresh(contractor)
    return contractor


@router.get("/{contractor_id}")
def get_contractor(
    contractor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contractor = db.query(Contractor).filter(
        Contractor.id == contractor_id, Contractor.is_deleted == False
    ).first()
    if not contractor:
        raise HTTPException(status_code=404, detail="Kontrahent nie istnieje")

    invoices = db.query(Invoice).filter(
        Invoice.contractor_id == contractor_id,
        Invoice.is_deleted == False
    ).order_by(Invoice.issue_date.desc()).limit(10).all()

    balance_q = db.query(func.sum(Invoice.gross_amount)).filter(
        Invoice.contractor_id == contractor_id,
        Invoice.is_deleted == False,
        Invoice.status.in_(["oczekuje", "czesciowo_zaplacona", "przeterminowana"])
    ).scalar()
    balance = Decimal(str(balance_q)) if balance_q else Decimal("0")

    return {
        "contractor": contractor,
        "balance": float(balance),
        "recent_invoices": invoices
    }


@router.put("/{contractor_id}", response_model=ContractorOut)
def update_contractor(
    contractor_id: uuid.UUID,
    body: ContractorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contractor = db.query(Contractor).filter(
        Contractor.id == contractor_id, Contractor.is_deleted == False
    ).first()
    if not contractor:
        raise HTTPException(status_code=404, detail="Kontrahent nie istnieje")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(contractor, field, value)
    db.commit()
    db.refresh(contractor)
    return contractor


@router.delete("/{contractor_id}")
def delete_contractor(
    contractor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contractor = db.query(Contractor).filter(
        Contractor.id == contractor_id, Contractor.is_deleted == False
    ).first()
    if not contractor:
        raise HTTPException(status_code=404, detail="Kontrahent nie istnieje")
    contractor.is_deleted = True
    db.commit()
    return {"message": "Kontrahent usunięty"}
