"""Implementações SQLite das portas de domain/ports.py.

Convertem Table <-> entidade de domínio. A aplicação só conhece os Protocols.
TODO(US-01): implementar conforme a carga for sendo feita.
"""
from __future__ import annotations

from sqlmodel import Session

from app.domain.models import Evento, Solicitacao


class SqlSolicitacaoRepository:
    def __init__(self, session: Session):
        self._s = session

    def obter(self, solicitacao_id: str) -> Solicitacao | None:
        raise NotImplementedError("US-01")

    def listar(self, apenas_ativas: bool = True) -> list[Solicitacao]:
        raise NotImplementedError("US-01")

    def salvar(self, solicitacao: Solicitacao) -> None:
        raise NotImplementedError("US-01")

    def salvar_varias(self, solicitacoes: list[Solicitacao]) -> None:
        raise NotImplementedError("US-01")


class SqlEventoRepository:
    def __init__(self, session: Session):
        self._s = session

    def listar_por_solicitacao(self, solicitacao_id: str) -> list[Evento]:
        raise NotImplementedError("US-01")

    def listar_todos(self) -> list[Evento]:
        raise NotImplementedError("US-01")

    def adicionar(self, evento: Evento) -> None:
        raise NotImplementedError("US-01")

    def salvar_varios(self, eventos: list[Evento]) -> None:
        raise NotImplementedError("US-01")


# Demais repositórios (Pendencia, Decisao, Correcao, Fila) seguem o mesmo padrão.
