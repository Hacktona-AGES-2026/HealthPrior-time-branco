"""US-05 · Inconsistências não bloqueantes (C-05/C-06, PRE-10..PRE-15).

O paciente segue ativo: o achado vira alerta em `alertas` (PRE-10..15) e, em PRE-10..13, também uma
pendência não bloqueante (D-46). Idempotente: refaz só os alertas e as pendências automáticas
dessas regras, sem tocar nos dados originais nem em alertas de outras regras. Não confirma a
transação (ver UnidadeDeTrabalho): a carga confirma tudo junto.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date

from app.domain.models import Evento, Pendencia, ResultadoSincronizacao
from app.domain.ports import EventoRepository, PendenciaRepository, SolicitacaoRepository
from app.domain.preprocessing.inconsistencias import (
    ALERTA_POR_REGRA,
    ALERTAS_NAO_BLOQUEANTES,
    REGRAS_COM_PENDENCIA,
    detectar_nao_bloqueantes,
)


@dataclass
class ResumoInconsistencias:
    solicitacoes: int = 0
    alertas: dict[str, int] = field(default_factory=dict)  # por regra (PRE-xx)
    pendencias: ResultadoSincronizacao = field(default_factory=ResultadoSincronizacao)


class DetectarInconsistencias:
    def __init__(self, solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 pendencias: PendenciaRepository, hoje: date):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._pendencias = pendencias
        self._hoje = hoje  # data de referência (REF), nunca date.today()

    def executar(self) -> ResumoInconsistencias:
        solicitacoes = self._solicitacoes.listar(apenas_ativas=False)
        por_solicitacao: dict[str, list[Evento]] = defaultdict(list)
        for e in self._eventos.listar_todos():
            por_solicitacao[e.solicitacao_id].append(e)

        contagem: Counter = Counter()
        pendencias: list[Pendencia] = []
        for s in solicitacoes:
            achados = detectar_nao_bloqueantes(s, por_solicitacao.get(s.solicitacao_id, []))
            # Troca só os alertas desta US; os de outras regras ficam.
            s.alertas = [a for a in s.alertas if a not in ALERTAS_NAO_BLOQUEANTES] + [
                ALERTA_POR_REGRA[a.regra] for a in achados]
            contagem.update(a.regra for a in achados)
            pendencias.extend(
                Pendencia(pendencia_id="", solicitacao_id=s.solicitacao_id, regra=a.regra,
                          titulo=a.titulo, bloqueante=False, evidencias=a.evidencias,
                          acao_sugerida=a.acao_sugerida, aberta_em=self._hoje)
                for a in achados if a.regra in REGRAS_COM_PENDENCIA
            )

        self._solicitacoes.salvar_alertas(solicitacoes)
        sincronizadas = self._pendencias.sincronizar(REGRAS_COM_PENDENCIA, pendencias)
        return ResumoInconsistencias(solicitacoes=len(solicitacoes), alertas=dict(contagem),
                                     pendencias=sincronizadas)
