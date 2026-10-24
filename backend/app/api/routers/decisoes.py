"""US-13, US-14 · Decisões do regulador."""
from fastapi import APIRouter, Depends

from app.api import schemas
from app.api.deps import get_decidir
from app.application.decidir import ComandoDecisao, DecidirClasse
from app.config import settings

router = APIRouter(prefix="/decisoes", tags=["regulador"])


@router.post("", response_model=schemas.DecisaoResultadoOut,
             responses={404: {"model": schemas.Erro}, 409: {"model": schemas.Erro},
                        422: {"model": schemas.Erro}})
def registrar_decisao(body: schemas.DecisaoIn, decidir: DecidirClasse = Depends(get_decidir)):
    if settings.use_mocks:
        return schemas.DecisaoResultadoOut(decisao_id="DEC-MOCK", posicao_anterior=536,
                                           posicao_nova=140, fila_publicada=True)
    r = decidir.executar(ComandoDecisao(
        solicitacao_id=body.solicitacao_id, regulador_id=body.regulador_id, acao=body.acao,
        classe=body.classe, score=body.score, motivo_codificado=body.motivo_codificado,
        justificativa=body.justificativa))  # editar/manter: US-14 (NotImplementedError -> 501)
    return schemas.DecisaoResultadoOut(decisao_id=r.decisao_id, posicao_anterior=r.posicao_anterior,
                                       posicao_nova=r.posicao_nova, fila_publicada=r.fila_publicada)
