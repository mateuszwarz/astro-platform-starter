# FakturaVPS - System Fakturowania

Kompletna aplikacja webowa do zarządzania fakturami z integracją KSeF (mock).

## Stos technologiczny

- **Backend**: Python 3.12 + FastAPI + SQLAlchemy + Alembic + Celery + Redis
- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS + Recharts
- **Baza danych**: PostgreSQL 16
- **Deployment**: Docker Compose

## Uruchomienie

```bash
docker-compose up --build
```

Aplikacja będzie dostępna pod adresem: http://localhost:5173

## Dane logowania

- **Email**: admin@faktura.pl
- **Hasło**: Admin123!

## Endpointy API

- Dokumentacja Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## Funkcjonalności

- Zarządzanie fakturami (sprzedaż, zakup, korekty, pro forma)
- Numeracja FV/YYYY/NNN
- Integracja z KSeF (mock)
- Generowanie PDF
- Rejestracja płatności
- Zarządzanie kontrahentami z walidacją NIP
- Dashboard z wykresami (Recharts)
- Raporty: VAT, przychody/koszty, wiekowanie należności, top kontrahenci
- Zadania Celery: automatyczne oznaczanie przeterminowanych faktur
- Audit log
