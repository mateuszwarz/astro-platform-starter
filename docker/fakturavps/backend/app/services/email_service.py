"""
Email invoice fetching service.

Connects to IMAP, fetches unread messages, extracts PDF/XML attachments,
parses invoice data, runs deduplication, and creates Invoice records.
"""
import io
import re
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional
from xml.etree import ElementTree as ET

from imapclient import IMAPClient
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.config import settings
from app.models.email_source import EmailSource, EmailMessage, EmailMessageStatus
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatusHistory
from app.models.contractor import Contractor
from app.models.company import Company
from app.services.dedup_service import (
    compute_pdf_hash,
    find_duplicate_by_contractor_nip,
    normalize_invoice_number,
)

logger = logging.getLogger(__name__)


# ── Fernet encryption helpers ─────────────────────────────────────────────────

def _get_fernet() -> Fernet:
    """Derive Fernet key from SECRET_KEY (first 32 bytes base64-urlsafe)."""
    import base64
    raw = settings.SECRET_KEY.encode()[:32]
    # Pad to exactly 32 bytes
    raw = raw.ljust(32, b"0")
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt_password(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


# ── MIME parsing helpers ───────────────────────────────────────────────────────

def _extract_attachments(raw_message: bytes) -> list[dict]:
    """
    Extract attachments from raw MIME message.
    Returns list of {"filename": str, "content_type": str, "data": bytes}.
    """
    import email as email_lib
    msg = email_lib.message_from_bytes(raw_message)
    attachments = []
    for part in msg.walk():
        disposition = part.get_content_disposition()
        if disposition not in ("attachment", "inline"):
            continue
        filename = part.get_filename() or ""
        ct = part.get_content_type() or ""
        data = part.get_payload(decode=True)
        if data:
            attachments.append({"filename": filename, "content_type": ct, "data": data})
    return attachments


def _get_envelope(raw_message: bytes) -> dict:
    """Extract sender, subject, message-id, date from raw MIME."""
    import email as email_lib
    from email.header import decode_header
    msg = email_lib.message_from_bytes(raw_message)

    def _decode_header(h: Optional[str]) -> str:
        if not h:
            return ""
        parts = decode_header(h)
        result = []
        for part, enc in parts:
            if isinstance(part, bytes):
                result.append(part.decode(enc or "utf-8", errors="replace"))
            else:
                result.append(part)
        return "".join(result)

    from_raw = msg.get("From", "")
    # Parse "Name <email>" format
    match = re.match(r"^(.*?)<(.+?)>$", from_raw.strip())
    if match:
        sender_name = _decode_header(match.group(1)).strip().strip('"')
        sender_email = match.group(2).strip()
    else:
        sender_name = ""
        sender_email = from_raw.strip()

    subject = _decode_header(msg.get("Subject", ""))
    message_id = msg.get("Message-ID", "").strip()

    date_str = msg.get("Date", "")
    received_at = None
    if date_str:
        from email.utils import parsedate_to_datetime
        try:
            received_at = parsedate_to_datetime(date_str)
        except Exception:
            pass

    return {
        "sender_email": sender_email[:255],
        "sender_name": sender_name[:255],
        "subject": subject[:1000],
        "message_id": message_id[:500],
        "received_at": received_at,
    }


# ── XML FA(2/3) parser ────────────────────────────────────────────────────────

# KSeF FA(2) / FA(3) namespace URIs
_FA_NAMESPACES = {
    "fa2": "http://crd.gov.pl/wzor/2023/06/29/12648/",
    "fa3": "http://crd.gov.pl/wzor/2024/02/08/12148/",
    "etd": "http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2022/01/05/eD/DefinicjeTypy/",
}


def _parse_fa_xml(xml_bytes: bytes) -> Optional[dict]:
    """
    Parse KSeF FA(2) or FA(3) XML and extract key invoice fields.
    Returns dict or None on failure.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None

    ns_map = {}
    tag = root.tag
    # Detect namespace from root element
    if "12648" in tag:
        ns_map = {"fa": "http://crd.gov.pl/wzor/2023/06/29/12648/"}
    elif "12148" in tag:
        ns_map = {"fa": "http://crd.gov.pl/wzor/2024/02/08/12148/"}
    else:
        # Try generic approach — strip namespace
        ns_match = re.match(r"\{(.+?)\}", tag)
        if ns_match:
            ns_map = {"fa": ns_match.group(1)}
        else:
            return None

    def find(path: str) -> Optional[ET.Element]:
        return root.find(path, ns_map)

    def text(path: str) -> Optional[str]:
        el = find(path)
        return el.text.strip() if el is not None and el.text else None

    result: dict = {}

    # Invoice number
    result["number"] = text("fa:Fa/fa:P_2") or text("fa:FA/fa:P_2")

    # Issue date
    result["issue_date"] = text("fa:Fa/fa:P_1") or text("fa:FA/fa:P_1")

    # Sale date
    result["sale_date"] = text("fa:Fa/fa:P_6") or text("fa:FA/fa:P_6")

    # Seller NIP
    result["seller_nip"] = (
        text("fa:Podmiot1/fa:DaneIdentyfikacyjne/fa:NIP")
        or text("fa:Podmiot1/fa:NIP")
    )

    # Buyer NIP
    result["buyer_nip"] = (
        text("fa:Podmiot2/fa:DaneIdentyfikacyjne/fa:NIP")
        or text("fa:Podmiot2/fa:NIP")
    )

    # Gross amount P_15 = total gross
    gross_str = text("fa:Fa/fa:P_15") or text("fa:FA/fa:P_15")
    if gross_str:
        try:
            result["gross_amount"] = Decimal(gross_str)
        except InvalidOperation:
            pass

    # Net amount P_13_1 (23%), P_13_2 (8%), P_13_3 (5%), P_13_10 (0%)
    net_total = Decimal("0")
    for p in ["P_13_1", "P_13_2", "P_13_3", "P_13_10"]:
        v = text(f"fa:Fa/fa:{p}") or text(f"fa:FA/fa:{p}")
        if v:
            try:
                net_total += Decimal(v)
            except InvalidOperation:
                pass
    if net_total > 0:
        result["net_amount"] = net_total

    # VAT amount P_14_1 + P_14_2 + P_14_3
    vat_total = Decimal("0")
    for p in ["P_14_1", "P_14_2", "P_14_3"]:
        v = text(f"fa:Fa/fa:{p}") or text(f"fa:FA/fa:{p}")
        if v:
            try:
                vat_total += Decimal(v)
            except InvalidOperation:
                pass
    if vat_total > 0:
        result["vat_amount"] = vat_total

    # Seller name
    result["seller_name"] = (
        text("fa:Podmiot1/fa:DaneIdentyfikacyjne/fa:PelnaNazwa")
        or text("fa:Podmiot1/fa:PelnaNazwa")
    )

    return result


# ── Invoice creation from parsed data ────────────────────────────────────────

def _get_or_create_contractor(db: Session, nip: Optional[str], name: Optional[str]) -> Optional[Contractor]:
    """Find contractor by NIP or create a new one."""
    if not nip:
        return None
    contractor = db.query(Contractor).filter(
        Contractor.nip == nip, Contractor.is_deleted == False
    ).first()
    if contractor:
        return contractor
    if name:
        contractor = Contractor(
            id=uuid.uuid4(),
            nip=nip,
            name=name[:255],
            category="dostawca",
            status="aktywny",
        )
        db.add(contractor)
        db.flush()
        return contractor
    return None


def _get_default_company(db: Session) -> Optional[Company]:
    return db.query(Company).filter(Company.is_active == True).first()


def _create_invoice_from_xml(
    db: Session,
    parsed: dict,
    email_message_id: uuid.UUID,
    pdf_hash: Optional[str],
    company_nip: Optional[str],
) -> tuple[Optional[Invoice], bool]:
    """
    Create an invoice from parsed XML data.
    Returns (invoice, is_duplicate).
    company_nip: our company's NIP to determine type (sprzedaz vs zakup).
    """
    gross = parsed.get("gross_amount")
    invoice_number = parsed.get("number")
    seller_nip = parsed.get("seller_nip")
    buyer_nip = parsed.get("buyer_nip")

    # Determine contractor NIP: if we are the buyer → this is zakup, contractor = seller
    inv_type = "zakup"
    contractor_nip = seller_nip
    contractor_name = parsed.get("seller_name")
    if company_nip and seller_nip and seller_nip.replace("-", "") == company_nip.replace("-", ""):
        inv_type = "sprzedaz"
        contractor_nip = buyer_nip
        contractor_name = None

    # Deduplication check
    duplicate = find_duplicate_by_contractor_nip(
        db,
        pdf_hash=pdf_hash,
        contractor_nip=contractor_nip,
        invoice_number=invoice_number,
        gross_amount=gross,
    )
    if duplicate:
        return duplicate, True

    # Get or create contractor
    contractor = _get_or_create_contractor(db, contractor_nip, contractor_name)
    company = _get_default_company(db)

    # Parse dates
    from datetime import date
    def parse_date(s: Optional[str]) -> Optional[date]:
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y%m%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    issue_date = parse_date(parsed.get("issue_date")) or date.today()
    sale_date = parse_date(parsed.get("sale_date"))
    net = parsed.get("net_amount", Decimal("0"))
    vat = parsed.get("vat_amount", Decimal("0"))
    if not gross:
        gross = net + vat

    invoice = Invoice(
        id=uuid.uuid4(),
        number=invoice_number or f"EMAIL/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        type=inv_type,
        contractor_id=contractor.id if contractor else None,
        company_id=company.id if company else None,
        issue_date=issue_date,
        sale_date=sale_date,
        due_date=None,
        status="oczekuje",
        net_amount=net,
        vat_amount=vat,
        gross_amount=gross,
        currency="PLN",
        source="email",
        email_message_id=email_message_id,
        pdf_hash=pdf_hash,
    )
    db.add(invoice)
    db.flush()

    db.add(InvoiceStatusHistory(
        id=uuid.uuid4(),
        invoice_id=invoice.id,
        old_status=None,
        new_status="oczekuje",
        source="email",
        reason="Zaimportowana z maila",
    ))

    return invoice, False


# ── Main fetch function ───────────────────────────────────────────────────────

def fetch_emails_for_source(db: Session, source: EmailSource) -> dict:
    """
    Connect to IMAP, fetch unread messages, process attachments.
    Returns stats dict: {fetched, created, duplicates, errors}.
    """
    stats = {"fetched": 0, "created": 0, "duplicates": 0, "errors": 0}

    try:
        password = decrypt_password(source.encrypted_password)
    except Exception as e:
        logger.error("Failed to decrypt password for source %s: %s", source.id, e)
        source.last_error = f"Błąd odszyfrowania hasła: {e}"
        db.commit()
        return stats

    # Get our company NIP for sprzedaz/zakup determination
    company = _get_default_company(db)
    company_nip = company.nip if company else None

    try:
        with IMAPClient(source.host, port=source.port, ssl=source.use_ssl) as client:
            client.login(source.username, password)
            client.select_folder(source.folder)

            # Fetch UNSEEN messages
            message_ids = client.search(["UNSEEN"])
            logger.info("Source %s: found %d unseen messages", source.id, len(message_ids))

            for uid in message_ids:
                try:
                    _process_single_message(
                        db, client, uid, source, company_nip, stats
                    )
                except Exception as e:
                    logger.error("Error processing message %s: %s", uid, e)
                    stats["errors"] += 1

            source.last_checked_at = datetime.now(timezone.utc)
            source.last_error = None
            db.commit()

    except Exception as e:
        logger.error("IMAP connection error for source %s: %s", source.id, e)
        source.last_error = str(e)[:500]
        source.last_checked_at = datetime.now(timezone.utc)
        db.commit()
        stats["errors"] += 1

    return stats


def _process_single_message(
    db: Session,
    client: IMAPClient,
    uid: int,
    source: EmailSource,
    company_nip: Optional[str],
    stats: dict,
) -> None:
    """Fetch and process a single IMAP message."""
    raw_data = client.fetch([uid], ["RFC822"])
    raw_message = raw_data[uid][b"RFC822"]

    envelope = _get_envelope(raw_message)
    message_id_str = envelope["message_id"] or f"uid:{uid}@{source.host}"

    # Skip if already processed
    existing_msg = db.query(EmailMessage).filter(
        EmailMessage.message_id == message_id_str
    ).first()
    if existing_msg:
        logger.debug("Message %s already processed, skipping", message_id_str)
        return

    # Apply sender filter if configured
    if source.filter_senders:
        sender = envelope["sender_email"].lower()
        allowed = [p.lower() for p in source.filter_senders]
        if not any(a in sender for a in allowed):
            logger.debug("Message %s sender %s not in filter, skipping", message_id_str, sender)
            return

    attachments = _extract_attachments(raw_message)
    invoice_attachments = [
        a for a in attachments
        if a["filename"].lower().endswith((".pdf", ".xml"))
        or a["content_type"] in ("application/pdf", "text/xml", "application/xml")
    ]

    email_msg = EmailMessage(
        id=uuid.uuid4(),
        email_source_id=source.id,
        message_id=message_id_str,
        sender_email=envelope["sender_email"],
        sender_name=envelope["sender_name"],
        subject=envelope["subject"],
        received_at=envelope["received_at"],
        attachment_count=len(invoice_attachments),
        status=EmailMessageStatus.pending.value,
    )
    db.add(email_msg)
    db.flush()
    stats["fetched"] += 1

    created = 0
    duplicates = 0
    errors_in_msg = 0

    for attachment in invoice_attachments:
        try:
            data = attachment["data"]
            filename = attachment["filename"].lower()

            pdf_hash = None
            parsed = None

            if filename.endswith(".pdf"):
                pdf_hash = compute_pdf_hash(data)
                # No OCR here — just hash for dedup; XML is preferred
                # Mark as needing manual review if no XML companion
                continue  # PDF-only: stored hash but skip auto-create without XML

            elif filename.endswith(".xml"):
                parsed = _parse_fa_xml(data)

            if not parsed:
                continue

            invoice, is_dup = _create_invoice_from_xml(
                db, parsed, email_msg.id, pdf_hash, company_nip
            )
            if is_dup:
                duplicates += 1
            else:
                created += 1

        except Exception as e:
            logger.error("Error processing attachment %s: %s", attachment["filename"], e)
            errors_in_msg += 1

    # Now handle PDF attachments for dedup purposes — pair with created invoices
    for attachment in invoice_attachments:
        if attachment["filename"].lower().endswith(".pdf"):
            pdf_hash = compute_pdf_hash(attachment["data"])
            # If an invoice was just created from XML companion, attach hash
            # Find recently created invoice from this email
            recent_inv = db.query(Invoice).filter(
                Invoice.email_message_id == email_msg.id,
                Invoice.pdf_hash.is_(None),
            ).first()
            if recent_inv:
                recent_inv.pdf_hash = pdf_hash

    email_msg.invoices_created = created
    email_msg.invoices_duplicated = duplicates
    email_msg.processed_at = datetime.now(timezone.utc)

    if errors_in_msg > 0 and created == 0 and duplicates == 0:
        email_msg.status = EmailMessageStatus.error.value
        email_msg.error_message = f"{errors_in_msg} błąd(y) przetwarzania załączników"
    elif duplicates > 0 and created == 0:
        email_msg.status = EmailMessageStatus.duplicate.value
    elif len(invoice_attachments) == 0:
        email_msg.status = EmailMessageStatus.skipped.value
    else:
        email_msg.status = EmailMessageStatus.processed.value

    # Mark message as SEEN in IMAP
    client.set_flags([uid], [b"\\Seen"])

    # Apply processed label if configured
    if source.processed_label:
        try:
            client.copy([uid], source.processed_label)
        except Exception:
            pass

    db.flush()


def test_imap_connection(host: str, port: int, username: str, password: str, use_ssl: bool, folder: str) -> dict:
    """Test IMAP connection. Returns {"ok": bool, "error": Optional[str], "folders": list}."""
    try:
        with IMAPClient(host, port=port, ssl=use_ssl) as client:
            client.login(username, password)
            folders = [str(f[2]) for f in client.list_folders()]
            client.select_folder(folder)
            unseen = client.search(["UNSEEN"])
            return {"ok": True, "error": None, "folders": folders, "unseen_count": len(unseen)}
    except Exception as e:
        return {"ok": False, "error": str(e), "folders": [], "unseen_count": 0}
