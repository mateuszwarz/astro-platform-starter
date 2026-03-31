"""
OCR Service – extract text from uploaded PDF or image files
and parse Polish invoice fields for form pre-filling.
"""
import io
import re
import os
import uuid
import hashlib
from datetime import date
from typing import Optional

UPLOAD_DIR = "/app/uploads"


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_uploaded_file(file_bytes: bytes, original_filename: str) -> str:
    """Save uploaded file to disk; return relative filename (UUID-based)."""
    _ensure_upload_dir()
    ext = os.path.splitext(original_filename)[1].lower() or ".bin"
    stored_name = f"{uuid.uuid4()}{ext}"
    path = os.path.join(UPLOAD_DIR, stored_name)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return stored_name


def load_attachment(stored_name: str) -> Optional[bytes]:
    """Load attachment bytes from disk."""
    path = os.path.join(UPLOAD_DIR, stored_name)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        return ""


def _extract_text_from_image(file_bytes: bytes) -> str:
    """Extract text from image using pytesseract."""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img, lang="pol+eng")
    except Exception:
        return ""


def extract_text(file_bytes: bytes, original_filename: str) -> str:
    """Dispatch to appropriate extractor based on file extension."""
    ext = os.path.splitext(original_filename)[1].lower()
    if ext == ".pdf":
        text = _extract_text_from_pdf(file_bytes)
        if not text.strip():
            # PDF may be scanned – try OCR on first page image
            text = _ocr_pdf_as_image(file_bytes)
        return text
    return _extract_text_from_image(file_bytes)


def _ocr_pdf_as_image(file_bytes: bytes) -> str:
    """Convert first PDF page to image and run OCR (fallback for scanned PDFs)."""
    try:
        import pdfplumber
        import pytesseract
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            if not pdf.pages:
                return ""
            img = pdf.pages[0].to_image(resolution=200).original
            return pytesseract.image_to_string(img, lang="pol+eng")
    except Exception:
        return ""


# ── Polish invoice field parsers ──────────────────────────────────────────────

def _find_nip(text: str) -> Optional[str]:
    patterns = [
        r"NIP[:\s]*(\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})",
        r"NIP[:\s]*(\d{10})",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return re.sub(r"[^0-9]", "", m.group(1))
    return None


def _find_invoice_number(text: str) -> Optional[str]:
    patterns = [
        r"(?:Nr faktury|Faktura VAT|Numer faktury|Nr)[:\s#]*([A-Z0-9/\-]{3,30})",
        r"(FV/\d{4}/\d+)",
        r"(FZ/\d{4}/\d+)",
        r"(FK/\d{4}/\d+)",
        r"(FA/\d{4}/\d+)",
        r"(PR/\d{4}/\d+)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _parse_polish_date(raw: str) -> Optional[str]:
    """Convert DD.MM.YYYY or YYYY-MM-DD to YYYY-MM-DD."""
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return raw
    return None


def _find_date(text: str, keywords: list[str]) -> Optional[str]:
    for kw in keywords:
        pattern = rf"{kw}[:\s]*(\d{{2}}\.\d{{2}}\.\d{{4}}|\d{{4}}-\d{{2}}-\d{{2}})"
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return _parse_polish_date(m.group(1))
    return None


def _find_amount(text: str, keywords: list[str]) -> Optional[float]:
    for kw in keywords:
        pattern = rf"{kw}[:\s]*([\d\s]+[.,]\d{{2}})"
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip().replace(" ", "").replace(",", ".")
            try:
                return float(raw)
            except ValueError:
                pass
    return None


def _find_contractor_name(text: str) -> Optional[str]:
    """Try to extract buyer/seller name from invoice text."""
    for kw in ["Nabywca:", "Kupujący:", "Odbiorca:"]:
        idx = text.lower().find(kw.lower())
        if idx != -1:
            snippet = text[idx + len(kw):idx + len(kw) + 80]
            line = snippet.strip().split("\n")[0].strip()
            if line:
                return line[:100]
    return None


def parse_invoice_fields(text: str) -> dict:
    """
    Parse extracted text and return a dict with pre-filled invoice fields.
    All values are best-effort; frontend should allow user correction.
    """
    today = date.today().isoformat()

    nip = _find_nip(text)
    number = _find_invoice_number(text)
    issue_date = _find_date(text, ["Data wystawienia", "Data faktury", "Wystawiono", "Data"]) or today
    sale_date = _find_date(text, ["Data sprzedaży", "Data dostawy", "Sprzedaż"])
    due_date = _find_date(text, ["Termin płatności", "Płatność do", "Zapłata do"])
    gross_amount = _find_amount(text, ["Do zapłaty", "Razem brutto", "Suma brutto", "Kwota brutto", "Łącznie"])
    contractor_name = _find_contractor_name(text)

    # Detect document type
    detected_type = "zakup"
    if re.search(r"FAKTURA\s+VAT\s+SPRZEDAŻ", text, re.IGNORECASE):
        detected_type = "sprzedaz"
    elif re.search(r"PARAGON", text, re.IGNORECASE):
        detected_type = "paragon"
    elif re.search(r"PROFORMA|PRO.?FORMA", text, re.IGNORECASE):
        detected_type = "proforma"
    elif re.search(r"KORYGUJ", text, re.IGNORECASE):
        detected_type = "korekta"
    elif re.search(r"ZALICZK", text, re.IGNORECASE):
        detected_type = "zaliczkowa"

    return {
        "detected_type": detected_type,
        "number": number,
        "issue_date": issue_date,
        "sale_date": sale_date,
        "due_date": due_date,
        "gross_amount": gross_amount,
        "contractor_nip": nip,
        "contractor_name": contractor_name,
        "raw_text_preview": text[:500] if text else "",
    }
