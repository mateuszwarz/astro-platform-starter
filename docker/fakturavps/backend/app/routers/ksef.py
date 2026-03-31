from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ksef", tags=["KSeF"])


@router.get("/status")
def ksef_status(current_user: User = Depends(get_current_user)):
    return {
        "status": "connected",
        "environment": "test",
        "message": "Połączono z KSeF (środowisko testowe)",
        "last_sync": None
    }


@router.get("/info")
def ksef_info(current_user: User = Depends(get_current_user)):
    return {
        "environment": "test",
        "api_version": "2.0",
        "supported_features": ["send", "check_status", "download_upo"],
        "note": "Implementacja mock - nie łączy z prawdziwym KSeF MF"
    }
