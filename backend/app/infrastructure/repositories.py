"""Implementações SQL das portas de domain/ports.py.

Convertem Table <-> entidade de domínio. A aplicação só conhece os Protocols.
TODO(US-01): implementar conforme a carga for sendo feita.
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import bindparam, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, SQLModel

from app.domain.enums import Classe, ClasseStatus, StatusFila
from app.domain.models import (
    Correcao,
    Evento,
    Pendencia,
    ResultadoSincronizacao,
    ResultadoTabela,
    Solicitacao,
)
from app.infrastructure.tables import (
    CorrecaoTable,
    EventoTable,
    PendenciaTable,
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
        flag_diabetico=t.flag_diabetico, flag_piora_clinica=t.flag_piora_clinica,
        asa=t.asa, distancia_hospital_km=t.distancia_hospital_km, comorbidades=t.comorbidades,
        hba1c_ultima=t.hba1c_ultima, piora_recalculada=t.piora_recalculada,
        cid_norm=t.cid_norm, nome_norm=t.nome_norm or "", oncologico=t.oncologico,
        municipio_norm=t.municipio_norm, prioridade_norm=t.prioridade_norm,
        status_fila=StatusFila(t.status_fila), motivo_status=t.motivo_status,
        classe_status=ClasseStatus(t.classe_status), alertas=json.loads(t.alertas_json),
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

    def salvar_alertas(self, solicitacoes: list[Solicitacao]) -> None:
        if not solicitacoes:
            return
        tabela = SolicitacaoTable.__table__
        self._s.execute(
            update(tabela).where(tabela.c.solicitacao_id == bindparam("b_id"))
            .values(alertas_json=bindparam("alertas_json")),
            [{"b_id": s.solicitacao_id, "alertas_json": json.dumps(s.alertas, ensure_ascii=False)}
             for s in solicitacoes],
        )
        self._s.expire_all()

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


def _evidencias_json(pendencia: Pendencia) -> str:
    """Mesmo formato de EvidenciaOut (fonte, ref, texto) + sinal e data da evidência."""
    return json.dumps(
        [{"fonte": m.fonte, "ref": m.ref, "texto": m.evidencia, "sinal": m.sinal,
          "data": m.data.isoformat() if m.data else None} for m in pendencia.evidencias],
        ensure_ascii=False, sort_keys=True)


class SqlPendenciaRepository:
    def __init__(self, session: Session):
        self._s = session

    def obter(self, pendencia_id: str) -> Pendencia | None:
        raise NotImplementedError("US-06")

    def listar(self, bloqueante: bool | None = None, regra: str | None = None,
               status: str | None = "aberta") -> list[Pendencia]:
        raise NotImplementedError("US-06")

    def salvar(self, pendencia: Pendencia) -> None:
        raise NotImplementedError("US-07")

    def sincronizar(self, regras: tuple[str, ...], pendencias: list[Pendencia]) -> ResultadoSincronizacao:
        existentes = {(t.solicitacao_id, t.regra): t for t in self._s.execute(
            select(PendenciaTable).where(PendenciaTable.regra.in_(regras))).scalars()}
        desejadas = {(p.solicitacao_id, p.regra): p for p in pendencias}
        resultado = ResultadoSincronizacao()
        proximo = self._proximo_numero()

        for chave in sorted(desejadas):  # ordem fixa: ids iguais em qualquer banco novo
            p, atual = desejadas[chave], existentes.get(chave)
            if atual is None:
                self._s.add(PendenciaTable(
                    pendencia_id=f"PEN-{proximo:04d}", solicitacao_id=p.solicitacao_id, regra=p.regra,
                    titulo=p.titulo, bloqueante=p.bloqueante, evidencias_json=_evidencias_json(p),
                    acao_sugerida=p.acao_sugerida, aberta_em=p.aberta_em))
                proximo += 1
                resultado.abertas += 1
            elif atual.status == "aberta":
                novos = (p.titulo, _evidencias_json(p), p.acao_sugerida)
                if (atual.titulo, atual.evidencias_json, atual.acao_sugerida) != novos:
                    atual.titulo, atual.evidencias_json, atual.acao_sugerida = novos
                    resultado.atualizadas += 1
            # resolvida/descartada por uma pessoa: continua como está, mesmo que o achado persista

        for chave, atual in existentes.items():
            if chave not in desejadas and atual.status == "aberta":
                atual.status, atual.resolvido_por = "resolvida", "sistema"
                atual.resolvido_em, atual.resolucao = datetime.utcnow(), "deixou_de_valer"
                resultado.encerradas += 1

        self._s.flush()
        return resultado

    def _proximo_numero(self) -> int:
        ultimo = self._s.execute(select(func.max(PendenciaTable.pendencia_id))).scalar()
        return int(ultimo.split("-")[1]) + 1 if ultimo else 1


class SqlUnidadeDeTrabalho:
    def __init__(self, session: Session):
        self._s = session

    def confirmar(self) -> None:
        self._s.commit()

    def desfazer(self) -> None:
        self._s.rollback()


# Demais repositórios (Pendencia, Decisao, Correcao, Fila) seguem o mesmo padrão.
