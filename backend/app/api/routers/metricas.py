"""US-22 · Métricas 'antes × depois'."""
from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.api.deps import get_comparar_filas
from app.api.schemas import ComparacaoOut
from app.application.comparar_filas import CompararFilas

router = APIRouter(prefix="/metricas", tags=["metricas"])


@router.get("/comparacao", response_model=ComparacaoOut)
def comparacao(caso_de_uso: CompararFilas = Depends(get_comparar_filas)):
    """US-22: indicadores da ordem atual (antes) × fila publicada (depois). Sem publicação: depois nulo."""
    return asdict(caso_de_uso.executar())
