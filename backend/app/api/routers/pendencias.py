"""US-06, US-07 · Pendências administrativas."""
from typing import Optional

from fastapi import APIRouter

from app.api import mocks, schemas
from app.config import settings

router = APIRouter(prefix="/pendencias", tags=["pendencias"])


@router.get("", response_model=schemas.PendenciasOut)
def listar_pendencias(bloqueante: Optional[bool] = None, regra: Optional[str] = None,
                      status: str = "aberta"):
    if settings.use_mocks:
        return mocks.PENDENCIAS
    raise NotImplementedError("US-06: GET /pendencias")


@router.post("/{pendencia_id}/resolver", response_model=schemas.ResolverPendenciaOut,
             responses={404: {"model": schemas.Erro}})
def resolver_pendencia(pendencia_id: str, body: schemas.ResolverPendenciaIn):
    if settings.use_mocks:
        return schemas.ResolverPendenciaOut(status_fila="removida", fila_publicada=True)
    raise NotImplementedError("US-07: POST /pendencias/{id}/resolver")
