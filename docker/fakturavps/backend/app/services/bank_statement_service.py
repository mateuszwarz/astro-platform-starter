"""
Bank Statement Service
======================
Parsowanie wyciągów bankowych (CSV / MT940) i dopasowywanie transakcji do faktur.

Obsługiwane formaty CSV polskich banków:
 - PKO BP  (średnik, nagłówek na 1 wierszu, kolumny standardowe)
 - ING      (średnik / przecinek)
 - mBank    (csv po kliknięciu "Pobierz wyciąg")
 - Pekao    (ogólny CSV)
 - Generyczny CSV (auto-detect kolumn)

Format MT940 (SWIFT) – używany przez większość banków dla rozliczeń B2B.
"""
from __future__ import annotations

import io
import re
import os
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

import chardet

UPLOAD_DIR = "/app/uploads"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ensure_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_statement_file(file_bytes: bytes, original_filename: str) -> str:
    _ensure_dir()
    ext = os.path.splitext(original_filename)[1].lower() or ".dat"
    stored = f"stmt_{uuid.uuid4()}{ext}"
    with open(os.path.join(UPLOAD_DIR, stored), "wb") as f:
        f.write(file_bytes)
    return stored


def _decode(file_bytes: bytes) -> str:
    detected = chardet.detect(file_bytes)
    enc = detected.get("encoding") or "utf-8"
    try:
        return file_bytes.decode(enc)
    except Exception:
        return file_bytes.decode("utf-8", errors="replace")


def _parse_amount(raw: str) -> Optional[Decimal]:
    """Convert '1 234,56' or '1234.56' or '-1234,56' to Decimal."""
    if not raw:
        return None
    s = raw.strip().replace(" ", "").replace("\xa0", "")
    # Polish format: comma as decimal separator
    if "," in s and "." in s:
        # e.g. 1.234,56
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _parse_date(raw: str) -> Optional[date]:
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%Y%m%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


# ── Row dataclass ─────────────────────────────────────────────────────────────

class RawTransaction:
    __slots__ = (
        "transaction_date", "booking_date", "amount", "currency",
        "description", "counterparty_name", "counterparty_account", "reference",
    )

    def __init__(self):
        self.transaction_date: Optional[date] = None
        self.booking_date: Optional[date] = None
        self.amount: Optional[Decimal] = None
        self.currency: str = "PLN"
        self.description: str = ""
        self.counterparty_name: str = ""
        self.counterparty_account: str = ""
        self.reference: str = ""


# ── CSV parsers ───────────────────────────────────────────────────────────────

def _detect_separator(text: str) -> str:
    first_line = text.split("\n")[0]
    return ";" if first_line.count(";") >= first_line.count(",") else ","


def _csv_rows(text: str) -> list[list[str]]:
    sep = _detect_separator(text)
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append([c.strip().strip('"') for c in line.split(sep)])
    return rows


def _header_index(headers: list[str], candidates: list[str]) -> int:
    hl = [h.lower() for h in headers]
    for c in candidates:
        if c.lower() in hl:
            return hl.index(c.lower())
    return -1


def _parse_csv_generic(text: str) -> tuple[list[RawTransaction], str]:
    """Auto-detect column layout from CSV headers."""
    rows = _csv_rows(text)
    if len(rows) < 2:
        return [], "generic"

    # Find header row (first row with at least 3 non-empty cells)
    header_row_idx = 0
    for i, row in enumerate(rows[:5]):
        if len([c for c in row if c]) >= 3:
            header_row_idx = i
            break

    headers = rows[header_row_idx]
    data_rows = rows[header_row_idx + 1:]

    # Map known header names
    date_col = _header_index(headers, [
        "data operacji", "data transakcji", "data ksiegowania",
        "data", "date", "transaction date", "data waluty",
    ])
    booking_col = _header_index(headers, [
        "data ksiegowania", "data rozliczenia", "booking date",
    ])
    amount_col = _header_index(headers, [
        "kwota", "amount", "kwota operacji", "kwota transakcji",
        "wartość", "wartosc",
    ])
    credit_col = _header_index(headers, ["uznanie", "wpływ", "credit", "wplyw"])
    debit_col = _header_index(headers, ["obciążenie", "obciazenie", "debit", "wypływ"])
    desc_col = _header_index(headers, [
        "opis transakcji", "tytuł", "tytul", "opis", "title",
        "description", "szczegóły", "szczegoly", "tresc",
    ])
    counterparty_col = _header_index(headers, [
        "nadawca / odbiorca", "odbiorca", "nadawca", "kontrahent",
        "counterparty", "nazwa kontrahenta",
    ])
    account_col = _header_index(headers, [
        "numer rachunku", "rachunek kontrahenta", "account",
        "nr rachunku", "counterparty account",
    ])
    ref_col = _header_index(headers, [
        "numer referencyjny", "reference", "nr ref", "id transakcji",
    ])

    transactions: list[RawTransaction] = []
    for row in data_rows:
        if not row or all(c == "" for c in row):
            continue
        t = RawTransaction()

        def get(idx: int) -> str:
            if idx < 0 or idx >= len(row):
                return ""
            return row[idx]

        t.transaction_date = _parse_date(get(date_col)) if date_col >= 0 else None
        if booking_col >= 0:
            t.booking_date = _parse_date(get(booking_col))
        if not t.transaction_date:
            continue

        # Amount: try single column first, then credit/debit
        if amount_col >= 0:
            t.amount = _parse_amount(get(amount_col))
        elif credit_col >= 0 and debit_col >= 0:
            credit = _parse_amount(get(credit_col))
            debit = _parse_amount(get(debit_col))
            if credit and credit > 0:
                t.amount = credit
            elif debit and debit > 0:
                t.amount = -debit
        if t.amount is None:
            continue

        t.description = get(desc_col) if desc_col >= 0 else ""
        t.counterparty_name = get(counterparty_col) if counterparty_col >= 0 else ""
        t.counterparty_account = get(account_col) if account_col >= 0 else ""
        t.reference = get(ref_col) if ref_col >= 0 else ""
        transactions.append(t)

    return transactions, "csv_generic"


