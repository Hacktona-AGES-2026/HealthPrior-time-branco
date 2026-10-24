"""US-18 (C-14): agrupa justificativas dos reguladores em propostas de regra para o comitê."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from app.domain.aprendizado import CasoAprendizado, ParametrosAprendizado, PropostaRegra, agrupar
from app.domain.cid import is_oncologico
from app.domain.enums import AcaoDecisao, MotivoCodificado
from app.domain.ports import ClassificadorMotivo, DecisaoRepository, PropostaRepository, SolicitacaoRepository, UnidadeDeTrabalho


@dataclass
class ResultadoGeracao:
    analisadas: int
    consideradas: int
    outros_reclassificados: int
    outros_sem_grupo: int
    propostas: list[PropostaRegra] = field(default_factory=list)
    descartadas: list[PropostaRegra] = field(default_factory=list)


class GerarPropostas:
    def __init__(self, decisoes: DecisaoRepository, solicitacoes: SolicitacaoRepository,
                 propostas: PropostaRepository, uow: UnidadeDeTrabalho, referencia: datetime,
                 classificador: ClassificadorMotivo | None = None,
                 params: ParametrosAprendizado = ParametrosAprendizado(),
                 relogio: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.decisoes, self.solicitacoes, self.propostas, self.uow = decisoes, solicitacoes, propostas, uow
        self.referencia, self.classificador, self.params, self.relogio = referencia, classificador, params, relogio

    def executar(self) -> ResultadoGeracao:
        todas = self.decisoes.listar_todas()
        sols = {s.solicitacao_id: s for s in self.solicitacoes.listar(apenas_ativas=False)}
        onco = {s.procedimento_id for s in self.solicitacoes.listar(apenas_ativas=True)
                if is_oncologico(s.cid_norm or s.cid_principal)}
        casos: list[CasoAprendizado] = []
        reclassificados = sem_grupo = 0
        for d in todas:
            if d.acao not in (AcaoDecisao.EDITAR, AcaoDecisao.MANTER):
                continue
            if d.classe_sugerida is None or d.classe_decidida is None:
                continue
            if d.acao == AcaoDecisao.EDITAR and d.classe_sugerida == d.classe_decidida:
                continue
            proc = d.procedimento_id or (sols[d.solicitacao_id].procedimento_id if d.solicitacao_id in sols else None)
            if not proc or d.motivo_codificado is None:
                continue
            motivo, por_llm = d.motivo_codificado, False
            if motivo == MotivoCodificado.OUTRO:
                motivo = self._classificar(d.justificativa)
                if motivo is None:
                    sem_grupo += 1
                    continue
                por_llm = True
                reclassificados += 1
            casos.append(CasoAprendizado(
                decisao_id=d.decisao_id, solicitacao_id=d.solicitacao_id, regulador_id=d.regulador_id,
                data=d.data, procedimento_id=proc, motivo=motivo, classe_de=d.classe_sugerida,
                classe_para=d.classe_decidida, justificativa=d.justificativa,
                reclassificado_por_llm=por_llm))

        geradas = agrupar(casos, self.referencia, self.params, onco)
        decididos = self.propostas.ids_decididos()
        geradas = [p for p in geradas if p.proposta_id not in decididos]
        self.propostas.substituir_geradas(geradas, self.relogio())
        self.uow.confirmar()
        return ResultadoGeracao(
            analisadas=len(todas), consideradas=len(casos), outros_reclassificados=reclassificados,
            outros_sem_grupo=sem_grupo,
            propostas=[p for p in geradas if p.status == "pendente"],
            descartadas=[p for p in geradas if p.status == "descartada"])

    def _classificar(self, texto: str | None) -> MotivoCodificado | None:
        if self.classificador is None or not (texto or "").strip():
            return None
        try:
            m = self.classificador.classificar(texto)
        except Exception:
            return None
        return None if m in (None, MotivoCodificado.OUTRO) else m
