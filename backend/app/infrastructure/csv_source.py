"""Fonte de dados CSV (somente leitura) para solicitações e eventos clínicos."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from app.domain.cid import is_oncologico, normalizar_cid
from app.domain.models import Evento, Solicitacao
from app.domain.preprocessing.normalizacao import normalizar_prioridade


def _txt(valor) -> str | None:
    """Converte NaN/vazio em None e devolve texto sem alterar o conteúdo."""
    if valor is None or pd.isna(valor):
        return None
    return str(valor)


def _inteiro(valor) -> int | None:
    if valor is None or pd.isna(valor):
        return None
    return int(float(valor))


def _data(valor) -> date:
    return date.fromisoformat(str(valor)[:10])


def _numero(valor) -> float | None:
    if valor is None or pd.isna(valor):
        return None
    return float(valor)


def carregar_do_csv(data_dir: Path) -> tuple[list[Solicitacao], dict[str, list[Evento]]]:
    """Lê fila_cirurgica.csv e eventos_clinicos.csv e devolve entidades de domínio.

    Eventos duplicados são marcados em ``duplicado_de``; eventos anteriores à
    entrada na fila recebem ``historico=True``; eventos órfãos ficam de fora.
    """
    df_fila = pd.read_csv(data_dir / "fila_cirurgica.csv", dtype=str, keep_default_na=True)
    df_evt = pd.read_csv(data_dir / "eventos_clinicos.csv", dtype=str, keep_default_na=True)

    solicitacoes: list[Solicitacao] = []
    for r in df_fila.to_dict("records"):
        cid = _txt(r["cid_principal"]) or ""
        prioridade = _txt(r.get("prioridade_regulacao"))
        solicitacoes.append(Solicitacao(
            solicitacao_id=r["solicitacao_id"],
            paciente_id=r["paciente_id"],
            procedimento_id=r["procedimento_id"],
            cid_principal=cid,
            data_entrada_fila=_data(r["data_entrada_fila"]),
            nome_paciente=_txt(r.get("nome_paciente")) or "",
            procedimento=_txt(r.get("procedimento")),
            especialidade=_txt(r.get("especialidade")),
            intensidade_dor_eva=_inteiro(r.get("intensidade_dor_eva")),
            limitacao_funcional=_txt(r.get("limitacao_funcional")),
            justificativa_clinica=_txt(r.get("justificativa_clinica")) or "",
            observacoes=_txt(r.get("observacoes")) or "",
            prioridade_regulacao=prioridade,
            flag_oncologico=_txt(r.get("flag_oncologico")),
            cid_norm=normalizar_cid(cid),
            oncologico=is_oncologico(cid),  # sempre pelo CID, nunca pela flag
            prioridade_norm=normalizar_prioridade(prioridade),
        ))

    entrada = {s.solicitacao_id: s.data_entrada_fila for s in solicitacoes}
    eventos: dict[str, list[Evento]] = {}
    primeiro_por_chave: dict[tuple, str] = {}
    for r in df_evt.sort_values("evento_id", kind="stable").to_dict("records"):
        sid = r["solicitacao_id"]
        if sid not in entrada:
            continue  # órfão
        data_evt = _data(r["data_evento"])
        resultado = _txt(r.get("resultado"))
        descricao = _txt(r.get("descricao")) or ""
        chave = (sid, data_evt, r["tipo_evento"], resultado, descricao)
        dup = primeiro_por_chave.setdefault(chave, r["evento_id"])
        eventos.setdefault(sid, []).append(Evento(
            evento_id=r["evento_id"],
            solicitacao_id=sid,
            paciente_id=r["paciente_id"],
            data_evento=data_evt,
            tipo_evento=r["tipo_evento"],
            resultado=resultado,
            valor_numerico=_numero(r.get("valor_numerico")),
            descricao=descricao,
            origem=_txt(r.get("origem")),
            duplicado_de=None if dup == r["evento_id"] else dup,
            historico=data_evt < entrada[sid],
        ))
    return solicitacoes, eventos
