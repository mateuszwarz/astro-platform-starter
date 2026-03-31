from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from decimal import Decimal
from datetime import date
from app.database import get_db
from app.models.invoice import Invoice
from app.models.contractor import Contractor
from app.dependencies import get_current_user
from app.models.user import User
from app.models.invoice import InvoiceItem

router = APIRouter(prefix="/reports", tags=["Raporty"])

MONTH_NAMES = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
               "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"]


VALID_REPORT_TYPES = {"sprzedaz", "zakup"}


@router.get("/vat")
def get_vat_report(
    year: int = Query(default=date.today().year, ge=2020, le=2100),
    month: int = Query(default=date.today().month, ge=1, le=12),
    type: str = Query(default="sprzedaz"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if type not in VALID_REPORT_TYPES:
        raise HTTPException(status_code=400, detail="Nieprawidłowy typ raportu")
    invoices = db.query(Invoice).filter(
        Invoice.is_deleted == False,
        Invoice.type == type,
        Invoice.status.notin_(["szkic", "anulowana"]),
        func.extract("year", Invoice.issue_date) == year,
        func.extract("month", Invoice.issue_date) == month,
    ).order_by(Invoice.issue_date).all()

    rows = []
    totals = {"net_0": 0, "net_5": 0, "net_8": 0, "net_23": 0, "vat_5": 0, "vat_8": 0, "vat_23": 0, "gross": 0}

    for inv in invoices:
        contractor = db.query(Contractor).filter(Contractor.id == inv.contractor_id).first() if inv.contractor_id else None
        items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == inv.id).all()

        row = {
            "number": inv.number,
            "issue_date": inv.issue_date.isoformat(),
            "contractor_name": contractor.name if contractor else "-",
            "contractor_nip": contractor.nip if contractor else "-",
            "net_0": 0, "net_5": 0, "net_8": 0, "net_23": 0,
            "vat_5": 0, "vat_8": 0, "vat_23": 0, "gross": float(inv.gross_amount),
        }
        for item in items:
            net = float(item.net_amount)
            vat = float(item.vat_amount)
            rate = item.vat_rate
            if rate in ("0", "zw", "np"):
                row["net_0"] += net
            elif rate == "5":
                row["net_5"] += net
                row["vat_5"] += vat
            elif rate == "8":
                row["net_8"] += net
                row["vat_8"] += vat
            elif rate == "23":
                row["net_23"] += net
                row["vat_23"] += vat

        for k in ["net_0", "net_5", "net_8", "net_23", "vat_5", "vat_8", "vat_23", "gross"]:
            totals[k] += row[k]

        rows.append(row)

    return {"rows": rows, "totals": totals, "year": year, "month": month, "type": type}


@router.get("/income-costs")
def get_income_costs(
    year: int = Query(default=date.today().year, ge=2020, le=2100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = []
    for month in range(1, 13):
        income = db.query(func.sum(Invoice.net_amount)).filter(
            Invoice.is_deleted == False,
            Invoice.type == "sprzedaz",
            Invoice.status.notin_(["szkic", "anulowana"]),
            func.extract("year", Invoice.issue_date) == year,
            func.extract("month", Invoice.issue_date) == month,
        ).scalar() or 0

        costs = db.query(func.sum(Invoice.net_amount)).filter(
            Invoice.is_deleted == False,
            Invoice.type == "zakup",
            Invoice.status.notin_(["szkic", "anulowana"]),
            func.extract("year", Invoice.issue_date) == year,
            func.extract("month", Invoice.issue_date) == month,
        ).scalar() or 0

        rows.append({
            "month": month,
            "month_name": MONTH_NAMES[month - 1],
            "income": float(income),
            "costs": float(costs),
            "profit": float(income) - float(costs),
        })

    return {"rows": rows, "year": year}


@router.get("/aging")
def get_aging_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    invoices = db.query(Invoice).filter(
        Invoice.is_deleted == False,
        Invoice.status.in_(["oczekuje", "czesciowo_zaplacona", "przeterminowana"]),
    ).all()

    contractors_data = {}
    for inv in invoices:
        if not inv.contractor_id:
            continue
        days = (today - inv.due_date).days if inv.due_date else 0
        key = str(inv.contractor_id)
        if key not in contractors_data:
            contractor = db.query(Contractor).filter(Contractor.id == inv.contractor_id).first()
            contractors_data[key] = {
                "contractor_id": key,
                "contractor_name": contractor.name if contractor else "-",
                "type": inv.type,
                "bucket_0_30": 0,
                "bucket_31_60": 0,
                "bucket_61_90": 0,
                "bucket_90_plus": 0,
                "total": 0,
            }
        amount = float(inv.gross_amount)
        contractors_data[key]["total"] += amount
        if days <= 0:
            contractors_data[key]["bucket_0_30"] += amount
        elif days <= 30:
            contractors_data[key]["bucket_0_30"] += amount
        elif days <= 60:
            contractors_data[key]["bucket_31_60"] += amount
        elif days <= 90:
            contractors_data[key]["bucket_61_90"] += amount
        else:
            contractors_data[key]["bucket_90_plus"] += amount

    rows = sorted(contractors_data.values(), key=lambda x: x["total"], reverse=True)
    return {"rows": rows, "date": today.isoformat()}


@router.get("/contractors")
def get_top_contractors(
    limit: int = Query(default=10, ge=1, le=50),
    year: int = Query(default=date.today().year, ge=2020, le=2100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    results = db.query(
        Invoice.contractor_id,
        func.sum(Invoice.net_amount).label("total_net"),
        func.sum(Invoice.gross_amount).label("total_gross"),
        func.count(Invoice.id).label("invoice_count"),
    ).filter(
        Invoice.is_deleted == False,
        Invoice.status.notin_(["szkic", "anulowana"]),
        func.extract("year", Invoice.issue_date) == year,
        Invoice.contractor_id.isnot(None),
    ).group_by(Invoice.contractor_id).order_by(func.sum(Invoice.gross_amount).desc()).limit(limit).all()

    rows = []
    for r in results:
        contractor = db.query(Contractor).filter(Contractor.id == r.contractor_id).first()
        rows.append({
            "contractor_id": str(r.contractor_id),
            "contractor_name": contractor.name if contractor else "-",
            "contractor_nip": contractor.nip if contractor else "-",
            "total_net": float(r.total_net),
            "total_gross": float(r.total_gross),
            "invoice_count": r.invoice_count,
        })

    return {"rows": rows, "year": year}
