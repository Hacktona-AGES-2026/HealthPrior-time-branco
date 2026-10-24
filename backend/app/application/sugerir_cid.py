"""PRE-12 · Sugerir o CID a partir do laudo (D-125).

Para uma pendência "câncer escondido" aberta: manda o laudo ao LLM, valida a resposta (o código
existe na tabela CID-10, é outro CID e a citação está literalmente no laudo) e guarda a sugestão
na pendência. Não muda o CID: quem decide é o regulador, ao resolver a pendência (I-05).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.domain.correcao_cid import laudos_da_pendencia, motivo_rejeicao
from app.domain.enums import StatusPendencia
from app.domain.models import SugestaoCid
from app.domain.ports import (
    PendenciaRepository,
    SolicitacaoRepository,
    SugestorCid,
    TabelaCid,
    UnidadeDeTrabalho,
)
from app.domain.preprocessing.inconsistencias import PRE_CANCER_ESCONDIDO

log = logging.getLogger(__name__)


@dataclass
class ResumoSugestoes:
    pendencias: int = 0
    sugeridas: int = 0
    sem_sugestao: int = 0  # LLM sem resposta (sem chave, falha) ou sugestão descartada na validação


class SugerirCid:
    def __init__(self, pendencias: PendenciaRepository, solicitacoes: SolicitacaoRepository,
                 sugestor: SugestorCid, tabela: TabelaCid, uow: UnidadeDeTrabalho):
        self._pendencias = pendencias
        self._solicitacoes = solicitacoes
        self._sugestor = sugestor
        self._tabela = tabela
        self._uow = uow

    def executar(self, pendencia_id: str) -> SugestaoCid | None:
        """Sugestão guardada na pendência, ou None (sem laudo, LLM sem resposta ou sugestão inválida)."""
        p = self._pendencias.obter(pendencia_id)
        if p is None or p.regra != PRE_CANCER_ESCONDIDO or p.status != StatusPendencia.ABERTA:
            return None
        s = self._solicitacoes.obter(p.solicitacao_id)
        laudos = laudos_da_pendencia(p)
        if s is None or not laudos:
            return None
        evento_id, laudo = laudos[-1]  # o laudo mais recente manda
        sugestao = self._sugestor.sugerir(s.procedimento or "", s.cid_principal, s.cid_descricao or "", laudo)
        if sugestao is None:
            return None
        descricao = self._tabela.descricao(sugestao.cid)
        rejeicao = motivo_rejeicao(sugestao, laudo, s.cid_principal, descricao)
        if rejeicao:
            log.info("Sugestão de CID descartada em %s: %s", pendencia_id, rejeicao)
            return None
        sugestao.descricao, sugestao.evento_id = descricao, evento_id  # descrição oficial, não a do LLM
        p.sugestao_cid = sugestao
        self._pendencias.salvar(p)
        self._uow.confirmar()
        return sugestao

    def executar_abertas(self) -> ResumoSugestoes:
        """Todas as PRE-12 abertas (comando `sugerir-cid`): aquece o cache para a demo."""
        resumo = ResumoSugestoes()
        for p in self._pendencias.listar(regra=PRE_CANCER_ESCONDIDO, status=StatusPendencia.ABERTA.value):
            resumo.pendencias += 1
            if self.executar(p.pendencia_id):
                resumo.sugeridas += 1
            else:
                resumo.sem_sugestao += 1
        return resumo
