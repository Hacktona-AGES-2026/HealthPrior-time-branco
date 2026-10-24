"""US-20, US-09 · Fila priorizada."""
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api import mocks, schemas
from app.api.deps import get_gerar_fila
from app.application.gerar_fila import GerarFila
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
def exportar_fila(gerar_fila: GerarFila = Depends(get_gerar_fila)):
    """US-09: gera a fila a partir do banco e devolve o CSV (independe de HP_USE_MOCKS)."""
    resultado = gerar_fila.executar(settings.output_dir / "fila_priorizada.csv")
    return FileResponse(resultado.caminho_csv, media_type="text/csv",
                        filename="fila_priorizada.csv")
