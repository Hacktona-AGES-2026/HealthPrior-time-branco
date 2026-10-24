"""Implementações SQL das portas de domain/ports.py.

Convertem Table <-> entidade de domínio. A aplicação só conhece os Protocols.
TODO(US-01): implementar conforme a carga for sendo feita.
"""
from __future__ import annotations

from sqlalchemy import bindparam, delete, select, update
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


def _para_entidade(t: SolicitacaoTable) -> Solicitacao:
    return Solicitacao(
        solicitacao_id=t.solicitacao_id, paciente_id=t.paciente_id,
        procedimento_id=t.procedimento_id, cid_principal=t.cid_principal,
        data_entrada_fila=t.data_entrada_fila,
        nome_paciente=t.nome_paciente, idade=t.idade, sexo=t.sexo, municipio=t.municipio,
        procedimento=t.procedimento, especialidade=t.especialidade, cid_descricao=t.cid_descricao,
        intensidade_dor_eva=t.intensidade_dor_eva, limitacao_funcional=t.limitacao_funcional,
        justificativa_clinica=t.justificativa_clinica or "", observacoes=t.observacoes or "",
        prioridade_regulacao=t.prioridade_regulacao, flag_oncologico=t.flag_oncologico,
        flag_piora_clinica=t.flag_piora_clinica, piora_recalculada=t.piora_recalculada,
        cid_norm=t.cid_norm, nome_norm=t.nome_norm or "", oncologico=t.oncologico,
        municipio_norm=t.municipio_norm, prioridade_norm=t.prioridade_norm,
        status_fila=StatusFila(t.status_fila), motivo_status=t.motivo_status,
        classe_status=ClasseStatus(t.classe_status),
        classe_medico=Classe(t.classe_medico) if t.classe_medico else None,
        score_medico=t.score_medico, editado_manualmente=t.editado_manualmente,
        editado_por=t.editado_por, editado_em=t.editado_em,
    )


def _para_evento(t: EventoTable) -> Evento:
    return Evento(
        evento_id=t.evento_id, solicitacao_id=t.solicitacao_id, paciente_id=t.paciente_id,
        data_evento=t.data_evento, tipo_evento=t.tipo_evento, resultado=t.resultado,
        valor_numerico=t.valor_numerico, descricao=t.descricao or "", origem=t.origem,
        duplicado_de=t.duplicado_de, historico=t.historico, orfao=t.orfao,
    )


class SqlSolicitacaoRepository:
    def __init__(self, session: Session):
        self._s = session

    def obter(self, solicitacao_id: str) -> Solicitacao | None:
        raise NotImplementedError("US-01")

    def listar(self, apenas_ativas: bool = True) -> list[Solicitacao]:
        consulta = select(SolicitacaoTable).order_by(SolicitacaoTable.solicitacao_id)
        if apenas_ativas:
            consulta = consulta.where(SolicitacaoTable.status_fila == StatusFila.ATIVA.value)
        return [_para_entidade(t) for t in self._s.exec(consulta).scalars()]

    def salvar(self, solicitacao: Solicitacao) -> None:
        raise NotImplementedError("US-01")

    def salvar_varias(self, solicitacoes: list[Solicitacao]) -> None:
        raise NotImplementedError("US-01")

    def salvar_normalizadas(self, solicitacoes: list[Solicitacao]) -> None:
        if not solicitacoes:
            return
        tabela = SolicitacaoTable.__table__
        self._s.execute(
            update(tabela)
            .where(tabela.c.solicitacao_id == bindparam("b_id"))
            .values(cid_norm=bindparam("cid_norm"), nome_norm=bindparam("nome_norm"),
                    municipio_norm=bindparam("municipio_norm"),
                    prioridade_norm=bindparam("prioridade_norm")),
            [{"b_id": s.solicitacao_id, "cid_norm": s.cid_norm, "nome_norm": s.nome_norm,
              "municipio_norm": s.municipio_norm, "prioridade_norm": s.prioridade_norm}
             for s in solicitacoes],
        )
        self._s.expire_all()  # o update em lote não sincroniza os objetos já carregados

    def atualizar_flags(self, solicitacoes: list[Solicitacao]) -> None:
        if not solicitacoes:
            return
        tabela = SolicitacaoTable.__table__
        self._s.execute(
            update(tabela)
            .where(tabela.c.solicitacao_id == bindparam("b_id"))
            .values(oncologico=bindparam("oncologico"),
                    piora_recalculada=bindparam("piora_recalculada")),
            [{"b_id": s.solicitacao_id, "oncologico": s.oncologico,
              "piora_recalculada": s.piora_recalculada} for s in solicitacoes],
        )
        self._s.expire_all()


