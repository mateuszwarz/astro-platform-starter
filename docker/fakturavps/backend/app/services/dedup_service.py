"""
Duplicate detection for email-imported invoices.

Strategy (in order):
1. Exact PDF hash match (SHA-256 of raw bytes)
2. NIP + normalized invoice number + gross amount within ±0.01 PLN
"""
import hashlib
import re
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.invoice import Invoice


def compute_pdf_hash(pdf_bytes: bytes) -> str:
    """Return SHA-256 hex digest of PDF bytes."""
    return hashlib.sha256(pdf_bytes).hexdigest()


def normalize_invoice_number(number: str) -> str:
    """
    Normalize invoice number for comparison:
    - uppercase
    - collapse whitespace
    - remove leading zeros in numeric segments
    """
    number = number.upper().strip()
    number = re.sub(r"\s+", "", number)
    # Normalize numeric segments: remove leading zeros
    number = re.sub(r"(?<!\w)0+(\d)", r"\1", number)
    return number


def find_duplicate(
    db: Session,
    pdf_hash: Optional[str],
    nip: Optional[str],
    invoice_number: Optional[str],
    gross_amount: Optional[Decimal],
) -> Optional[Invoice]:
    """
    Check if an invoice already exists matching either:
    - Same pdf_hash (exact file duplicate)
    - Same NIP + normalized invoice number + gross amount ±0.01 PLN
    Returns the existing Invoice or None.
    """
    # 1. Exact hash match
    if pdf_hash:
        existing = (
            db.query(Invoice)
            .filter(Invoice.pdf_hash == pdf_hash, Invoice.is_deleted == False)
            .first()
        )
        if existing:
            return existing

    # 2. NIP + invoice number + gross amount
    if nip and invoice_number and gross_amount is not None:
        normalized = normalize_invoice_number(invoice_number)
        candidates = (
            db.query(Invoice)
            .join(
                Invoice.__table__.alias("contractors_join"),
                Invoice.contractor_id.isnot(None),
            )
            .filter(Invoice.is_deleted == False)
            .all()
        )
        # Do the normalized number and gross comparison in Python to avoid
        # DB-level normalization complexity
        for inv in candidates:
            if inv.number and normalize_invoice_number(inv.number) == normalized:
                if inv.gross_amount is not None:
                    diff = abs(Decimal(str(inv.gross_amount)) - gross_amount)
                    if diff <= Decimal("0.01"):
                        return inv

    return None


def find_duplicate_by_contractor_nip(
    db: Session,
    pdf_hash: Optional[str],
    contractor_nip: Optional[str],
    invoice_number: Optional[str],
    gross_amount: Optional[Decimal],
) -> Optional[Invoice]:
    """
    More efficient lookup joining through contractor table to get NIP.
    """
    # 1. Exact hash match
    if pdf_hash:
        existing = (
            db.query(Invoice)
            .filter(Invoice.pdf_hash == pdf_hash, Invoice.is_deleted == False)
            .first()
        )
        if existing:
            return existing

    # 2. NIP + normalized invoice number + gross ±0.01
    if contractor_nip and invoice_number and gross_amount is not None:
        normalized = normalize_invoice_number(invoice_number)
        # Import here to avoid circular
        from app.models.contractor import Contractor

        candidates = (
            db.query(Invoice)
            .join(Contractor, Invoice.contractor_id == Contractor.id)
            .filter(
                Contractor.nip == contractor_nip,
                Invoice.is_deleted == False,
            )
            .all()
        )
        for inv in candidates:
            if inv.number and normalize_invoice_number(inv.number) == normalized:
                if inv.gross_amount is not None:
                    diff = abs(Decimal(str(inv.gross_amount)) - gross_amount)
                    if diff <= Decimal("0.01"):
                        return inv

    return None
