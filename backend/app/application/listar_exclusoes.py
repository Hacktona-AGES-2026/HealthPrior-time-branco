"""US-11 · Lista quem ficou fora da fila e confere com a cobertura do verificador."""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.exclusoes import GrupoExclusao, agrupar_exclusoes
from app.domain.ports import FilaRepository, SolicitacaoRepository


@dataclass
class ResultadoExclusoes:
    grupos: list[GrupoExclusao]
    total: int  # solicitações no banco
    fora: int  # solicitações que não estão ativas
    publicadas: int | None  # linhas da fila publicada; None se ainda não há publicação

    @property
    def confere(self) -> bool | None:
        """O verificador avisa `total - linhas do arquivo`: tem de ser igual ao que a tabela lista."""
        if self.publicadas is None:
            return None
        return self.total - self.publicadas == self.fora


class ListarExclusoes:
    def __init__(self, solicitacoes: SolicitacaoRepository, fila: FilaRepository):
        self._solicitacoes = solicitacoes
        self._fila = fila

    def executar(self) -> ResultadoExclusoes:
        todas = self._solicitacoes.listar(apenas_ativas=False)
        grupos = agrupar_exclusoes(todas)
        publicada = self._fila.obter_publicada()
        return ResultadoExclusoes(
            grupos=grupos,
            total=len(todas),
            fora=sum(g.quantidade for g in grupos),
            publicadas=len(publicada) if publicada else None,
        )
