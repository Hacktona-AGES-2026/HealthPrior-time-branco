"""US-07 · Resolver pendência (C-06). Reprocessa ou remove com motivo; nada é apagado (I-03)."""
from __future__ import annotations

from app.domain.enums import ResolucaoPendencia


class ResolverPendencia:
    def __init__(self, pendencias, solicitacoes, gerar_fila):
        self._pendencias = pendencias
        self._solicitacoes = solicitacoes
        self._gerar_fila = gerar_fila

    def executar(self, pendencia_id: str, resolucao: ResolucaoPendencia, usuario_id: str,
                 observacao: str | None = None, fundir_com: str | None = None) -> str:
        """TODO(US-07). Retorna o novo status_fila."""
        raise NotImplementedError("US-07: ResolverPendencia.executar")
