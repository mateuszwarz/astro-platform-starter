import uuid
import random
import string
from datetime import datetime


def generate_ksef_number() -> str:
    year = datetime.now().year
    seq = ''.join(random.choices(string.digits, k=10))
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{year}{seq}{suffix}"


def send_invoice(invoice_data: dict) -> dict:
    reference = str(uuid.uuid4())
    return {
        "ksef_reference": reference,
        "status": "processing",
        "timestamp": datetime.utcnow().isoformat()
    }


def check_status(reference: str) -> dict:
    ksef_number = generate_ksef_number()
    upo_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<UPO xmlns="http://ksef.mf.gov.pl/schema/gtw/svc/online/types/v2">
  <NumerKSeF>{ksef_number}</NumerKSeF>
  <SkrotSHA>{reference[:16]}</SkrotSHA>
  <DataCzasUtworzenia>{datetime.utcnow().isoformat()}</DataCzasUtworzenia>
</UPO>"""
    return {
        "status": "accepted",
        "ksef_number": ksef_number,
        "upo_xml": upo_xml
    }
