"""US-18 · Ciclo de aprendizado: agrupa as justificativas do comitê em propostas de regra."""
from typing import Optional

from fastapi import APIRouter, Body, Depends

from app.api import mocks, schemas
from app.api.deps import get_gerar_propostas, get_nomes_procedimentos
from app.application.gerar_propostas import GerarPropostas, ResultadoGeracao
from app.config import settings
from app.domain.aprendizado import ParametrosAprendizado, PropostaRegra

router = APIRouter(prefix="/aprendizado", tags=["comite"])


def _proposta(p: PropostaRegra, nomes: dict[str, str]) -> schemas.PropostaRegraOut:
    return schemas.PropostaRegraOut(
        proposta_id=p.proposta_id, procedimento_id=p.procedimento_id,
        procedimento=nomes.get(p.procedimento_id), motivo=p.motivo, classe_de=p.classe_de,
        classe_para=p.classe_para, direcao=p.direcao, n_casos=p.n_casos,
        n_reguladores=p.n_reguladores, consistencia=p.consistencia, casos=list(p.casos),
        status=p.status, motivo_descarte=p.motivo_descarte)


def _saida(r: ResultadoGeracao, nomes: dict[str, str]) -> schemas.GerarPropostasOut:
    return schemas.GerarPropostasOut(
        analisadas=r.analisadas, consideradas=r.consideradas,
        outros_reclassificados=r.outros_reclassificados, outros_sem_grupo=r.outros_sem_grupo,
        propostas=[_proposta(p, nomes) for p in r.propostas],
        descartadas=[_proposta(p, nomes) for p in r.descartadas])


@router.post("/gerar-propostas", response_model=schemas.GerarPropostasOut)
def gerar_propostas(body: Optional[schemas.ParametrosAprendizadoIn] = Body(default=None),
                    caso: GerarPropostas = Depends(get_gerar_propostas),
                    nomes: dict[str, str] = Depends(get_nomes_procedimentos)):
    """Agrupa decisões por (procedimento, motivo, classe) e grava as propostas pendentes (C-14).

    Os parâmetros do corpo (opcionais) substituem os padrões de Q-05 nesta execução.
    """
    if settings.use_mocks:
        return mocks.GERAR_PROPOSTAS
    if body is not None:
        padrao = ParametrosAprendizado()
        caso.params = ParametrosAprendizado(**{
            k: (v if v is not None else getattr(padrao, k)) for k, v in body.model_dump().items()})
    return _saida(caso.executar(), nomes)
