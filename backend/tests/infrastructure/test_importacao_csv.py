"""Leitura e validação do CSV de novas solicitações (sem banco)."""
from datetime import date

import pytest

from app.infrastructure.importacao_csv import COLUNAS, OBRIGATORIAS, ler_solicitacoes, modelo_csv

HOJE = date(2026, 10, 23)
PROCS = {"PROC004": ("Colecistectomia videolaparoscopica", "Cirurgia Geral")}
CAB = ",".join(OBRIGATORIAS)


def linha(**kw):
    base = dict(solicitacao_id="SOL-X-1", paciente_id="PAC-1", nome_paciente="Ana Teste", procedimento_id="PROC004",
                cid_principal="K80.2", data_entrada_fila="2026-10-01")
    base.update(kw)
    return ",".join(str(base[c]) for c in OBRIGATORIAS)


def ler(texto):
    return ler_solicitacoes(texto, PROCS, HOJE)


def test_minimo_valido_preenche_o_que_o_sistema_sabe():
    r = ler(f"{CAB}\n{linha()}\n")
    assert r.erros == [] and r.lidas == 1
    reg = r.registros[0]
    assert reg["procedimento"] == "Colecistectomia videolaparoscopica" and reg["especialidade"] == "Cirurgia Geral"
    assert reg["dias_em_fila"] == 22 and reg["data_entrada_fila"] == date(2026, 10, 1)
    assert set(reg) == set(COLUNAS) and reg["sexo"] is None  # colunas ausentes ficam vazias


def test_ponto_e_virgula_bom_e_linhas_em_branco():
    texto = "﻿" + f"{CAB.replace(',', ';')}\n{linha().replace(',', ';')}\n\n;;;;;\n"
    r = ler(texto)
    assert r.erros == [] and len(r.registros) == 1


def test_modelo_baixado_e_aceito():
    r = ler(modelo_csv())
    assert r.erros == [] and r.registros[0]["solicitacao_id"] == "SOL-2026-90001"


@pytest.mark.parametrize("texto,campo", [
    (f"{CAB},coluna_estranha\n{linha()},x\n", "coluna_estranha"),
    (f"solicitacao_id,paciente_id\nA,B\n", "nome_paciente"),
])
def test_cabecalho_errado_para_na_linha_1(texto, campo):
    r = ler(texto)
    assert r.registros == [] and r.erros[0].linha == 1 and campo in r.erros[0].campo


def test_erros_por_linha_e_campo():
    r = ler(f"{CAB},idade,sexo,intensidade_dor_eva\n"
            f"{linha()},abc,M,5\n"                                  # linha 2: idade não numérica
            f"{linha(solicitacao_id='B', procedimento_id='PROC999')},40,X,11\n"  # linha 3: 3 erros
            f"{linha(solicitacao_id='C', data_entrada_fila='2027-01-01')},40,F,5\n"  # linha 4: futuro
            f"{linha(solicitacao_id='D', nome_paciente='')},40,F,5\n")  # linha 5: obrigatório vazio
    achados = {(e.linha, e.campo) for e in r.erros}
    assert (2, "idade") in achados
    assert {(3, "procedimento_id"), (3, "sexo"), (3, "intensidade_dor_eva")} <= achados
    assert (4, "data_entrada_fila") in achados and (5, "nome_paciente") in achados
    assert r.registros == []


def test_id_repetido_no_arquivo_e_data_invalida():
    r = ler(f"{CAB}\n{linha()}\n{linha()}\n{linha(solicitacao_id='Z', data_entrada_fila='01/10/2026')}\n")
    assert any(e.linha == 3 and "mais de uma vez" in e.mensagem for e in r.erros)
    assert any(e.linha == 4 and e.campo == "data_entrada_fila" for e in r.erros)


def test_vazio_e_so_cabecalho():
    assert "vazio" in ler("").erros[0].mensagem
    assert "Nenhuma linha" in ler(f"{CAB}\n").erros[0].mensagem


def test_limite_de_erros_resume():
    corpo = "\n".join(linha(solicitacao_id=f"S{i}", procedimento_id="NADA") for i in range(200))
    r = ler(f"{CAB}\n{corpo}\n")
    assert len(r.erros) <= 52 and "Mais erros adiante" in r.erros[-1].mensagem
