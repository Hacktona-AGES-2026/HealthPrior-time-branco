"""Implementações SQL das portas de domain/ports.py.

Convertem Table <-> entidade de domínio. A aplicação só conhece os Protocols.
TODO(US-01): implementar conforme a carga for sendo feita.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, SQLModel

from app.domain.models import Evento, ResultadoTabela, Solicitacao
from app.infrastructure.tables import EventoTable, ProcedimentoTable, SolicitacaoTable

TAMANHO_LOTE = 500


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


class SqlCargaRepository:
    """US-01: upsert dos CSVs. Atualiza só as colunas do CSV e preserva o estado do sistema."""

    def __init__(self, session: Session):
        self._s = session

    def gravar(self, procedimentos: list[dict], solicitacoes: list[dict],
               eventos: list[dict]) -> dict[str, ResultadoTabela]:
        # Ordem importa: solicitacoes referencia procedimentos.
        SQLModel.metadata.create_all(self._s.get_bind())  # idempotente: só cria o que falta
        try:
            resultado = {
                "procedimentos": self._upsert(ProcedimentoTable, procedimentos),
                "solicitacoes": self._upsert(SolicitacaoTable, solicitacoes),
                "eventos": self._upsert(EventoTable, eventos),
            }
            self._s.commit()
        except Exception:
            self._s.rollback()
            raise
        return resultado

    def _upsert(self, tabela: type, registros: list[dict]) -> ResultadoTabela:
        resultado = ResultadoTabela(lido=len(registros))
        pk = tabela.__table__.primary_key.columns.keys()[0]
        for i in range(0, len(registros), TAMANHO_LOTE):
            lote = registros[i : i + TAMANHO_LOTE]
            ids = [r[pk] for r in lote]
            existentes = set(self._s.exec(select(tabela.__table__.c[pk]).where(
                tabela.__table__.c[pk].in_(ids))).scalars())
            stmt = insert(tabela).values(lote)
            stmt = stmt.on_conflict_do_update(
                index_elements=[pk],
                set_={c: stmt.excluded[c] for c in lote[0] if c != pk},
            )
            self._s.execute(stmt)
            resultado.atualizados += len(existentes)
            resultado.inseridos += len(ids) - len(existentes)
        return resultado


# Demais repositórios (Pendencia, Decisao, Correcao, Fila) seguem o mesmo padrão.
