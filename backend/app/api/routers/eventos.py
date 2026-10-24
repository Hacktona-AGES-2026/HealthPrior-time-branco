"""US-15 · Registrar evento novo."""
from fastapi import APIRouter, status

from app.api import schemas
from app.config import settings

router = APIRouter(prefix="/eventos", tags=["eventos"])


@router.post("", response_model=schemas.EventoResultadoOut, status_code=status.HTTP_201_CREATED,
             responses={404: {"model": schemas.Erro}, 422: {"model": schemas.Erro}})
def registrar_evento(body: schemas.EventoIn):
    if settings.use_mocks:
        return schemas.EventoResultadoOut(evento_id="EVT-MOCK", desfecho="enviado_inbox",
                                          classe_antes="C", classe_depois="B")
    # TODO(US-15): RegistrarEvento via deps.get_registrar_evento
    raise NotImplementedError("US-15: POST /eventos")
