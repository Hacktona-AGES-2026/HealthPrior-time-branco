"""US-19 · Comitê clínico: propostas de regra, impacto simulado e decisão (C-14)."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api import mocks, schemas
from app.api.deps import get_decidir_proposta, get_listar_propostas, get_nomes_procedimentos
from app.application.propostas import DecidirProposta, ListarPropostas, PropostaDetalhe
from app.config import settings

router = APIRouter(tags=["comite"])
_ERROS = {404: {"model": schemas.Erro}, 409: {"model": schemas.Erro}, 422: {"model": schemas.Erro}}


def _item(d: PropostaDetalhe, nomes: dict[str, str]) -> schemas.PropostaDetalheOut:
    p = d.proposta
    return schemas.PropostaDetalheOut(
        proposta_id=p.proposta_id, procedimento_id=p.procedimento_id,
        procedimento=nomes.get(p.procedimento_id), motivo=p.motivo, classe_de=p.classe_de,
        classe_para=p.classe_para, direcao=p.direcao, n_casos=p.n_casos,
        n_reguladores=p.n_reguladores, consistencia=p.consistencia, casos=list(p.casos),
        status=p.status, motivo_descarte=p.motivo_descarte,
        casos_origem=[schemas.CasoOrigemOut(
            decisao_id=c.decisao_id, solicitacao_id=c.solicitacao_id, regulador_id=c.regulador_id,
            data=c.data, acao=c.acao.value, classe_de=c.classe_sugerida, classe_para=c.classe_decidida,
            motivo=c.motivo_codificado, justificativa=c.justificativa) for c in d.casos_origem],
        impacto=None if d.impacto is None else schemas.ImpactoOut(
            afetados=d.impacto.afetados, oncologicos_afetados=d.impacto.oncologicos_afetados,
            oncologicos_rebaixados=d.impacto.oncologicos_rebaixados, exemplos=d.impacto.exemplos),
        decidida_por=p.decidida_por, decidida_em=p.decidida_em, observacao=p.observacao,
        versao=d.versao)


@router.get("/propostas", response_model=schemas.PropostasOut)
def listar_propostas(status: Optional[str] = Query(default=None, pattern="^(pendente|descartada|aprovada|rejeitada)$"),
                     caso: ListarPropostas = Depends(get_listar_propostas),
                     nomes: dict[str, str] = Depends(get_nomes_procedimentos)):
    """Propostas com os casos de origem e, nas pendentes, o impacto simulado (shadow run)."""
    if settings.use_mocks:
        return mocks.PROPOSTAS
    itens = [_item(d, nomes) for d in caso.executar(status)]
    return schemas.PropostasOut(total=len(itens), itens=itens)


@router.post("/propostas/{proposta_id}/decidir", response_model=schemas.DecidirPropostaOut, responses=_ERROS)
def decidir_proposta(proposta_id: str, body: schemas.DecidirPropostaIn,
                     caso: DecidirProposta = Depends(get_decidir_proposta)):
    """Aprovar cria a versão N+1 das regras e manda os afetados ao inbox; rejeitar exige o motivo."""
    if settings.use_mocks:
        return mocks.DECIDIR_PROPOSTA
    r = caso.executar(proposta_id, body.decisao, body.usuario_id, body.observacao)
    return schemas.DecidirPropostaOut(
        proposta_id=r.proposta_id, status=r.status, versao=r.versao, versao_regras=r.versao_regras,
        enviados_ao_inbox=r.enviados_ao_inbox)
