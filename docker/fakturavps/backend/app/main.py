from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.database import Base, engine, SessionLocal
from app.models import User, Company, Contractor, Invoice, AuditLog
from app.models.invoice import InvoiceItem, InvoiceStatusHistory
from app.security import hash_password
import os
from app.routers import auth, users, invoices, contractors, payments, reports, dashboard, ksef, email_sources, bank_statements


# ── Security Headers Middleware ───────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # CSP — dozwolone tylko własne zasoby
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        # Nagłówek "server" jest usuwany przez flagę --no-server-header w uvicorn
        # (nie można go usunąć z poziomu middleware ASGI)
        return response


# ── Rate Limiter (globalny) ───────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

_env = os.environ.get("APP_ENV", "production")
app = FastAPI(
    title="FakturaVPS API",
    description="System fakturowania FakturaVPS",
    version="1.0.0",
    docs_url="/docs" if _env == "development" else None,
    redoc_url="/redoc" if _env == "development" else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)

_cors_raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "message": "Błąd walidacji danych"},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"message": "Zasób nie istnieje"},
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Błąd serwera"},
    )


API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(invoices.router, prefix=API_PREFIX)
app.include_router(contractors.router, prefix=API_PREFIX)
app.include_router(payments.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(ksef.router, prefix=API_PREFIX)
app.include_router(email_sources.router, prefix=API_PREFIX)
app.include_router(bank_statements.router, prefix=API_PREFIX)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "FakturaVPS API"}


