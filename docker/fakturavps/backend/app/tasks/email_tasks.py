"""
Celery task: fetch invoices from all active email sources every 5 minutes.
"""
import logging
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.email_source import EmailSource
from app.services.email_service import fetch_emails_for_source

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.email_tasks.fetch_all_email_sources", bind=True, max_retries=3)
def fetch_all_email_sources(self):
    """Fetch invoices from all active IMAP sources."""
    db = SessionLocal()
    try:
        sources = db.query(EmailSource).filter(EmailSource.is_active == True).all()
        total_stats = {"fetched": 0, "created": 0, "duplicates": 0, "errors": 0}
        for source in sources:
            try:
                stats = fetch_emails_for_source(db, source)
                for k in total_stats:
                    total_stats[k] += stats.get(k, 0)
            except Exception as e:
                logger.error("Failed to process email source %s: %s", source.id, e)
                total_stats["errors"] += 1
        logger.info("Email fetch complete: %s", total_stats)
        return total_stats
    finally:
        db.close()


@celery_app.task(name="app.tasks.email_tasks.fetch_single_email_source")
def fetch_single_email_source(source_id: str):
    """Fetch invoices from a single email source (on-demand trigger)."""
    db = SessionLocal()
    try:
        source = db.query(EmailSource).filter(
            EmailSource.id == source_id,
            EmailSource.is_active == True,
        ).first()
        if not source:
            return {"error": f"Source {source_id} not found or inactive"}
        stats = fetch_emails_for_source(db, source)
        logger.info("On-demand fetch for source %s: %s", source_id, stats)
        return stats
    finally:
        db.close()