def _parse_mt940(text: str) -> tuple[list[RawTransaction], str]:
    """Parse MT940 (SWIFT) bank statement format."""
    try:
        import mt940
        transactions: list[RawTransaction] = []
        data = mt940.models.Transactions()
        data.parse(text.encode("utf-8") if isinstance(text, str) else text)

        for t_mt in data.data.get("transactions", []):
            t = RawTransaction()
            d = t_mt.data
            t.transaction_date = d.get("date")
            t.booking_date = d.get("entry_date")
            raw_amount = d.get("amount")
            if raw_amount is not None:
                t.amount = Decimal(str(raw_amount.amount))
            else:
                continue
            t.currency = str(d.get("currency", "PLN"))
            details = d.get("transaction_details", "") or ""
            t.description = details
            # Try to extract counterparty from details
            m = re.search(r"(?:Nadawca|Odbiorca|Name)[:\s]+([^\n/]{3,60})", details, re.I)
            if m:
                t.counterparty_name = m.group(1).strip()
            t.reference = str(d.get("id", ""))
            transactions.append(t)

        return transactions, "mt940"
    except Exception:
        return [], "mt940"


# ── Main parser ────────────────────────────────────────────────────────────────

def parse_bank_statement(file_bytes: bytes, filename: str) -> tuple[list[RawTransaction], str]:
    """
    Detect format and parse bank statement.
    Returns (transactions, detected_format).
    """
    ext = os.path.splitext(filename)[1].lower()
    text = _decode(file_bytes)

    if ext in (".sta", ".940", ".mt940") or text.strip().startswith(":20:"):
        txs, fmt = _parse_mt940(text)
        if txs:
            return txs, fmt

    # Fallback to CSV
    txs, fmt = _parse_csv_generic(text)
    return txs, fmt


# ── Invoice matching ──────────────────────────────────────────────────────────

def _normalize_nip(text: str) -> list[str]:
    """Extract all NIP-like sequences from text."""
    return re.findall(r"\b\d{10}\b|\b\d{3}[-\s]\d{3}[-\s]\d{2}[-\s]\d{2}\b", text)


def _normalize_str(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def score_match(transaction: RawTransaction, invoice, contractor) -> int:
    """
    Calculate match confidence (0–100) between a bank transaction and an invoice.
    """
    score = 0
    if transaction.amount is None or invoice.gross_amount is None:
        return 0

    # Amount must match within ±0.02 PLN
    t_amount = abs(transaction.amount)
    i_amount = Decimal(str(invoice.gross_amount))
    if abs(t_amount - i_amount) > Decimal("0.02"):
        return 0

    score += 50  # Amount match is the primary criterion

    # Date proximity: invoice issue/due date vs transaction date
    if transaction.transaction_date and invoice.due_date:
        delta = abs((transaction.transaction_date - invoice.due_date).days)
        if delta <= 3:
            score += 20
        elif delta <= 14:
            score += 10
        elif delta <= 60:
            score += 5
    elif transaction.transaction_date and invoice.issue_date:
        delta = abs((transaction.transaction_date - invoice.issue_date).days)
        if delta <= 7:
            score += 15
        elif delta <= 30:
            score += 8

    # Contractor match in description
    desc_all = " ".join([
        transaction.description or "",
        transaction.counterparty_name or "",
        transaction.counterparty_account or "",
    ])

    if contractor:
        # NIP match
        desc_nips = [re.sub(r"[^0-9]", "", n) for n in _normalize_nip(desc_all)]
        if contractor.nip and re.sub(r"[^0-9]", "", contractor.nip or "") in desc_nips:
            score += 25

        # Name match (partial)
        c_words = [w for w in _normalize_str(contractor.name or "").split() if len(w) >= 4]
        if c_words:
            desc_norm = _normalize_str(desc_all)
            matched_words = sum(1 for w in c_words if w in desc_norm)
            if matched_words >= 2:
                score += 15
            elif matched_words == 1:
                score += 7

    # Invoice number match in description
    if invoice.number:
        num_clean = _normalize_str(invoice.number)
        if num_clean in _normalize_str(desc_all):
            score += 20

    return min(score, 100)


def find_matches(transaction: RawTransaction, invoices_with_contractors: list) -> list[dict]:
    """
    For a given transaction, find candidate invoice matches sorted by confidence.
    invoices_with_contractors: list of (invoice, contractor) tuples
    """
    candidates = []
    for invoice, contractor in invoices_with_contractors:
        conf = score_match(transaction, invoice, contractor)
        if conf >= 50:  # Minimum threshold
            candidates.append({
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.number,
                "invoice_gross": float(invoice.gross_amount),
                "invoice_status": invoice.status,
                "invoice_type": invoice.type,
                "contractor_name": contractor.name if contractor else None,
                "contractor_nip": contractor.nip if contractor else None,
                "confidence": conf,
            })
    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    return candidates[:5]  # Top 5 matches
