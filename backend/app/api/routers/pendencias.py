"""US-06, US-07 · Pendências administrativas."""
from typing import Optional

from fastapi import APIRouter, Depends

from app.api import mocks, schemas
from app.api.deps import get_listar_pendencias, get_resolver_pendencia
from app.application.listar_pendencias import ListarPendencias
from app.application.resolver_pendencia import ResolverPendencia
from app.config import settings
from app.domain.enums import StatusPendencia
from app.domain.models import Pendencia

router = APIRouter(prefix="/pendencias", tags=["pendencias"])


def _para_out(p: Pendencia) -> schemas.PendenciaOut:
    return schemas.PendenciaOut(
        pendencia_id=p.pendencia_id, solicitacao_id=p.solicitacao_id, regra=p.regra, titulo=p.titulo,
        bloqueante=p.bloqueante, acao_sugerida=p.acao_sugerida, status=p.status, aberta_em=p.aberta_em,
        evidencias=[schemas.EvidenciaOut(fonte=m.fonte, ref=m.ref, texto=m.evidencia) for m in p.evidencias],
    )


@router.get("", response_model=schemas.PendenciasOut)
def listar_pendencias(
    bloqueante: Optional[bool] = None,
    regra: Optional[str] = None,
    status: StatusPendencia = StatusPendencia.ABERTA,
    caso_de_uso: ListarPendencias = Depends(get_listar_pendencias),
):
    if settings.use_mocks:
        return mocks.PENDENCIAS
    itens = caso_de_uso.executar(bloqueante=bloqueante, regra=regra, status=status)
    return schemas.PendenciasOut(total=len(itens), itens=[_para_out(p) for p in itens])


@router.post("/{pendencia_id}/resolver", response_model=schemas.ResolverPendenciaOut,
             responses={404: {"model": schemas.Erro}, 409: {"model": schemas.Erro},
                        422: {"model": schemas.Erro}})
def resolver_pendencia(pendencia_id: str, body: schemas.ResolverPendenciaIn,
                       caso_de_uso: ResolverPendencia = Depends(get_resolver_pendencia)):
    if settings.use_mocks:
        return schemas.ResolverPendenciaOut(status_fila="removida", fila_publicada=True)
    resultado = caso_de_uso.executar(
        pendencia_id, body.resolucao, body.usuario_id, body.observacao, body.fundir_com)
    return schemas.ResolverPendenciaOut(status_fila=resultado.status_fila, fila_publicada=resultado.fila_publicada)
