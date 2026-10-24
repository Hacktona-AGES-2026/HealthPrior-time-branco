"""US-13, US-14 · Decisões do regulador."""
from fastapi import APIRouter

from app.api import schemas
from app.config import settings

router = APIRouter(prefix="/decisoes", tags=["regulador"])


@router.post("", response_model=schemas.DecisaoResultadoOut,
             responses={404: {"model": schemas.Erro}, 422: {"model": schemas.Erro}})
def registrar_decisao(body: schemas.DecisaoIn):
    if settings.use_mocks:
        return schemas.DecisaoResultadoOut(decisao_id="DEC-MOCK", posicao_anterior=536,
                                           posicao_nova=140, fila_publicada=True)
    # TODO(US-13/14): DecidirClasse via deps.get_decidir
    raise NotImplementedError("US-13/14: POST /decisoes")
