"""US-12 · Inbox do regulador."""
from typing import Optional

from fastapi import APIRouter

from app.api import mocks, schemas
from app.config import settings

router = APIRouter(prefix="/inbox", tags=["regulador"])


@router.get("", response_model=schemas.InboxOut)
def listar_inbox(regulador_id: Optional[str] = None):
    if settings.use_mocks:
        return mocks.INBOX
    raise NotImplementedError("US-12: GET /inbox")
