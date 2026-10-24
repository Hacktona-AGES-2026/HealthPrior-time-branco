"""Notificações ao paciente (demo): enfileira nas mudanças que importam e envia por um canal (simulado ou Twilio).

Enfileirar é barato e fica na mesma transação da mudança; enviar é um passo à parte, com limite por rodada,
e nunca derruba a operação que o disparou (falha de envio fica registrada, a decisão/publicação vale).
Só texto genérico (domain/notificacoes.py) e só para o número da demo.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from app.domain.models import LinhaFila
from app.domain.notificacoes import (
    ENVIADA,
    FALHOU,
    POSICAO,
    Notificacao,
    mudancas_de_posicao,
    texto,
)
from app.domain.ports import NotificacaoRepository, Notificador, UnidadeDeTrabalho

log = logging.getLogger(__name__)


@dataclass
class ResultadoEnvios:
    enviadas: int = 0
    falhas: int = 0
    pendentes: int = 0  # ficaram para a próxima rodada (limite)


class EnviarNotificacoes:
    def __init__(self, repo: NotificacaoRepository, notificador: Notificador, uow: UnidadeDeTrabalho,
                 destino: str, limite: int, relogio: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self._repo, self._notificador, self._uow = repo, notificador, uow
        self._destino, self._limite, self._relogio = destino, limite, relogio

    def executar(self) -> ResultadoEnvios:
        r = ResultadoEnvios()
        if not self._destino and getattr(self._notificador, "exige_destino", True):
            return r  # sem número da demo não há para quem enviar
        for n in self._repo.pendentes(self._limite):
            res = self._notificador.enviar(self._destino, n.texto)
            self._repo.registrar_envio(n.notificacao_id, ENVIADA if res.ok else FALHOU, self._relogio(), res.detalhe)
            r.enviadas += res.ok
            r.falhas += not res.ok
        self._uow.confirmar()
        r.pendentes = len(self._repo.pendentes(10_000))
        return r


class NotificarMudancas:
    """Enfileira (e, se `enviar` for dado, tenta enviar) as notificações das mudanças da fila. Nunca levanta."""

    def __init__(self, repo: NotificacaoRepository, uow: UnidadeDeTrabalho, canal: str,
                 min_posicoes: int, max_por_publicacao: int,
                 enviar: EnviarNotificacoes | None = None,
                 relogio: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self._repo, self._uow, self._canal = repo, uow, canal
        self._min, self._max, self._enviar, self._relogio = min_posicoes, max_por_publicacao, enviar, relogio

    def fila_publicada(self, antes: list[LinhaFila], depois: list[LinhaFila]) -> None:
        if not antes:  # primeira publicação: não há "mudou de lugar"
            return
        mud = mudancas_de_posicao({l.solicitacao_id: l.posicao for l in antes},
                                  {l.solicitacao_id: l.posicao for l in depois}, self._min, self._max)
        self._guardar([(sid, POSICAO, subiu) for sid, subiu in mud])

    def evento(self, solicitacao_id: str, motivo: str) -> None:
        self._guardar([(solicitacao_id, motivo, None)])

    def enfileirar(self, solicitacao_ids: list[str], motivo: str) -> None:
        """Só enfileira (sem commit nem envio): para quem já tem a própria transação em curso."""
        for sid in sorted(solicitacao_ids)[: self._max]:  # demo: nunca uma enxurrada
            self._adicionar(sid, motivo, None)

    def _adicionar(self, sid: str, motivo: str, subiu: bool | None) -> None:
        if self._repo.existe_pendente(sid, motivo):  # não empilha o mesmo aviso
            return
        self._repo.adicionar(Notificacao(self._repo.proximo_id(), sid, motivo, texto(motivo, sid, subiu),
                                         self._canal, criada_em=self._relogio()))

    def _guardar(self, itens: list[tuple[str, str, bool | None]]) -> None:
        try:
            for sid, motivo, subiu in itens:
                self._adicionar(sid, motivo, subiu)
            self._uow.confirmar()
            if self._enviar is not None:  # também esvazia o que outros passos deixaram pendente
                self._enviar.executar()
        except Exception:  # a operação que disparou já valeu; aviso perdido não pode derrubá-la
            log.exception("falha ao registrar ou enviar notificações")
            self._uow.desfazer()
