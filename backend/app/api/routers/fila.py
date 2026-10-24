"""US-20, US-09 · Fila priorizada."""
from typing import Optional

from fastapi import APIRouter

from app.api import mocks, schemas
from app.config import settings

router = APIRouter(prefix="/fila", tags=["fila"])


@router.get("", response_model=schemas.FilaOut)
def listar_fila(
    camada: Optional[int] = None,
    procedimento_id: Optional[str] = None,
    especialidade: Optional[str] = None,
    busca: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
):
    if settings.use_mocks:
        return mocks.FILA
    raise NotImplementedError("US-20: GET /fila")


@router.get("/export")
def exportar_fila():
    raise NotImplementedError("US-09: GET /fila/export")
