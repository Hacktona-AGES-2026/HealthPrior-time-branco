"""US-01, US-16 · Operações administrativas (disparo manual para a demo)."""
from dataclasses import asdict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_carga_inicial, get_publicar_fila
from app.api.schemas import CargaOut, PublicacaoOut
from app.application.carga_inicial import CargaInicial
from app.application.publicar_fila import PublicarFila

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/carga", response_model=CargaOut)
def carga(caso_de_uso: CargaInicial = Depends(get_carga_inicial)):
    """US-01 (carga) + US-02 (normalização), na mesma transação. Idempotente."""
    return asdict(caso_de_uso.executar())


@router.post("/publicar-fila", response_model=PublicacaoOut,
             responses={422: {"model": PublicacaoOut}})
def publicar_fila(caso_de_uso: PublicarFila = Depends(get_publicar_fila)):
    """US-10: gera, verifica e publica a fila (I-07). 422 se o verificador falhar."""
    r = caso_de_uso.executar()
    corpo = PublicacaoOut(publicada=r.publicada, total=r.total, por_camada=r.por_camada,
                          versao_regras=r.versao_regras, saida_verificador=r.saida_verificador)
    return JSONResponse(status_code=200 if r.publicada else 422, content=corpo.model_dump())


@router.post("/atualizacao-diaria")
def atualizacao_diaria():
    raise NotImplementedError("US-16: POST /admin/atualizacao-diaria")
