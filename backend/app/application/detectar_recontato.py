"""US-17 · Recontato (C-04, passo 3 do C-13): pendência para quem está sem evento há N dias (I-08).

Só quem está ativo na fila. Idempotente: abre as que faltam, atualiza os dias das abertas e encerra
("sistema") as que deixaram de valer, por exemplo quando o retorno do contato virou um evento. Não
confirma a transação, nem altera classe, score ou posição.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from app.domain.models import Evento, Pendencia, ResultadoSincronizacao
from app.domain.ports import EventoRepository, PendenciaRepository, SolicitacaoRepository
from app.domain.recontato import REC_SEM_EVENTO, detectar_recontato


@dataclass
class ResumoRecontato:
    avaliadas: int = 0
    sem_evento: int = 0  # quantas passaram do limite
    n_dias: int = 0
    pendencias: ResultadoSincronizacao = field(default_factory=ResultadoSincronizacao)


class DetectarRecontato:
    def __init__(self, solicitacoes: SolicitacaoRepository, eventos: EventoRepository,
                 pendencias: PendenciaRepository, hoje: date, n_dias: int, notificar=None):
        self._notificar = notificar  # NotificarMudancas (demo): só enfileira quem ganhou pendência hoje
        self._solicitacoes, self._eventos, self._pendencias = solicitacoes, eventos, pendencias
        self._hoje, self._n_dias = hoje, n_dias  # data de referência (REF), nunca date.today()

    def executar(self) -> ResumoRecontato:
        ativas = self._solicitacoes.listar(apenas_ativas=True)
        por_sol: dict[str, list[Evento]] = defaultdict(list)
        for e in self._eventos.listar_todos():
            por_sol[e.solicitacao_id].append(e)
        pendencias = []
        for s in ativas:
            a = detectar_recontato(s, por_sol.get(s.solicitacao_id, []), self._hoje, self._n_dias)
            if a is not None:
                pendencias.append(Pendencia(
                    pendencia_id="", solicitacao_id=s.solicitacao_id, regra=a.regra, titulo=a.titulo,
                    bloqueante=False, evidencias=a.evidencias, acao_sugerida=a.acao_sugerida,
                    aberta_em=self._hoje))
        antes = self._pendencias.chaves_abertas((REC_SEM_EVENTO,)) if self._notificar else set()
        sincronizadas = self._pendencias.sincronizar((REC_SEM_EVENTO,), pendencias)
        if self._notificar is not None:
            novas = {sid for sid, _ in self._pendencias.chaves_abertas((REC_SEM_EVENTO,)) - antes}
            self._notificar.enfileirar(sorted(novas), "recontato")
        return ResumoRecontato(len(ativas), len(pendencias), self._n_dias, sincronizadas)
