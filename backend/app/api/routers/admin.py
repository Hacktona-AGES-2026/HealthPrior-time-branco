"""US-01, US-16 · Operações administrativas (disparo manual para a demo)."""
from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_atualizacao_diaria, get_carga_inicial, get_publicar_fila
from app.api.schemas import CargaOut, PublicacaoOut, RecontatoOut
from app.application.atualizacao_diaria import AtualizacaoDiaria
from app.application.carga_inicial import CargaInicial
from app.application.publicar_fila import PublicarFila, ResultadoPublicacao

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/carga", response_model=CargaOut)
def carga(caso_de_uso: CargaInicial = Depends(get_carga_inicial)):
    """US-01 (carga) + US-02 (normalização), na mesma transação. Idempotente."""
    return asdict(caso_de_uso.executar())


@router.post("/publicar-fila", response_model=PublicacaoOut,
             responses={422: {"model": PublicacaoOut}})
def publicar_fila(caso_de_uso: PublicarFila = Depends(get_publicar_fila)):
    """US-10: gera, verifica e publica a fila (I-07). 422 se o verificador falhar."""
    return _resposta_publicacao(caso_de_uso.executar())


@router.post("/atualizacao-diaria", response_model=PublicacaoOut,
             responses={422: {"model": PublicacaoOut}})
def atualizacao_diaria(data: date | None = None,
                       caso_de_uso: AtualizacaoDiaria = Depends(get_atualizacao_diaria)):
    """US-16: avança a data de referência (+1 dia, ou `data`) e republica como o publicar-fila.

    Recalcula tudo a partir da data, então repetir a mesma `data` dá a mesma fila. 422 se o
    verificador falhar (a fila e a data anteriores continuam valendo).
    """
    return _resposta_publicacao(caso_de_uso.executar(data))


def _resposta_publicacao(r: ResultadoPublicacao) -> JSONResponse:
    corpo = PublicacaoOut(publicada=r.publicada, total=r.total, por_camada=r.por_camada,
                          versao_regras=r.versao_regras, saida_verificador=r.saida_verificador,
                          data_referencia=r.data_referencia, recontato=_recontato(r.recontato))
    return JSONResponse(status_code=200 if r.publicada else 422, content=corpo.model_dump(mode="json"))


def _recontato(r) -> RecontatoOut | None:
    if r is None:
        return None
    return RecontatoOut(n_dias=r.n_dias, sem_evento=r.sem_evento, abertas=r.pendencias.abertas,
                        atualizadas=r.pendencias.atualizadas, encerradas=r.pendencias.encerradas)
