from app.celery_app import celery_app
from datetime import date
import uuid


@celery_app.task(name="app.tasks.scheduled.mark_overdue_invoices")
def mark_overdue_invoices():
    from app.database import SessionLocal
    from app.models.invoice import Invoice, InvoiceStatusHistory
    db = SessionLocal()
    try:
        today = date.today()
        invoices = db.query(Invoice).filter(
            Invoice.due_date < today,
            Invoice.status.in_(["oczekuje", "czesciowo_zaplacona"]),
            Invoice.is_deleted == False
        ).all()

        count = 0
        for invoice in invoices:
            old_status = invoice.status
            invoice.status = "przeterminowana"
            history = InvoiceStatusHistory(
                id=uuid.uuid4(),
                invoice_id=invoice.id,
                old_status=old_status,
                new_status="przeterminowana",
                changed_by_id=None,
                source="system",
                reason="Automatyczne oznaczenie - minął termin płatności"
            )
            db.add(history)
            count += 1

        db.commit()
        return {"marked_overdue": count, "date": str(today)}
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
