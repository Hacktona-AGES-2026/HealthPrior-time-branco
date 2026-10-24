"""US-07 · Resolver pendência (C-06). Reprocessa ou remove com motivo; nada é apagado (I-03).

A pessoa escolhe uma resolução (confirmar saída, fundir, reativar, descartar ou, na PRE-12,
corrigir o CID, D-117) e o caso de uso:
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
from app.domain.correcao_cid import aplicar_correcao_cid
from app.domain.enums import ResolucaoPendencia as R
from app.domain.enums import ClasseStatus, StatusFila, StatusPendencia
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
    SwalisScorer,
    TabelaCid,
    UnidadeDeTrabalho,
)
from app.domain.preprocessing.inconsistencias import (
    ALERTA_POR_REGRA,
    ALERTA_SAIDA_A_CONFIRMAR,
    PRE_CANCER_ESCONDIDO,
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
                 recalcular_flags: RecalcularFlags | None = None, notificar=None,
                 tabela_cid: TabelaCid | None = None, scorer: SwalisScorer | None = None):
        self._notificar = notificar  # NotificarMudancas (demo)
        self._pendencias = pendencias
        self._solicitacoes = solicitacoes
        self._eventos = eventos
        self._correcoes = correcoes
        self._uow = uow
        self._publicar = publicar
        self._relogio = relogio
        self._recalcular_flags = recalcular_flags
        self._tabela_cid = tabela_cid
        self._scorer = scorer

    def executar(self, pendencia_id: str, resolucao: R, usuario_id: str,
                 observacao: str | None = None, fundir_com: str | None = None,
                 cid: str | None = None) -> ResultadoResolucao:
        try:
            status_fila = self._resolver(pendencia_id, resolucao, usuario_id, observacao, fundir_com, cid)
            self._uow.confirmar()
        except Exception:
            self._uow.desfazer()
            raise
        self._avisar_paciente(pendencia_id)
        return ResultadoResolucao(status_fila=status_fila, fila_publicada=self._republicar())

    def _avisar_paciente(self, pendencia_id: str) -> None:
        """Só pendência bloqueante muda a situação do paciente (sai, volta ou segue suspenso)."""
        if self._notificar is None:
            return
        p = self._pendencias.obter(pendencia_id)
        if p is not None and p.bloqueante and p.solicitacao_id:
            self._notificar.evento(p.solicitacao_id, "situacao")

    def _resolver(self, pendencia_id: str, resolucao: R, usuario_id: str,
                  observacao: str | None, fundir_com: str | None, cid: str | None = None) -> StatusFila | None:
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
        elif resolucao == R.CORRIGIR_CID:
            correcao = self._corrigir_cid(s, cid)
            correcoes = [correcao]
            p.observacao = f"CID corrigido: {correcao.original} -> {correcao.novo}" + (
                f". {p.observacao}" if p.observacao else "")
        self._pendencias.salvar(p)

        # 2) o que acontece com a solicitação
        if s is not None:
            if resolucao == R.CONFIRMAR_SAIDA:
                s.status_fila, s.motivo_status = StatusFila.REMOVIDA, p.regra  # D-90: o motivo é a regra
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
        """D-89: `fundir_com` permanece; a outra sai (`removida`), os eventos vão junto e a data mais antiga vale."""
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

    def _corrigir_cid(self, s: Solicitacao, cid: str | None) -> Correcao:
        """D-117: o regulador confirmou o CID (o sugerido ou outro). Vale para tudo dali em diante."""
        codigo = (cid or "").strip().upper()
        if not codigo:
            raise ResolucaoInvalidaError("Corrigir o CID exige o CID novo.")
        descricao = self._tabela_cid.descricao(codigo) if self._tabela_cid else None
        if descricao is None:
            raise ResolucaoInvalidaError(f"O CID {codigo} não existe na tabela CID-10.")
        if self._scorer is None:  # sem SWALIS não dá para congelar a classe (I-04): melhor falhar alto
            raise RuntimeError("corrigir_cid precisa do SWALIS (scorer) para proteger a classe em vigor")
        eventos = self._eventos.listar_por_solicitacao(s.solicitacao_id)
        antes = self._scorer.calcular(s, eventos).classe_sistema
        correcao = aplicar_correcao_cid(s, codigo, descricao)
        if self._scorer.calcular(s, eventos).classe_sistema != antes:
            # I-04: o CID novo pode mudar a classe sugerida; ela só vale com decisão do regulador.
            # Quem nunca foi confirmado fica com a classe anterior congelada (como no evento, C-08).
            if s.classe_status != ClasseStatus.CONFIRMADA and s.classe_vigente is None:
                s.classe_vigente = antes
                self._solicitacoes.salvar(s)
        self._solicitacoes.salvar_cid_confirmado(s)
        alerta = ALERTA_POR_REGRA[PRE_CANCER_ESCONDIDO]
        s.alertas = [a for a in s.alertas if a != alerta]  # o CID já foi revisto
        return correcao

    @staticmethod
    def _permanece(alteradas: list[Solicitacao], s: Solicitacao) -> Solicitacao:
        return alteradas[1] if alteradas else s

    def _reavaliar(self, s: Solicitacao, resolucao: R) -> None:
        """Mesma regra da detecção (D-82): quem manda é a pendência bloqueante que continua aberta."""
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
        except Exception:  # a resolução já foi confirmada: não esconder isso atrás de um 500 (D-91)
            log.exception("Resolução confirmada, mas a fila não foi republicada")
            return False
