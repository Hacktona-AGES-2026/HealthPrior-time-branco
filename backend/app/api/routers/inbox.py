"""US-12 · Inbox do regulador."""
from typing import Optional

from fastapi import APIRouter, Depends

from app.api import mocks, schemas
from app.api.deps import get_listar_inbox
from app.application.listar_inbox import Inbox, ListarInbox
from app.config import settings

router = APIRouter(prefix="/inbox", tags=["regulador"])


def _para_schema(inbox: Inbox) -> schemas.InboxOut:
    itens = []
    for i in inbox.itens:
        editado = (schemas.EditadoAnteriormente(por=i.editado_anteriormente[0],
                                                em=i.editado_anteriormente[1].date())
                   if i.editado_anteriormente else None)
        itens.append(schemas.ItemInboxOut(
            solicitacao_id=i.solicitacao_id, procedimento=i.procedimento, camada=i.camada,
            dias_em_fila=i.dias_em_fila, classe_atual=i.classe_atual,
            classe_sugerida=i.classe_sugerida,
            motivos=[schemas.MotivoOut(sinal=m.sinal, evidencia=m.evidencia, fonte=m.fonte,
                                       ref=m.ref, data=m.data) for m in i.motivos],
            evento_gatilho=i.evento_gatilho, editado_anteriormente=editado,
            criado_em=i.criado_em))
    return schemas.InboxOut(total=inbox.total, itens=itens)


@router.get("", response_model=schemas.InboxOut)
def listar_inbox(regulador_id: Optional[str] = None,  # aceito e ignorado: sem atribuição
                 caso: ListarInbox = Depends(get_listar_inbox)):
    if settings.use_mocks:
        return mocks.INBOX
    return _para_schema(caso.executar())
