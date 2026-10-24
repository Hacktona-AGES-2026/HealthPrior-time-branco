"""US-15 · Registrar evento novo."""
from fastapi import APIRouter, Depends, status

from app.api import schemas
from app.api.deps import get_registrar_evento
from app.application.registrar_evento import NovoEvento, RegistrarEvento
from app.config import settings

router = APIRouter(prefix="/eventos", tags=["eventos"])


@router.post("", response_model=schemas.EventoResultadoOut, status_code=status.HTTP_201_CREATED,
             responses={404: {"model": schemas.Erro}, 422: {"model": schemas.Erro}})
def registrar_evento(body: schemas.EventoIn, caso: RegistrarEvento = Depends(get_registrar_evento)):
    """Pré-processa o evento, reavalia o SWALIS e informa o desfecho (registrado/inbox/pendência)."""
    if settings.use_mocks:
        return schemas.EventoResultadoOut(evento_id="EVT-MOCK", desfecho="enviado_inbox",
                                          classe_antes="C", classe_depois="B")
    r = caso.executar(NovoEvento(**body.model_dump()))
    return schemas.EventoResultadoOut(evento_id=r.evento_id, desfecho=r.desfecho,
                                      classe_antes=r.classe_antes, classe_depois=r.classe_depois,
                                      pendencia_id=r.pendencia_id)
