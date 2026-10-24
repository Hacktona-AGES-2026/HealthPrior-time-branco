"""US-20, US-09 · Fila priorizada."""
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, JSONResponse

from app.api import mocks, schemas
from app.api.deps import get_exportar_fila_publicada, get_listar_fila
from app.application.listar_fila import FiltroFila, ListarFila, PaginaFila
from app.application.publicar_fila import ExportarFilaPublicada
from app.config import settings

router = APIRouter(prefix="/fila", tags=["fila"])


@router.get("", response_model=schemas.FilaOut)
def listar_fila(
    camada: Optional[int] = None,
    procedimento_id: Optional[str] = None,
    especialidade: Optional[str] = None,
    busca: Optional[str] = None,
    page: int = Query(1, description="1-based; < 1 -> 422 PAGINACAO_INVALIDA"),
    page_size: int = Query(50, description="1..200; acima de 200 é limitado a 200"),
    listar: ListarFila = Depends(get_listar_fila),
):
    if settings.use_mocks:
        return mocks.FILA
    filtro = FiltroFila(camada=camada, procedimento_id=procedimento_id,
                        especialidade=especialidade, busca=busca,
                        page=page, page_size=page_size)
    try:
        pagina = listar.executar(filtro)
    except ValueError as exc:
        return JSONResponse(status_code=422,
                            content={"erro": "PAGINACAO_INVALIDA", "mensagem": str(exc)})
    return _para_schema(pagina)


def _para_schema(pagina: PaginaFila) -> schemas.FilaOut:
    return schemas.FilaOut(
        versao_regras=pagina.versao_regras,
        gerada_em=pagina.gerada_em,
        publicada=pagina.publicada,
        total=pagina.total,
        itens=[schemas.ItemFilaOut(**asdict(i)) for i in pagina.itens],
    )


@router.get("/export")
def exportar_fila(exportar: ExportarFilaPublicada = Depends(get_exportar_fila_publicada)):
    """US-10: devolve só a fila publicada (409 FILA_NAO_PUBLICADA se ainda não houver)."""
    caminho = exportar.executar()
    return FileResponse(caminho, media_type="text/csv", filename="fila_priorizada.csv")
