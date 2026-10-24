"""US-07 · Resolver pendência (C-06). Reprocessa ou remove com motivo; nada é apagado (I-03).

A pessoa escolhe uma resolução (confirmar saída, fundir, reativar ou descartar) e o caso de uso:
  1. valida (a regra aceita essa resolução? `confirmar_saida` tem observação?);
  2. grava o desfecho da pendência (quem, quando, resolução, observação) e muda a solicitação:
     `removida` com motivo (confirmar saída e fusão) ou de volta à fila (reativar e descartar);
  3. **confirma a transação**; só então
  4. recalcula e publica a fila (US-09/10). A publicação desfaz a *própria* transação quando o
     verificador reprova, por isso não pode dividir a transação da resolução: se ela falhar, a
     pendência continua resolvida e a fila anterior segue publicada (I-07, `fila_publicada=false`).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from app.application.publicar_fila import PublicarFila
from app.application.recalcular_flags import RecalcularFlags
from app.domain.cid import is_oncologico
from app.domain.enums import ResolucaoPendencia as R
from app.domain.enums import StatusFila, StatusPendencia
from app.domain.errors import (
    PendenciaJaResolvidaError,
    PendenciaNaoEncontradaError,
    ResolucaoInvalidaError,
)
from app.domain.models import Correcao, Pendencia, Solicitacao
from app.domain.pendencias import STATUS_DA_PENDENCIA, fundir, validar_resolucao
from app.domain.ports import (
    CorrecaoRepository,
    EventoRepository,
    PendenciaRepository,
    SolicitacaoRepository,
    UnidadeDeTrabalho,
)
from app.domain.preprocessing.inconsistencias import (
    ALERTA_SAIDA_A_CONFIRMAR,
    PRE_DUPLICATA,
    PRE_EVENTO_ORFAO,
    REGRAS_DE_SOLICITACAO,
)

log = logging.getLogger(__name__)


@dataclass
class ResultadoResolucao:
    status_fila: StatusFila | None  # da solicitação da pendência; None quando não há (PRE-24, evento órfão)
    fila_publicada: bool


class ResolverPendencia:
    def __init__(self, pendencias: PendenciaRepository, solicitacoes: SolicitacaoRepository,
                 eventos: EventoRepository, correcoes: CorrecaoRepository, uow: UnidadeDeTrabalho,
                 publicar: PublicarFila, relogio: Callable[[], datetime],
                 recalcular_flags: RecalcularFlags | None = None):
        self._pendencias = pendencias
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._correcoes = correcoes
        self._uow = uow
        self._publicar = publicar
        self._relogio = relogio
        self._recalcular_flags = recalcular_flags

    def executar(self, pendencia_id: str, resolucao: R, usuario_id: str,
                 observacao: str | None = None, fundir_com: str | None = None) -> ResultadoResolucao:
        try:
            status_fila = self._resolver(pendencia_id, resolucao, usuario_id, observacao, fundir_com)
            self._uow.confirmar()
        except Exception:
            self._uow.desfazer()
            raise
        return ResultadoResolucao(status_fila=status_fila, fila_publicada=self._republicar())

    def _resolver(self, pendencia_id: str, resolucao: R, usuario_id: str,
                  observacao: str | None, fundir_com: str | None) -> StatusFila | None:
        p = self._pendencias.obter(pendencia_id)
        if p is None:
            raise PendenciaNaoEncontradaError(f"Pendência {pendencia_id} não encontrada.")
        if p.status != StatusPendencia.ABERTA:
            raise PendenciaJaResolvidaError(
                f"{pendencia_id} já está {p.status.value} (por {p.resolvido_por or 'sistema'}).")
        validar_resolucao(p.regra, resolucao, observacao)

        s = self._solicitacoes.obter(p.solicitacao_id)
        if s is None and p.regra != PRE_EVENTO_ORFAO:
            raise PendenciaNaoEncontradaError(f"A solicitação {p.solicitacao_id} da pendência não existe.")

        # 1) o desfecho da pendência vale antes de reavaliar a solicitação (ela deixa de contar como aberta)
        p.status = STATUS_DA_PENDENCIA[resolucao]
        p.resolvido_por, p.resolvido_em, p.resolucao = usuario_id, self._relogio(), resolucao.value
        p.observacao = (observacao or "").strip() or None
        alteradas: list[Solicitacao] = []
        correcoes: list[Correcao] = []
        if resolucao == R.FUNDIR:
            alteradas, correcoes = self._fundir(p, s, fundir_com)
            p.observacao = f"Fundida com {self._permanece(alteradas, s).solicitacao_id}" + (
                f". {p.observacao}" if p.observacao else "")
        self._pendencias.salvar(p)

        # 2) o que acontece com a solicitação
        if s is not None:
            if resolucao == R.CONFIRMAR_SAIDA:
                s.status_fila, s.motivo_status = StatusFila.REMOVIDA, p.regra  # D-65: o motivo é a regra
            for sol in alteradas or [s]:
                if sol.status_fila != StatusFila.REMOVIDA or resolucao == R.REATIVAR:
                    self._reavaliar(sol, resolucao)
                else:  # saiu da fila: não há mais saída a confirmar
                    sol.alertas = [a for a in sol.alertas if a != ALERTA_SAIDA_A_CONFIRMAR]
            self._solicitacoes.atualizar_status(alteradas or [s])
            self._solicitacoes.salvar_alertas(alteradas or [s])
        if correcoes:
            self._correcoes.adicionar_varias(correcoes)
        if resolucao == R.FUNDIR and self._recalcular_flags is not None:
            self._recalcular_flags.executar()  # eventos e data de entrada mudaram: refaz piora e histórico
        return s.status_fila if s is not None else None

    def _fundir(self, p: Pendencia, s: Solicitacao | None, fundir_com: str | None
                ) -> tuple[list[Solicitacao], list[Correcao]]:
        """D-64: `fundir_com` permanece; a outra sai (`removida`), os eventos vão junto e a data mais antiga vale."""
        outras = [m.ref for m in p.evidencias if m.fonte == "solicitacao" and m.ref and m.ref != s.solicitacao_id]
        outra = self._solicitacoes.obter(outras[0]) if outras else None
        if outra is None:
            raise ResolucaoInvalidaError("A pendência não aponta a outra solicitação duplicada.")
        permanece_id = fundir_com or outra.solicitacao_id
        if permanece_id not in (s.solicitacao_id, outra.solicitacao_id):
            raise ResolucaoInvalidaError(
                f"fundir_com deve ser {s.solicitacao_id} ou {outra.solicitacao_id}, as duas duplicadas.")
        permanece, removida = (outra, s) if permanece_id == outra.solicitacao_id else (s, outra)
        data_antes = permanece.data_entrada_fila
        correcoes = fundir(permanece, removida)
        movidos = self._eventos.mover(removida.solicitacao_id, permanece.solicitacao_id)
        correcoes += [Correcao(permanece.solicitacao_id, f"evento:{evento_id}.solicitacao_id",
                               removida.solicitacao_id, permanece.solicitacao_id, PRE_DUPLICATA)
                      for evento_id in movidos]
        if permanece.data_entrada_fila != data_antes:
            self._solicitacoes.atualizar_data_entrada(permanece)
        return [removida, permanece], correcoes

    @staticmethod
    def _permanece(alteradas: list[Solicitacao], s: Solicitacao) -> Solicitacao:
        return alteradas[1] if alteradas else s

    def _reavaliar(self, s: Solicitacao, resolucao: R) -> None:
        """Mesma regra da detecção (D-57): quem manda é a pendência bloqueante que continua aberta."""
        abertas = sorted(regra for sid, regra in self._pendencias.chaves_abertas(REGRAS_DE_SOLICITACAO)
                         if sid == s.solicitacao_id)
        suspensa_por_regra = s.status_fila == StatusFila.SUSPENSA and s.motivo_status in REGRAS_DE_SOLICITACAO
        if abertas and not is_oncologico(s.cid_principal):
            if s.status_fila in (StatusFila.ATIVA, StatusFila.SUSPENSA) or resolucao == R.REATIVAR:
                s.status_fila, s.motivo_status = StatusFila.SUSPENSA, abertas[0]
        elif suspensa_por_regra or (s.status_fila == StatusFila.REMOVIDA and resolucao == R.REATIVAR):
            s.status_fila, s.motivo_status = StatusFila.ATIVA, None  # volta ao fluxo normal
        if not abertas:
            s.alertas = [a for a in s.alertas if a != ALERTA_SAIDA_A_CONFIRMAR]

    def _republicar(self) -> bool:
        try:
            return self._publicar.executar().publicada
        except Exception:  # a resolução já foi confirmada: não esconder isso atrás de um 500 (D-66)
            log.exception("Resolução confirmada, mas a fila não foi republicada")
            return False
