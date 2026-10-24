"""Testes unitários das regras PRE-01..PRE-04: sem banco, rodam em milissegundos."""
import csv

import pytest

from app import config
from app.preprocessing import (
    MUNICIPIOS_OFICIAIS,
    Correcao,
    normalize_cid,
    normalize_municipio,
    normalize_nome,
    normalize_prioridade,
    preprocess_solicitacao,
)


@pytest.mark.parametrize(
    "raw, esperado",
    [("K42.9", "K429"), ("K429", "K429"), ("k42.9", "K429"), ("  c18.7 ", "C187"), ("", None), (None, None)],
)
def test_normalize_cid(raw, esperado):
    assert normalize_cid(raw) == esperado


def test_nome_com_grafias_diferentes_gera_a_mesma_chave():
    # PAC-00087
    assert normalize_nome("Jurema Quadros Weber") == normalize_nome("JUREMA QUADROS WEBER")


def test_nome_ignora_acento_e_espaco_repetido():
    assert normalize_nome("  João  da   Conceição ") == "joao da conceicao"


@pytest.mark.parametrize("raw", ["Porto Alegre", "PORTO ALEGRE", "porto alegre", " porto  alegre "])
def test_municipio_porto_alegre(raw):
    assert normalize_municipio(raw) == "Porto Alegre"


@pytest.mark.parametrize(
    "raw, oficial",
    [("osorio", "Osório"), ("VIAMAO", "Viamão"), ("Gravatai", "Gravataí"), ("camaqua", "Camaquã")],
)
def test_municipio_recebe_o_nome_oficial_com_acento(raw, oficial):
    assert normalize_municipio(raw) == oficial


def test_municipio_desconhecido_so_perde_espacos_sobrando():
    assert normalize_municipio("  Vila   Nova ") == "Vila Nova"


def test_todo_municipio_do_dataset_esta_na_tabela():
    with (config.DATA_DIR / "fila_cirurgica.csv").open(encoding="utf-8", newline="") as f:
        valores = {r["municipio"] for r in csv.DictReader(f)}
    nao_mapeados = {v for v in valores if normalize_municipio(v) not in MUNICIPIOS_OFICIAIS.values()}
    assert nao_mapeados == set()


@pytest.mark.parametrize(
    "raw, esperado",
    [("alta", "alta"), ("Alta", "alta"), ("Média", "media"), ("media", "media"), ("Baixa", "baixa"),
     ("", None), (None, None), ("urgente", None)],
)
def test_normalize_prioridade(raw, esperado):
    assert normalize_prioridade(raw) == esperado


def linha(**kw):
    base = {"cid_principal": "K40.9", "nome_paciente": "Ana Souza", "municipio": "Pelotas",
            "prioridade_regulacao": "alta"}
    base.update(kw)
    return base


def test_linha_limpa_nao_gera_correcao():
    norm, correcoes = preprocess_solicitacao(linha())

    assert correcoes == []
    assert norm == {"cid_norm": "K409", "nome_norm": "ana souza", "municipio_norm": "Pelotas",
                    "prioridade_norm": "alta"}


def test_municipio_corrigido_vai_para_o_log_com_original_e_novo():
    _, correcoes = preprocess_solicitacao(linha(municipio="PORTO ALEGRE"))

    assert correcoes == [Correcao("municipio", "PORTO ALEGRE", "Porto Alegre", "PRE-03")]


def test_prioridade_corrigida_vai_para_o_log():
    _, correcoes = preprocess_solicitacao(linha(prioridade_regulacao="Média"))

    assert correcoes == [Correcao("prioridade_regulacao", "Média", "media", "PRE-04")]


def test_prioridade_desconhecida_vira_vazia_e_fica_registrada():
    norm, correcoes = preprocess_solicitacao(linha(prioridade_regulacao="urgente"))

    assert norm["prioridade_norm"] is None
    assert correcoes == [Correcao("prioridade_regulacao", "urgente", None, "PRE-04")]


def test_prioridade_vazia_nao_gera_correcao():
    _, correcoes = preprocess_solicitacao(linha(prioridade_regulacao=""))

    assert correcoes == []


def test_cid_sem_ponto_e_chave_de_comparacao_e_nao_gera_log():
    # D-17: K42.9 e K429 diferem de cid_norm só pelo ponto
    for cid in ("K42.9", "K429"):
        _, correcoes = preprocess_solicitacao(linha(cid_principal=cid))
        assert correcoes == []


def test_cid_com_defeito_alem_do_ponto_gera_log():
    norm, correcoes = preprocess_solicitacao(linha(cid_principal="k42.9 "))

    assert norm["cid_norm"] == "K429"
    assert correcoes == [Correcao("cid_principal", "k42.9 ", "K429", "PRE-01")]


def test_nome_nunca_gera_log():
    _, correcoes = preprocess_solicitacao(linha(nome_paciente="JUREMA QUADROS WEBER"))

    assert correcoes == []
