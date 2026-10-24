"""US-04 · Inconsistências bloqueantes (C-05/C-06, PRE-20..PRE-25).

Duplicata, saída da fila (operou fora, convênio, desistência), fontes contraditórias e evento
órfão. Cada achado vira uma pendência **bloqueante**; enquanto ela estiver aberta, a solicitação
fica `suspensa` com o motivo (PRE-xx) e sai da fila priorizada. Oncológico nunca é suspenso sem
confirmação humana (I-02): fica ativo, com o alerta `saida_a_confirmar`. Nada é apagado (I-03).

Idempotente. Quem decide é a pendência: uma resolvida ou descartada por pessoa não suspende de
novo; se o achado sumiu, a pendência é encerrada e a suspensão automática é desfeita. Só mexe em
suspensão cujo motivo é uma regra desta US (nunca em `removida`). Não confirma a transação
(ver UnidadeDeTrabalho): a carga confirma tudo junto.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date

from app.domain.cid import is_oncologico
from app.domain.enums import StatusFila
from app.domain.models import Evento, Pendencia, ResultadoSincronizacao, Solicitacao
from app.domain.ports import EventoRepository, PendenciaRepository, SolicitacaoRepository
from app.domain.preprocessing.inconsistencias import (
    ALERTA_SAIDA_A_CONFIRMAR,
    REGRAS_BLOQUEANTES,
    REGRAS_DE_SOLICITACAO,
    detectar_bloqueantes,
    detectar_eventos_orfaos,
)


@dataclass
class ResumoBloqueantes:
    solicitacoes: int = 0
    achados: dict[str, int] = field(default_factory=dict)  # por regra (PRE-xx)
    suspensas: int = 0               # suspensas ao fim da execução
    reativadas: int = 0              # suspensão automática desfeita nesta execução
    oncologicas_a_confirmar: int = 0  # com achado, mas ativas (I-02)
    eventos_orfaos: int = 0
    pendencias: ResultadoSincronizacao = field(default_factory=ResultadoSincronizacao)


class DetectarBloqueantes:
    def __init__(self, solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 pendencias: PendenciaRepository, hoje: date):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._pendencias = pendencias
        self._hoje = hoje  # data de referência (REF), nunca date.today()

    def executar(self) -> ResumoBloqueantes:
        solicitacoes = self._solicitacoes.listar(apenas_ativas=False)
        ids = {s.solicitacao_id for s in solicitacoes}
        eventos = self._eventos.listar_todos()

        por_solicitacao: dict[str, list[Evento]] = defaultdict(list)
        for e in eventos:
            e.orfao = e.solicitacao_id not in ids  # PRE-24: não é aplicado
            por_solicitacao[e.solicitacao_id].append(e)
        por_paciente: dict[str, list[Solicitacao]] = defaultdict(list)
        for s in solicitacoes:
            por_paciente[s.paciente_id].append(s)

        contagem: Counter = Counter()
        pendencias: list[Pendencia] = []
        for s in solicitacoes:
            for a in detectar_bloqueantes(s, por_solicitacao.get(s.solicitacao_id, []), por_paciente[s.paciente_id]):
                contagem[a.regra] += 1
                pendencias.append(self._pendencia(s.solicitacao_id, a))
        orfaos = detectar_eventos_orfaos(eventos, ids)
        for sid, a in orfaos.items():
            contagem[a.regra] += 1
            pendencias.append(self._pendencia(sid, a))

        self._eventos.atualizar_marcas(eventos)
        sincronizadas = self._pendencias.sincronizar(REGRAS_BLOQUEANTES, pendencias)
        abertas = self._pendencias.chaves_abertas(REGRAS_DE_SOLICITACAO)

        resumo = ResumoBloqueantes(solicitacoes=len(solicitacoes), achados=dict(contagem),
                                   eventos_orfaos=sum(len(a.evidencias) for a in orfaos.values()),
                                   pendencias=sincronizadas)
        self._aplicar_status(solicitacoes, abertas, resumo)
        self._solicitacoes.atualizar_status(solicitacoes)
        self._solicitacoes.salvar_alertas(solicitacoes)
        return resumo

    def _pendencia(self, solicitacao_id: str, achado) -> Pendencia:
        return Pendencia(pendencia_id="", solicitacao_id=solicitacao_id, regra=achado.regra,
                         titulo=achado.titulo, bloqueante=True, evidencias=achado.evidencias,
                         acao_sugerida=achado.acao_sugerida, aberta_em=self._hoje)

    def _aplicar_status(self, solicitacoes: list[Solicitacao], abertas: set[tuple[str, str]],
                        resumo: ResumoBloqueantes) -> None:
        regras_abertas: dict[str, list[str]] = defaultdict(list)
        for sid, regra in sorted(abertas):
            regras_abertas[sid].append(regra)

        for s in solicitacoes:
            s.alertas = [a for a in s.alertas if a != ALERTA_SAIDA_A_CONFIRMAR]
            bloqueios = regras_abertas.get(s.solicitacao_id, [])
            oncologico = is_oncologico(s.cid_principal)  # sempre pelo CID (I-09)
            suspensa_por_nos = s.status_fila == StatusFila.SUSPENSA and s.motivo_status in REGRAS_DE_SOLICITACAO

            if bloqueios and oncologico:
                s.alertas.append(ALERTA_SAIDA_A_CONFIRMAR)  # I-02: fica ativo até alguém confirmar
                resumo.oncologicas_a_confirmar += 1
            if bloqueios and not oncologico and (s.status_fila == StatusFila.ATIVA or suspensa_por_nos):
                s.status_fila, s.motivo_status = StatusFila.SUSPENSA, bloqueios[0]
            elif suspensa_por_nos and (not bloqueios or oncologico):
                s.status_fila, s.motivo_status = StatusFila.ATIVA, None  # achado sumiu / nunca suspender onco
                resumo.reativadas += 1
            if s.status_fila == StatusFila.SUSPENSA:
                resumo.suspensas += 1
