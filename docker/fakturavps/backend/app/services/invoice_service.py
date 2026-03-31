from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatusHistory
from app.models.payment import Payment
import uuid


VAT_RATES = {
    "23": Decimal("0.23"),
    "8": Decimal("0.08"),
    "5": Decimal("0.05"),
    "0": Decimal("0.00"),
    "zw": Decimal("0.00"),
    "np": Decimal("0.00"),
}


def calculate_item_amounts(quantity: Decimal, unit_price_net: Decimal, vat_rate_str: str):
    rate = VAT_RATES.get(vat_rate_str, Decimal("0.23"))
    net = (quantity * unit_price_net).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    vat = (net * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    gross = net + vat
    return net, vat, gross


def recalculate_invoice_totals(items):
    total_net = Decimal("0")
    total_vat = Decimal("0")
    total_gross = Decimal("0")
    for item in items:
        total_net += Decimal(str(item.net_amount))
        total_vat += Decimal(str(item.vat_amount))
        total_gross += Decimal(str(item.gross_amount))
    return total_net, total_vat, total_gross


def generate_invoice_number(db: Session, invoice_type: str, year: int) -> str:
    prefix = "FV"
    if invoice_type == "zakup":
        prefix = "FZ"
    elif invoice_type == "korekta":
        prefix = "FK"
    elif invoice_type == "proforma":
        prefix = "FP"
    elif invoice_type == "zaliczkowa":
        prefix = "FA"
    elif invoice_type == "paragon":
        prefix = "PR"

    year_str = str(year)
    count = db.query(Invoice).filter(
        Invoice.number.like(f"{prefix}/{year_str}/%"),
        Invoice.is_deleted == False
    ).count()
    return f"{prefix}/{year_str}/{str(count + 1).zfill(3)}"


def update_invoice_payment_status(db: Session, invoice: Invoice, current_user_id=None):
    payments = db.query(Payment).filter(Payment.invoice_id == invoice.id).all()
    total_paid = sum(Decimal(str(p.amount)) for p in payments)
    gross = Decimal(str(invoice.gross_amount))

    old_status = invoice.status

    if total_paid <= 0:
        new_status = "oczekuje"
    elif total_paid >= gross:
        new_status = "zaplacona"
    else:
        new_status = "czesciowo_zaplacona"

    if new_status != old_status and old_status not in ("anulowana", "szkic", "w_ksef"):
        invoice.status = new_status
        history = InvoiceStatusHistory(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            old_status=old_status,
            new_status=new_status,
            changed_by_id=current_user_id,
            source="system",
            reason="Automatyczna aktualizacja po rejestracji płatności"
        )
        db.add(history)
        db.flush()
