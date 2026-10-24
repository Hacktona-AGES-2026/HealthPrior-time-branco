"""Notificações ao paciente (demo): o que foi enfileirado/enviado e o disparo manual do envio."""
from fastapi import APIRouter, Depends, Query

from app.api import schemas
from app.api.deps import get_enviar_notificacoes, get_notificacoes
from app.application.notificacoes import EnviarNotificacoes
from app.config import settings
from app.infrastructure.notificador import criar_notificador
from app.infrastructure.repositories import SqlNotificacaoRepository

router = APIRouter(prefix="/notificacoes", tags=["notificacoes"])


def _destino_para_tela() -> str | None:
    canal = criar_notificador().canal
    partes = []
    if "waha" in canal or "twilio" in canal:
        partes.append(", ".join(_mascarar(n.strip()) or "" for n in settings.notifica_destino.split(",") if n.strip()))
    if "ntfy" in canal:
        partes.append(f"{settings.ntfy_url.split('://')[-1]}/{settings.ntfy_topic}")
    return " + ".join(p for p in partes if p) or None


def _mascarar(numero: str) -> str | None:
    return None if not numero else f"{numero[:3]}{'*' * max(len(numero) - 5, 0)}{numero[-2:]}"


@router.get("", response_model=schemas.NotificacoesOut)
def listar_notificacoes(limite: int = Query(default=100, ge=1, le=500),
                        repo: SqlNotificacaoRepository = Depends(get_notificacoes)):
    """Mais recentes primeiro. O canal e o destino mostram para onde as mensagens iriam agora."""
    if settings.use_mocks:
        return schemas.NotificacoesOut(canal="simulado", destino=None, total=0, itens=[])
    itens = [schemas.NotificacaoOut(**vars(n)) for n in repo.listar(limite)]
    return schemas.NotificacoesOut(canal=criar_notificador().canal, destino=_destino_para_tela(),
                                   total=len(itens), itens=itens)


@router.post("/enviar", response_model=schemas.EnviosOut)
def enviar_notificacoes(caso: EnviarNotificacoes = Depends(get_enviar_notificacoes)):
    """Envia as pendentes pelo canal configurado (no máximo `HP_NOTIFICA_LIMITE_ENVIO` por rodada)."""
    if settings.use_mocks:
        return schemas.EnviosOut(canal="simulado", enviadas=0, falhas=0, pendentes=0)
    r = caso.executar()
    return schemas.EnviosOut(canal=criar_notificador().canal, enviadas=r.enviadas, falhas=r.falhas,
                             pendentes=r.pendentes)
