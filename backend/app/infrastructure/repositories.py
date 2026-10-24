"""Implementações SQL das portas de domain/ports.py.

Convertem Table <-> entidade de domínio. A aplicação só conhece os Protocols.
TODO(US-01): implementar conforme a carga for sendo feita.
"""
from __future__ import annotations

import json
from dataclasses import fields

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, SQLModel

from app.domain.enums import Classe, ClasseStatus, StatusFila
from app.domain.models import Correcao, Evento, ResultadoTabela, Solicitacao
from app.infrastructure.tables import (
    CorrecaoTable,
    EventoTable,
    ProcedimentoTable,
    SolicitacaoTable,
)

TAMANHO_LOTE = 500
_CAMPOS_SOLICITACAO = [f.name for f in fields(Solicitacao)]
_CAMPOS_EVENTO = [f.name for f in fields(Evento)]


def _para_solicitacao(linha: SolicitacaoTable) -> Solicitacao:
    """Table -> entidade. Só traz as colunas que a entidade conhece; o resto fica no banco."""
    dados = {c: getattr(linha, c) for c in _CAMPOS_SOLICITACAO if hasattr(linha, c)}
    for texto in ("nome_paciente", "justificativa_clinica", "observacoes"):
        dados[texto] = dados[texto] or ""
    dados["status_fila"] = StatusFila(linha.status_fila)
    dados["classe_status"] = ClasseStatus(linha.classe_status)
    dados["classe_medico"] = Classe(linha.classe_medico) if linha.classe_medico else None
    dados["alertas"] = json.loads(linha.alertas_json)
    return Solicitacao(**dados)


def _para_evento(linha: EventoTable) -> Evento:
    dados = {c: getattr(linha, c) for c in _CAMPOS_EVENTO}
    dados["descricao"] = dados["descricao"] or ""
    return Evento(**dados)


class SqlSolicitacaoRepository:
    def __init__(self, session: Session):
        self._s = session

    def obter(self, solicitacao_id: str) -> Solicitacao | None:
        raise NotImplementedError("US-01")

    def listar(self, apenas_ativas: bool = True) -> list[Solicitacao]:
        consulta = select(SolicitacaoTable).order_by(SolicitacaoTable.solicitacao_id)
        if apenas_ativas:
            consulta = consulta.where(SolicitacaoTable.status_fila == StatusFila.ATIVA.value)
        return [_para_solicitacao(linha) for linha in self._s.execute(consulta).scalars().all()]

    def salvar(self, solicitacao: Solicitacao) -> None:
        raise NotImplementedError("US-01")

    def salvar_varias(self, solicitacoes: list[Solicitacao]) -> None:
        raise NotImplementedError("US-01")

    def atualizar_flags(self, solicitacoes: list[Solicitacao]) -> None:
        if not solicitacoes:
            return
        self._s.execute(update(SolicitacaoTable), [
            {"solicitacao_id": s.solicitacao_id, "oncologico": s.oncologico,
             "piora_recalculada": s.piora_recalculada}
            for s in solicitacoes
        ])


class SqlEventoRepository:
    def __init__(self, session: Session):
        self._s = session

    def listar_por_solicitacao(self, solicitacao_id: str) -> list[Evento]:
        raise NotImplementedError("US-01")

    def listar_todos(self) -> list[Evento]:
        consulta = select(EventoTable).order_by(EventoTable.evento_id)
        return [_para_evento(linha) for linha in self._s.execute(consulta).scalars().all()]

    def adicionar(self, evento: Evento) -> None:
        raise NotImplementedError("US-01")

    def salvar_varios(self, eventos: list[Evento]) -> None:
        raise NotImplementedError("US-01")

    def atualizar_marcas(self, eventos: list[Evento]) -> None:
        if not eventos:
            return
        self._s.execute(update(EventoTable), [
            {"evento_id": e.evento_id, "duplicado_de": e.duplicado_de, "historico": e.historico}
            for e in eventos
        ])


class SqlCorrecaoRepository:
    def __init__(self, session: Session):
        self._s = session

    def substituir_por_regras(self, regras: tuple[str, ...], correcoes: list[Correcao]) -> None:
        self._s.execute(delete(CorrecaoTable).where(CorrecaoTable.regra.in_(regras)))
        if correcoes:
            self._s.execute(insert(CorrecaoTable), [
                {"solicitacao_id": c.solicitacao_id, "campo": c.campo, "original": c.original,
                 "novo": c.novo, "regra": c.regra}
                for c in correcoes
            ])


class SqlUnidadeDeTrabalho:
    """Transação da sessão: confirma ou desfaz tudo o que os repositórios fizeram."""

    def __init__(self, session: Session):
        self._s = session

    def confirmar(self) -> None:
        self._s.commit()

    def desfazer(self) -> None:
        self._s.rollback()


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
