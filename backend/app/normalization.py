"""Aplica o pré-processamento (preprocessing.py) às solicitações já carregadas.

Idempotente: recalcula as colunas *_norm e refaz o log das regras PRE-01..PRE-04 do zero,
sem tocar nas colunas originais nem no log de outras regras.
"""
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict

from sqlalchemy import Connection, bindparam, delete, insert, select, update

from app.models import CorrecaoLog, Solicitacao
from app.preprocessing import PRE_CID, PRE_MUNICIPIO, PRE_NOME, PRE_PRIORIDADE, preprocess_solicitacao

REGRAS = (PRE_CID, PRE_NOME, PRE_MUNICIPIO, PRE_PRIORIDADE)


@dataclass
class NormalizacaoResult:
    solicitacoes: int = 0
    correcoes: int = 0
    por_regra: Dict[str, int] = field(default_factory=dict)


def normalizar(conn: Connection) -> NormalizacaoResult:
    colunas = Solicitacao.nome_paciente, Solicitacao.municipio, Solicitacao.cid_principal, \
        Solicitacao.prioridade_regulacao
    rows = conn.execute(select(Solicitacao.solicitacao_id, *colunas)).mappings().all()

    atualizacoes, log = [], []
    for row in rows:
        norm, correcoes = preprocess_solicitacao(row)
        atualizacoes.append({"b_id": row["solicitacao_id"], **norm})
        log.extend(
            {"solicitacao_id": row["solicitacao_id"], "campo": c.campo, "original": c.original,
             "novo": c.novo, "regra": c.regra}
            for c in correcoes
        )

    if atualizacoes:
        conn.execute(
            update(Solicitacao)
            .where(Solicitacao.solicitacao_id == bindparam("b_id"))
            .values(
                cid_norm=bindparam("cid_norm"),
                nome_norm=bindparam("nome_norm"),
                municipio_norm=bindparam("municipio_norm"),
                prioridade_norm=bindparam("prioridade_norm"),
            ),
            atualizacoes,
        )
    conn.execute(delete(CorrecaoLog).where(CorrecaoLog.regra.in_(REGRAS)))
    if log:
        conn.execute(insert(CorrecaoLog), log)

    return NormalizacaoResult(
        solicitacoes=len(rows),
        correcoes=len(log),
        por_regra=dict(Counter(item["regra"] for item in log)),
    )
