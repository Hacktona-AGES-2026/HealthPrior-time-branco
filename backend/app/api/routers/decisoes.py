"""US-13, US-14 · Decisões do regulador."""
from fastapi import APIRouter, Depends

from app.api import schemas
from app.api.deps import get_decidir
from app.application.decidir import ComandoDecisao, DecidirClasse
from app.config import settings

router = APIRouter(prefix="/decisoes", tags=["regulador"])


@router.post("", response_model=schemas.DecisaoResultadoOut,
             responses={404: {"model": schemas.Erro}, 422: {"model": schemas.Erro}})
def registrar_decisao(body: schemas.DecisaoIn, caso: DecidirClasse = Depends(get_decidir)):
    """aprovar | editar | manter. Grava a decisão e refaz a fila pelo verificador (I-07)."""
    if settings.use_mocks:
        return schemas.DecisaoResultadoOut(decisao_id="DEC-MOCK", posicao_anterior=536,
                                           posicao_nova=140, fila_publicada=True)
    r = caso.executar(ComandoDecisao(**body.model_dump()))
    return schemas.DecisaoResultadoOut(decisao_id=r.decisao_id, posicao_anterior=r.posicao_anterior,
                                       posicao_nova=r.posicao_nova, fila_publicada=r.fila_publicada)
