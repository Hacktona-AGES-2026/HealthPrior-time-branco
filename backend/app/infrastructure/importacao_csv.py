"""Leitura e validação do CSV de novas solicitações (mesmas colunas de `data/fila_cirurgica.csv`).

Aceita o arquivo inteiro ou só as colunas que a pessoa tem (as obrigatórias são exigidas), com `,` ou `;`
(Excel em português) e BOM. Valida tudo antes de devolver, com o número da linha: nada é gravado se algo falhar.
"""
from __future__ import annotations

import csv
import io
from datetime import date

from app.domain.importacao import ErroLinha, LeituraCsv
from app.infrastructure.csv_loader import _colunas_originais, _converter
from app.infrastructure.tables import SolicitacaoTable

COLUNAS = _colunas_originais(SolicitacaoTable)
OBRIGATORIAS = ("solicitacao_id", "paciente_id", "nome_paciente", "procedimento_id", "cid_principal",
                "data_entrada_fila")
MAX_LINHAS = 5000
MAX_ERROS = 50  # o resto é resumido: ninguém precisa de 3 mil mensagens iguais

EXEMPLO = {
    "solicitacao_id": "SOL-2026-90001", "paciente_id": "PAC-90001", "nome_paciente": "Maria Exemplo da Silva",
    "sexo": "F", "idade": "58", "municipio": "Porto Alegre", "uf": "RS", "procedimento_id": "PROC004",
    "cid_principal": "K80.2", "intensidade_dor_eva": "5", "limitacao_funcional": "moderada",
    "justificativa_clinica": "Colecistite calculosa com crises recorrentes.", "data_entrada_fila": "2026-10-01",
    "prioridade_regulacao": "media",
}


def modelo_csv() -> str:
    """Cabeçalho completo e uma linha de exemplo (procedimento e nomes ficam a cargo do sistema)."""
    saida = io.StringIO()
    w = csv.writer(saida, lineterminator="\n")
    w.writerow(COLUNAS)
    w.writerow([EXEMPLO.get(c, "") for c in COLUNAS])
    return saida.getvalue()


class LeitorEmMemoria:
    """Entrega ao `CargaInicial` só as solicitações já validadas (procedimentos e eventos não mudam)."""

    def __init__(self, solicitacoes: list[dict]):
        self._s = solicitacoes

    def procedimentos(self) -> list[dict]:
        return []

    def fila(self) -> list[dict]:
        return self._s

    def eventos(self) -> list[dict]:
        return []


def _delimitador(cabecalho: str) -> str:
    return ";" if cabecalho.count(";") > cabecalho.count(",") else ","


def ler_solicitacoes(texto: str, procedimentos: dict[str, tuple[str | None, str | None]],
                     hoje: date) -> LeituraCsv:
    """`procedimentos`: procedimento_id -> (nome, especialidade), para validar e preencher o que faltar."""
    out = LeituraCsv()
    texto = texto.lstrip("﻿")
    if not texto.strip():
        out.erros.append(ErroLinha(1, None, "O arquivo está vazio."))
        return out
    leitor = csv.DictReader(io.StringIO(texto), delimiter=_delimitador(texto.splitlines()[0]))
    campos = [c.strip() for c in (leitor.fieldnames or [])]
    leitor.fieldnames = campos
    desconhecidas = [c for c in campos if c not in COLUNAS]
    faltando = [c for c in OBRIGATORIAS if c not in campos]
    if desconhecidas:
        out.erros.append(ErroLinha(1, ",".join(desconhecidas), "Coluna desconhecida. Baixe o modelo para ver as colunas aceitas."))
    if faltando:
        out.erros.append(ErroLinha(1, ",".join(faltando), "Coluna obrigatória ausente."))
    if out.erros:
        return out

    colunas = SolicitacaoTable.__table__.columns
    vistos: set[str] = set()
    for n, linha in enumerate(leitor, start=2):
        if all(not (v or "").strip() for v in linha.values()):
            continue  # linha em branco
        out.lidas += 1
        if out.lidas > MAX_LINHAS:
            out.erros.append(ErroLinha(n, None, f"Mais de {MAX_LINHAS} linhas: divida o arquivo."))
            break
        erros_antes = len(out.erros)
        reg: dict = {}
        for c in COLUNAS:
            bruto = (linha.get(c) or "").strip() if c in campos else ""
            try:
                reg[c] = _converter(colunas[c], bruto)
            except ValueError:
                out.erros.append(ErroLinha(n, c, f"Valor inválido: '{bruto}'."))
                reg[c] = None
        for c in OBRIGATORIAS:
            if reg.get(c) in (None, ""):
                out.erros.append(ErroLinha(n, c, "Campo obrigatório vazio."))
        if len(out.erros) == erros_antes:  # só confere as regras se os tipos e obrigatórios estão certos
            _regras(reg, n, procedimentos, hoje, vistos, out.erros)
        if len(out.erros) == erros_antes:
            nome, esp = procedimentos[reg["procedimento_id"]]
            reg["procedimento"] = reg["procedimento"] or nome
            reg["especialidade"] = reg["especialidade"] or esp
            if reg["dias_em_fila"] is None:
                reg["dias_em_fila"] = (hoje - reg["data_entrada_fila"]).days
            out.registros.append(reg)
        if len(out.erros) >= MAX_ERROS:
            out.erros.append(ErroLinha(n, None, f"Mais erros adiante: corrija estes e envie de novo (mostrando {MAX_ERROS})."))
            break
    if out.lidas == 0 and not out.erros:
        out.erros.append(ErroLinha(2, None, "Nenhuma linha de dados."))
    return out


def _regras(reg: dict, n: int, procedimentos: dict, hoje: date, vistos: set[str], erros: list[ErroLinha]) -> None:
    def erro(campo: str, msg: str) -> None:
        erros.append(ErroLinha(n, campo, msg))

    if reg["solicitacao_id"] in vistos:
        erro("solicitacao_id", f"{reg['solicitacao_id']} aparece mais de uma vez no arquivo.")
    vistos.add(reg["solicitacao_id"])
    if reg["procedimento_id"] not in procedimentos:
        erro("procedimento_id", f"Procedimento {reg['procedimento_id']} não existe no cadastro.")
    if reg["sexo"] not in (None, "M", "F"):
        erro("sexo", "Use M ou F.")
    if reg["idade"] is not None and not 0 <= reg["idade"] <= 120:
        erro("idade", "Idade fora de 0 a 120.")
    if reg["intensidade_dor_eva"] is not None and not 0 <= reg["intensidade_dor_eva"] <= 10:
        erro("intensidade_dor_eva", "A escala de dor (EVA) vai de 0 a 10.")
    if reg["data_entrada_fila"] > hoje:
        erro("data_entrada_fila", f"Data de entrada no futuro (hoje é {hoje:%d/%m/%Y}).")
