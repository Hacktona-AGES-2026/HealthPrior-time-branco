"""US-19 · Comitê clínico: ver a proposta, os casos de origem e o impacto simulado; aprovar ou rejeitar (C-14)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from app.domain.aprendizado import PropostaRegra
from app.domain.enums import ClasseStatus, StatusFila
from app.domain.errors import (
    DecisaoPropostaInvalidaError,
    ObservacaoObrigatoriaError,
    PropostaJaDecididaError,
    PropostaNaoEncontradaError,
    RegraJaRevertidaError,
    RegraNaoEncontradaError,
)
from app.domain.models import Decisao
from app.domain.ports import (
    DecisaoRepository,
    EventoRepository,
    PropostaRepository,
    RegraRepository,
    SolicitacaoRepository,
    SwalisScorer,
    UnidadeDeTrabalho,
)
from app.domain.regras_aprendidas import Impacto, RegraAprendida, RegraRegistrada, aplicar_regras, simular_impacto


@dataclass
class PropostaDetalhe:
    proposta: PropostaRegra
    casos_origem: list[Decisao]
    impacto: Impacto | None  # só nas pendentes (shadow run)
    versao: int | None  # versão de regras criada, nas aprovadas e revertidas
    reversao: RegraRegistrada | None = None  # quem reverteu, quando e por quê


@dataclass
class ResultadoDecisaoProposta:
    proposta_id: str
    status: str
    versao: int | None
    versao_regras: str | None
    enviados_ao_inbox: int


def _regra(p: PropostaRegra, versao: int) -> RegraAprendida:
    return RegraAprendida(p.proposta_id, p.procedimento_id, p.classe_de, p.classe_para, versao)


class _Base:
    def __init__(self, propostas: PropostaRepository, regras: RegraRepository,
                 solicitacoes: SolicitacaoRepository, eventos: EventoRepository, scorer: SwalisScorer):
        self._propostas, self._regras = propostas, regras
        self._solicitacoes, self._eventos, self._scorer = solicitacoes, eventos, scorer

    def _candidatas(self):
        """Solicitações ativas com a classe que o SWALIS dá hoje (já com as regras em vigor)."""
        ativas = self._solicitacoes.listar(apenas_ativas=True)
        por_sol: dict[str, list] = {}
        for e in self._eventos.listar_todos():
            por_sol.setdefault(e.solicitacao_id, []).append(e)
        return [(s, self._scorer.calcular(s, por_sol.get(s.solicitacao_id, [])).classe_sistema)
                for s in ativas]


class ListarPropostas(_Base):
    def __init__(self, propostas, regras, solicitacoes, eventos, scorer, decisoes: DecisaoRepository):
        super().__init__(propostas, regras, solicitacoes, eventos, scorer)
        self._decisoes = decisoes

    def executar(self, status: str | None = None) -> list[PropostaDetalhe]:
        propostas = self._propostas.listar(status)
        log = {d.decisao_id: d for d in self._decisoes.listar_todas()}
        regras = {r.regra.regra_id: r for r in self._regras.listar_todas()}
        candidatas = self._candidatas() if any(p.status == "pendente" for p in propostas) else []
        saida = []
        for p in propostas:
            impacto = simular_impacto(candidatas, _regra(p, 0)) if p.status == "pendente" else None
            reg = regras.get(p.proposta_id)
            saida.append(PropostaDetalhe(
                p, [log[c] for c in p.casos if c in log], impacto, reg.regra.versao if reg else None,
                reg if reg and not reg.ativa else None))
        return saida


class DecidirProposta(_Base):
    def __init__(self, propostas, regras, solicitacoes, eventos, scorer, uow: UnidadeDeTrabalho,
                 relogio: Callable[[], datetime]):
        super().__init__(propostas, regras, solicitacoes, eventos, scorer)
        self._uow, self._relogio = uow, relogio

    def executar(self, proposta_id: str, decisao: str, usuario_id: str,
                 observacao: str | None = None) -> ResultadoDecisaoProposta:
        if decisao not in ("aprovar", "rejeitar"):
            raise DecisaoPropostaInvalidaError("decisao deve ser \"aprovar\" ou \"rejeitar\".")
        if not usuario_id.strip():
            raise DecisaoPropostaInvalidaError("usuario_id é obrigatório.")
        p = self._propostas.obter(proposta_id)
        if p is None:
            raise PropostaNaoEncontradaError(f"Proposta {proposta_id} não encontrada.")
        if p.status != "pendente":
            raise PropostaJaDecididaError(f"A proposta {proposta_id} está {p.status}: não vai ao comitê.")
        obs = (observacao or "").strip() or None
        if decisao == "rejeitar" and obs is None:
            raise ObservacaoObrigatoriaError("Rejeitar a proposta exige o motivo em texto.")
        agora = self._relogio()
        try:
            if decisao == "rejeitar":
                self._propostas.registrar_decisao(proposta_id, "rejeitada", usuario_id, agora, obs)
                self._uow.confirmar()
                return ResultadoDecisaoProposta(proposta_id, "rejeitada", None, None, 0)

            versao = self._regras.proxima_versao()
            regra = _regra(p, versao)
            candidatas = self._candidatas()  # antes de a regra entrar: é o que "mudaria"
            impacto = simular_impacto(candidatas, regra)
            self._regras.adicionar(regra, usuario_id, agora)
            self._propostas.registrar_decisao(proposta_id, "aprovada", usuario_id, agora, obs)
            # C-08: a nova sugerida passa pelo regulador. Quem não foi confirmado fica com a classe
            # anterior congelada (como no evento novo, D-75) e aparece no inbox.
            classes = {s.solicitacao_id: c for s, c in candidatas}
            enviados = 0
            for sid in impacto.ids:
                s = self._solicitacoes.obter(sid)
                if (s.status_fila == StatusFila.ATIVA and s.classe_status != ClasseStatus.CONFIRMADA
                        and s.classe_vigente is None):
                    s.classe_vigente = classes[sid]
                    self._solicitacoes.salvar(s)
                    enviados += 1
            self._uow.confirmar()
        except Exception:
            self._uow.desfazer()
            raise
        versao_regras = f"{self._scorer.versao_regras.split('+aprendizado-v')[0]}+aprendizado-v{versao}"
        return ResultadoDecisaoProposta(proposta_id, "aprovada", versao, versao_regras, enviados)


@dataclass
class ResultadoReversao:
    regra_id: str
    status: str
    versao_regras: str
    devolvidos_ao_inbox: int


class ReverterRegra:
    """US-19 (C-14: "versionada; reversível"). Desativa a regra e desfaz o que a aprovação pôs no inbox.

    `scorer_base` é o SWALIS sem regras aprendidas: com ele se vê o que cada paciente passaria a ter
    sem esta regra (as outras seguem valendo).
    """

    def __init__(self, propostas: PropostaRepository, regras: RegraRepository,
                 solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 scorer_base: SwalisScorer, uow: UnidadeDeTrabalho, relogio: Callable[[], datetime]):
        self._propostas, self._regras = propostas, regras
        self._solicitacoes, self._eventos, self._scorer = solicitacoes, eventos, scorer_base
        self._uow, self._relogio = uow, relogio

    def executar(self, regra_id: str, usuario_id: str, motivo: str | None) -> ResultadoReversao:
        if not usuario_id.strip():
            raise DecisaoPropostaInvalidaError("usuario_id é obrigatório.")
        reg = self._regras.obter(regra_id)
        if reg is None:
            raise RegraNaoEncontradaError(f"Regra {regra_id} não encontrada.")
        if not reg.ativa:
            raise RegraJaRevertidaError(f"A regra {regra_id} já foi revertida.")
        texto = (motivo or "").strip()
        if not texto:
            raise ObservacaoObrigatoriaError("Reverter a regra exige o motivo em texto.")
        restantes = [r for r in self._regras.listar_ativas() if r.regra_id != regra_id]
        agora = self._relogio()
        try:
            self._regras.desativar(regra_id, usuario_id, agora, texto)
            self._propostas.marcar(regra_id, "revertida")
            devolvidos = 0
            por_sol: dict[str, list] = {}
            for e in self._eventos.listar_todos():
                por_sol.setdefault(e.solicitacao_id, []).append(e)
            for s in self._solicitacoes.listar(apenas_ativas=True):
                if (s.procedimento_id != reg.regra.procedimento_id or s.classe_vigente is None
                        or s.classe_status == ClasseStatus.CONFIRMADA):
                    continue
                base = self._scorer.calcular(s, por_sol.get(s.solicitacao_id, [])).classe_sistema
                sugerida, _ = aplicar_regras(s, base, restantes)
                if sugerida == s.classe_vigente:  # sem a regra não há mais divergência: some do inbox
                    s.classe_vigente = None
                    self._solicitacoes.salvar(s)
                    devolvidos += 1
            self._uow.confirmar()
        except Exception:
            self._uow.desfazer()
            raise
        v = max((r.versao for r in restantes), default=0)
        base_versao = self._scorer.versao_regras
        return ResultadoReversao(regra_id, "revertida",
                                 f"{base_versao}+aprendizado-v{v}" if v else base_versao, devolvidos)