def seed_data():
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return

        company = Company(
            id=uuid.uuid4(),
            name="FakturaVPS Demo Sp. z o.o.",
            nip="5252344078",
            regon="017511575",
            address="ul. Marszałkowska 100",
            postal_code="00-026",
            city="Warszawa",
            bank_account="PL61109010140000071219812874",
            vat_rate_default=23,
            email="biuro@fakturavps.pl",
            phone="+48 22 123 45 67",
            is_active=True,
        )
        db.add(company)

        import os
        seed_admin_password = os.environ.get("SEED_ADMIN_PASSWORD", "")
        if not seed_admin_password or len(seed_admin_password) < 12:
            # Domyślne hasło demo — zmień SEED_ADMIN_PASSWORD w .env przed wdrożeniem
            seed_admin_password = "Admin123!demo"
        admin = User(
            id=uuid.uuid4(),
            email="admin@faktura.pl",
            hashed_password=hash_password(seed_admin_password),
            full_name="Administrator Systemu",
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.flush()

        contractors_data = [
            {
                "nip": "7272445205",
                "name": "Kowalski Technologie Sp. z o.o.",
                "regon": "100000001",
                "address": "ul. Polna 15",
                "postal_code": "90-001",
                "city": "Łódź",
                "email": "kontakt@kowalski-tech.pl",
                "phone": "+48 42 111 22 33",
                "bank_account": "PL11109010140000071219812874",
                "default_payment_days": 14,
                "category": "klient",
                "status": "aktywny",
            },
            {
                "nip": "5213254888",
                "name": "Nowak i Wspólnicy S.A.",
                "regon": "100000002",
                "address": "ul. Wrocławska 22",
                "postal_code": "60-101",
                "city": "Poznań",
                "email": "biuro@nowak-sa.pl",
                "phone": "+48 61 222 33 44",
                "bank_account": "PL22109010140000071219812874",
                "default_payment_days": 30,
                "category": "oba",
                "status": "aktywny",
            },
            {
                "nip": "6462465693",
                "name": "Zaopatrzenie Plus Sp. k.",
                "regon": "100000003",
                "address": "ul. Śląska 5",
                "postal_code": "40-001",
                "city": "Katowice",
                "email": "zamowienia@zaopatrzenie.pl",
                "phone": "+48 32 333 44 55",
                "bank_account": "PL33109010140000071219812874",
                "default_payment_days": 21,
                "category": "dostawca",
                "status": "aktywny",
            },
        ]

        contractor_objs = []
        for c_data in contractors_data:
            c = Contractor(id=uuid.uuid4(), created_by_id=admin.id, **c_data)
            db.add(c)
            contractor_objs.append(c)

        db.flush()

        today = date.today()
        invoices_data = [
            {
                "type": "sprzedaz",
                "contractor": contractor_objs[0],
                "issue_date": today - timedelta(days=5),
                "sale_date": today - timedelta(days=5),
                "due_date": today + timedelta(days=9),
                "status": "oczekuje",
                "items": [
                    {"name": "Usługi programistyczne", "qty": "10", "price": "150.00", "vat": "23"},
                    {"name": "Konsultacje IT", "qty": "5", "price": "200.00", "vat": "23"},
                ],
            },
            {
                "type": "sprzedaz",
                "contractor": contractor_objs[1],
                "issue_date": today - timedelta(days=35),
                "sale_date": today - timedelta(days=35),
                "due_date": today - timedelta(days=5),
                "status": "przeterminowana",
                "items": [
                    {"name": "Licencja oprogramowania", "qty": "1", "price": "1200.00", "vat": "23"},
                ],
            },
            {
                "type": "zakup",
                "contractor": contractor_objs[2],
                "issue_date": today - timedelta(days=10),
                "sale_date": today - timedelta(days=10),
                "due_date": today + timedelta(days=11),
                "status": "oczekuje",
                "items": [
                    {"name": "Materiały biurowe", "qty": "100", "price": "2.50", "vat": "23"},
                    {"name": "Toner do drukarki", "qty": "3", "price": "89.00", "vat": "23"},
                ],
            },
            {
                "type": "sprzedaz",
                "contractor": contractor_objs[0],
                "issue_date": today - timedelta(days=60),
                "sale_date": today - timedelta(days=60),
                "due_date": today - timedelta(days=46),
                "status": "zaplacona",
                "items": [
                    {"name": "Wdrożenie systemu", "qty": "1", "price": "5000.00", "vat": "23"},
                ],
            },
            {
                "type": "sprzedaz",
                "contractor": contractor_objs[1],
                "issue_date": today,
                "sale_date": today,
                "due_date": today + timedelta(days=14),
                "status": "szkic",
                "items": [
                    {"name": "Projekt graficzny", "qty": "1", "price": "800.00", "vat": "23"},
                    {"name": "Hosting roczny", "qty": "1", "price": "300.00", "vat": "23"},
                ],
            },
        ]

        type_counters = {}
        for inv_data in invoices_data:
            inv_type = inv_data["type"]
            year = inv_data["issue_date"].year
            key = f"{inv_type}_{year}"
            type_counters[key] = type_counters.get(key, 0) + 1

            prefix_map = {"sprzedaz": "FV", "zakup": "FZ"}
            prefix = prefix_map.get(inv_type, "FV")
            num_str = f"{prefix}/{year}/{str(type_counters[key]).zfill(3)}"

            invoice = Invoice(
                id=uuid.uuid4(),
                number=num_str,
                type=inv_type,
                contractor_id=inv_data["contractor"].id,
                company_id=company.id,
                issue_date=inv_data["issue_date"],
                sale_date=inv_data["sale_date"],
                due_date=inv_data["due_date"],
                status=inv_data["status"],
                currency="PLN",
                source="manual",
                created_by_id=admin.id,
                net_amount=Decimal("0"),
                vat_amount=Decimal("0"),
                gross_amount=Decimal("0"),
            )
            db.add(invoice)
            db.flush()

            total_net = Decimal("0")
            total_vat = Decimal("0")
            total_gross = Decimal("0")

            for pos, item in enumerate(inv_data["items"], 1):
                qty = Decimal(item["qty"])
                price = Decimal(item["price"])
                vat_rate_str = item["vat"]
                vat_rates = {"23": Decimal("0.23"), "8": Decimal("0.08"), "5": Decimal("0.05"), "0": Decimal("0")}
                rate = vat_rates.get(vat_rate_str, Decimal("0.23"))
                net = (qty * price).quantize(Decimal("0.01"))
                vat = (net * rate).quantize(Decimal("0.01"))
                gross = net + vat

                db.add(InvoiceItem(
                    id=uuid.uuid4(),
                    invoice_id=invoice.id,
                    name=item["name"],
                    quantity=qty,
                    unit="szt",
                    unit_price_net=price,
                    vat_rate=vat_rate_str,
                    net_amount=net,
                    vat_amount=vat,
                    gross_amount=gross,
                    position_order=pos,
                ))
                total_net += net
                total_vat += vat
                total_gross += gross

            invoice.net_amount = total_net
            invoice.vat_amount = total_vat
            invoice.gross_amount = total_gross

            db.add(InvoiceStatusHistory(
                id=uuid.uuid4(),
                invoice_id=invoice.id,
                old_status=None,
                new_status=inv_data["status"],
                changed_by_id=admin.id,
                source="system",
                reason="Dane przykładowe"
            ))

        db.commit()
        print("Dane przykładowe zostały dodane. Zaloguj się jako admin@faktura.pl")
    except Exception as e:
        db.rollback()
        print(f"Błąd przy seedowaniu danych: {e}")
    finally:
        db.close()


@app.on_event("startup")
async def startup():
    import time
    import sqlalchemy.exc
    for attempt in range(10):
        try:
            Base.metadata.create_all(bind=engine)
            seed_data()
            print("FakturaVPS API uruchomiony pomyślnie")
            break
        except sqlalchemy.exc.OperationalError as e:
            print(f"Baza danych niedostępna (próba {attempt+1}/10): {e}")
            time.sleep(3)
