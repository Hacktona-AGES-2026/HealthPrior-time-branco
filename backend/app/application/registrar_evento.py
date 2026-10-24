"""US-15 · Registrar evento novo (C-03, C-08).

Evento -> pré-processamento (PRE-07/08, flags) -> SWALIS -> desfecho:
- pendencia: o evento indica saída da fila (desistência, operou em outro serviço) -> call center;
- enviado_inbox: a classe sugerida mudou e o paciente entra na regra do inbox (US-12);
- registrado: só grava; a ordenação é refeita na próxima publicação (D-02).
Não republica a fila: a posição muda quando o regulador decide ou na atualização diária.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Callable

from app.domain.enums import Classe, DesfechoEvento, TipoEvento
from app.domain.errors import EventoInvalidoError, NaoEncontradoError
from app.domain.inbox import entra_no_inbox
from app.domain.models import Evento, Motivo, Pendencia
from app.domain.ports import (
    EventoRepository,
    PendenciaRepository,
    SolicitacaoRepository,
    SwalisScorer,
    UnidadeDeTrabalho,
)
from app.domain.preprocessing.flags import marcar_eventos, recalcular_flags

# Resultado de contato que indica saída da fila (PRE-21/22 e PRE-23). Bloqueante: humano confirma.
SAIDA_POR_CONTATO = {
    "informou_cirurgia_outro_servico": ("PRE-21", "Informou cirurgia em outro serviço",
                                        "Confirmar com o paciente e registrar a saída"),
    "desistiu": ("PRE-23", "Paciente desistiu da cirurgia",
                 "Ligar para confirmar a desistência e registrar a saída"),
}


@dataclass
class NovoEvento:
    solicitacao_id: str
    data_evento: date
    tipo_evento: str
    resultado: str | None = None
    valor_numerico: float | None = None
    descricao: str = ""
    origem: str | None = None


@dataclass
class ResultadoEvento:
    evento_id: str
    desfecho: DesfechoEvento
    classe_antes: Classe | None
    classe_depois: Classe | None
    pendencia_id: str | None = None


class RegistrarEvento:
    def __init__(self, solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 scorer: SwalisScorer, pendencias: PendenciaRepository, uow: UnidadeDeTrabalho,
                 gerar_id: Callable[[], str] = lambda: f"EVT-N{uuid.uuid4().hex[:8].upper()}"):
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._scorer = scorer
        self._pendencias = pendencias
        self._uow = uow
        self._gerar_id = gerar_id

    def executar(self, n: NovoEvento) -> ResultadoEvento:
        if n.tipo_evento not in TipoEvento._value2member_map_:
            raise EventoInvalidoError(f"tipo_evento desconhecido: {n.tipo_evento}")
        s = self._solicitacoes.obter(n.solicitacao_id)
        if s is None:
            raise NaoEncontradoError(f"Solicitação {n.solicitacao_id} não encontrada.")

        anteriores = self._eventos.listar_por_solicitacao(s.solicitacao_id)
        antes = self._scorer.calcular(s, anteriores).classe_sistema
        evento = Evento(evento_id=self._gerar_id(), solicitacao_id=s.solicitacao_id,
                        paciente_id=s.paciente_id, data_evento=n.data_evento,
                        tipo_evento=n.tipo_evento, resultado=n.resultado,
                        valor_numerico=n.valor_numerico, descricao=n.descricao or "",
                        origem=n.origem)
        todos = marcar_eventos(s, anteriores + [evento])  # PRE-07 (duplicado) e PRE-08 (histórico)
        self._eventos.adicionar(evento)
        recalcular_flags(s, todos)  # PRE-06: piora pelo evento novo
        self._solicitacoes.atualizar_flags([s])
        depois = self._scorer.calcular(s, todos).classe_sistema

        pendencia_id = None
        saida = SAIDA_POR_CONTATO.get(n.resultado or "") if n.tipo_evento == "contato_telefonico" else None
        if saida and not evento.duplicado_de:
            regra, titulo, acao = saida
            p = Pendencia(pendencia_id="", solicitacao_id=s.solicitacao_id, regra=regra,
                          titulo=titulo, bloqueante=True,
                          evidencias=[Motivo(n.resultado, n.descricao or titulo, "evento",
                                             ref=evento.evento_id, data=n.data_evento)],
                          acao_sugerida=acao, aberta_em=n.data_evento)
            self._pendencias.salvar(p)
            pendencia_id = p.pendencia_id
            desfecho = DesfechoEvento.PENDENCIA
        elif depois != antes and entra_no_inbox(depois, s.classe_status, s.classe_confirmada,
                                                 s.prioridade_norm):
            desfecho = DesfechoEvento.ENVIADO_INBOX
        else:
            desfecho = DesfechoEvento.REGISTRADO
        self._uow.confirmar()
        return ResultadoEvento(evento.evento_id, desfecho, antes, depois, pendencia_id)
