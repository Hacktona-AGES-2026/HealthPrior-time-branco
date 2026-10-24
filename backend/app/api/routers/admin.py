"""US-01, US-16 · Operações administrativas (disparo manual para a demo)."""
from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.api.deps import get_carga_inicial
from app.api.schemas import CargaOut
from app.application.carga_inicial import CargaInicial

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/carga", response_model=CargaOut)
def carga(caso_de_uso: CargaInicial = Depends(get_carga_inicial)):
    """US-01 (carga) + US-02 (normalização), na mesma transação. Idempotente."""
    return asdict(caso_de_uso.executar())


@router.post("/atualizacao-diaria")
def atualizacao_diaria():
    raise NotImplementedError("US-16: POST /admin/atualizacao-diaria")
