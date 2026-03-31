from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date, datetime
from decimal import Decimal
from app.database import get_db
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    first_of_month = date(today.year, today.month, 1)

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

    overdue_count = db.query(func.count(Invoice.id)).filter(
        Invoice.is_deleted == False,
        Invoice.status == "przeterminowana"
    ).scalar() or 0

    overdue_amount = db.query(func.sum(Invoice.gross_amount)).filter(
        Invoice.is_deleted == False,
        Invoice.status == "przeterminowana"
    ).scalar() or 0

    paid_this_month = db.query(func.sum(Payment.amount)).filter(
        Payment.payment_date >= first_of_month,
        Payment.payment_date <= today
    ).scalar() or 0

    week_end = date(today.year, today.month, min(today.day + 7, 28))
    pending_this_week_q = db.query(Invoice).filter(
        Invoice.is_deleted == False,
        Invoice.due_date >= today,
        Invoice.due_date <= week_end,
        Invoice.status.in_(["oczekuje", "czesciowo_zaplacona"])
    ).limit(5).all()

    recent_invoices_q = db.query(Invoice).filter(
        Invoice.is_deleted == False
    ).order_by(Invoice.created_at.desc()).limit(10).all()

    monthly_revenue = []
    for month in range(1, 13):
        revenue = db.query(func.sum(Invoice.net_amount)).filter(
            Invoice.is_deleted == False,
            Invoice.type == "sprzedaz",
            Invoice.status.in_(["zaplacona", "oczekuje", "czesciowo_zaplacona", "zaakceptowana_ksef"]),
            func.extract("year", Invoice.issue_date) == today.year,
            func.extract("month", Invoice.issue_date) == month
        ).scalar() or 0

        costs = db.query(func.sum(Invoice.net_amount)).filter(
            Invoice.is_deleted == False,
            Invoice.type == "zakup",
            Invoice.status.in_(["zaplacona", "oczekuje", "czesciowo_zaplacona"]),
            func.extract("year", Invoice.issue_date) == today.year,
            func.extract("month", Invoice.issue_date) == month
        ).scalar() or 0

        monthly_revenue.append({
            "month": month,
            "revenue": float(revenue),
            "costs": float(costs),
        })

    pending_this_week = []
    for inv in pending_this_week_q:
        pending_this_week.append({
            "id": str(inv.id),
            "number": inv.number,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "gross_amount": float(inv.gross_amount),
            "status": inv.status,
        })

    recent_invoices = []
    for inv in recent_invoices_q:
        recent_invoices.append({
            "id": str(inv.id),
            "number": inv.number,
            "type": inv.type,
            "status": inv.status,
            "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
            "gross_amount": float(inv.gross_amount),
        })

    return {
        "receivables_total": float(receivables),
        "payables_total": float(payables),
        "overdue_count": overdue_count,
        "overdue_amount": float(overdue_amount),
        "paid_this_month": float(paid_this_month),
        "pending_this_week": pending_this_week,
        "recent_invoices": recent_invoices,
        "monthly_revenue": monthly_revenue,
        "ksef_status": "connected",
    }