class SqlEventoRepository:
    def __init__(self, session: Session):
        self._s = session

    def listar_por_solicitacao(self, solicitacao_id: str) -> list[Evento]:
        consulta = (select(EventoTable).where(EventoTable.solicitacao_id == solicitacao_id)
                    .order_by(EventoTable.data_evento, EventoTable.evento_id))
        return [_para_evento(t) for t in self._s.exec(consulta).scalars()]

    def listar_todos(self) -> list[Evento]:
        consulta = select(EventoTable).order_by(EventoTable.evento_id)
        return [_para_evento(t) for t in self._s.exec(consulta).scalars()]

    def adicionar(self, evento: Evento) -> None:
        raise NotImplementedError("US-01")

    def salvar_varios(self, eventos: list[Evento]) -> None:
        raise NotImplementedError("US-01")

    def atualizar_marcas(self, eventos: list[Evento]) -> None:
        if not eventos:
            return
        tabela = EventoTable.__table__
        self._s.execute(
            update(tabela)
            .where(tabela.c.evento_id == bindparam("b_id"))
            .values(duplicado_de=bindparam("duplicado_de"), historico=bindparam("historico")),
            [{"b_id": e.evento_id, "duplicado_de": e.duplicado_de, "historico": e.historico}
             for e in eventos],
        )
        self._s.expire_all()


class SqlCargaRepository:
    """US-01: upsert dos CSVs. Atualiza só as colunas do CSV e preserva o estado do sistema."""

    def __init__(self, session: Session):
        self._s = session

    def gravar(self, procedimentos: list[dict], solicitacoes: list[dict],
               eventos: list[dict]) -> dict[str, ResultadoTabela]:
        # Ordem importa: solicitacoes referencia procedimentos.
        SQLModel.metadata.create_all(self._s.get_bind())  # idempotente: só cria o que falta
        return {
            "procedimentos": self._upsert(ProcedimentoTable, procedimentos),
            "solicitacoes": self._upsert(SolicitacaoTable, solicitacoes),
            "eventos": self._upsert(EventoTable, eventos),
        }

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


class SqlCorrecaoRepository:
    def __init__(self, session: Session):
        self._s = session

    def adicionar_varias(self, correcoes: list[Correcao]) -> None:
        raise NotImplementedError("US-03")

    def listar_por_solicitacao(self, solicitacao_id: str) -> list[Correcao]:
        raise NotImplementedError("US-03")

    def substituir(self, regras: tuple[str, ...], correcoes: list[Correcao]) -> None:
        self._s.execute(delete(CorrecaoTable).where(CorrecaoTable.regra.in_(regras)))
        self._s.add_all(
            CorrecaoTable(solicitacao_id=c.solicitacao_id, campo=c.campo, original=c.original,
                          novo=c.novo, regra=c.regra)
            for c in correcoes
        )
        self._s.flush()


class SqlUnidadeDeTrabalho:
    def __init__(self, session: Session):
        self._s = session

    def confirmar(self) -> None:
        self._s.commit()

    def desfazer(self) -> None:
        self._s.rollback()


# Demais repositórios (Pendencia, Decisao, Correcao, Fila) seguem o mesmo padrão.
