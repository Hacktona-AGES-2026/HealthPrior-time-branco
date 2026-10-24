"""PRE-01..PRE-04 (US-02): funções puras, sem banco."""
import csv

import pytest

from app.config import settings
from app.domain.models import Correcao, Solicitacao
from app.domain.preprocessing.municipios import MUNICIPIOS_OFICIAIS
from app.domain.preprocessing.normalizacao import (
    normalizar_cid,
    normalizar_municipio,
    normalizar_nome,
    normalizar_prioridade,
    normalizar_solicitacao,
)


@pytest.mark.parametrize(
    "bruto, esperado",
    [("K42.9", "K429"), ("K429", "K429"), ("k42.9", "K429"), ("  c18.7 ", "C187"), ("", ""), (None, "")],
)
def test_cid(bruto, esperado):
    assert normalizar_cid(bruto) == esperado


def test_nome_mesma_pessoa_grafias_diferentes():
    # PAC-00087
    assert normalizar_nome("Jurema Quadros Weber") == normalizar_nome("JUREMA QUADROS WEBER")


def test_nome_ignora_acento_e_espaco_repetido():
    assert normalizar_nome("  João  da   Conceição ") == "joao da conceicao"


@pytest.mark.parametrize("bruto", ["Porto Alegre", "PORTO ALEGRE", "porto alegre", " porto  alegre "])
def test_municipio_porto_alegre(bruto):
    assert normalizar_municipio(bruto, MUNICIPIOS_OFICIAIS) == "Porto Alegre"


@pytest.mark.parametrize(
    "bruto, oficial",
    [("osorio", "Osório"), ("VIAMAO", "Viamão"), ("Gravatai", "Gravataí"), ("camaqua", "Camaquã")],
)
def test_municipio_recebe_o_nome_oficial_com_acento(bruto, oficial):
    assert normalizar_municipio(bruto, MUNICIPIOS_OFICIAIS) == oficial


def test_municipio_desconhecido_so_perde_espacos_sobrando():
    assert normalizar_municipio("  Vila   Nova ", MUNICIPIOS_OFICIAIS) == "Vila Nova"


def test_todo_municipio_do_dataset_esta_na_tabela():
    with (settings.data_dir / "fila_cirurgica.csv").open(encoding="utf-8", newline="") as f:
        valores = {r["municipio"] for r in csv.DictReader(f)}
    nao_mapeados = {
        v for v in valores
        if normalizar_municipio(v, MUNICIPIOS_OFICIAIS) not in MUNICIPIOS_OFICIAIS.values()
    }
    assert nao_mapeados == set()


@pytest.mark.parametrize(
    "bruto, esperado",
    [("alta", "alta"), ("Alta", "alta"), ("Média", "media"), ("media", "media"), ("Baixa", "baixa"),
     ("", None), ("  ", None), (None, None), ("urgente", None)],
)
def test_prioridade(bruto, esperado):
    assert normalizar_prioridade(bruto) == esperado


def solicitacao(**kw):
    base = dict(solicitacao_id="SOL-1", paciente_id="PAC-1", procedimento_id="PROC001",
                cid_principal="K40.9", data_entrada_fila=None, nome_paciente="Ana Souza",
                municipio="Pelotas", prioridade_regulacao="alta")
    base.update(kw)
    return Solicitacao(**base)


def test_linha_limpa_nao_gera_correcao():
    s, correcoes = normalizar_solicitacao(solicitacao(), MUNICIPIOS_OFICIAIS)

    assert correcoes == []
    assert (s.cid_norm, s.nome_norm, s.municipio_norm, s.prioridade_norm) == (
        "K409", "ana souza", "Pelotas", "alta")


def test_original_nao_e_alterado():
    original = solicitacao(municipio="PORTO ALEGRE", prioridade_regulacao="Média", cid_principal="k42.9 ")

    s, _ = normalizar_solicitacao(original, MUNICIPIOS_OFICIAIS)

    assert (s.municipio, s.prioridade_regulacao, s.cid_principal) == ("PORTO ALEGRE", "Média", "k42.9 ")
    assert original.municipio_norm is None  # a entrada não é mutada


def test_municipio_corrigido_vai_para_o_log_com_original_e_novo():
    _, correcoes = normalizar_solicitacao(solicitacao(municipio="PORTO ALEGRE"), MUNICIPIOS_OFICIAIS)

    assert correcoes == [Correcao("SOL-1", "municipio", "PORTO ALEGRE", "Porto Alegre", "PRE-03")]


def test_prioridade_corrigida_vai_para_o_log():
    _, correcoes = normalizar_solicitacao(solicitacao(prioridade_regulacao="Média"), MUNICIPIOS_OFICIAIS)

    assert correcoes == [Correcao("SOL-1", "prioridade_regulacao", "Média", "media", "PRE-04")]


def test_prioridade_desconhecida_vira_vazia_e_fica_registrada():
    s, correcoes = normalizar_solicitacao(solicitacao(prioridade_regulacao="urgente"), MUNICIPIOS_OFICIAIS)

    assert s.prioridade_norm is None
    assert correcoes == [Correcao("SOL-1", "prioridade_regulacao", "urgente", None, "PRE-04")]


def test_prioridade_vazia_nao_gera_correcao():
    _, correcoes = normalizar_solicitacao(solicitacao(prioridade_regulacao=""), MUNICIPIOS_OFICIAIS)

    assert correcoes == []


@pytest.mark.parametrize("cid", ["K42.9", "K429"])
def test_cid_sem_ponto_e_chave_de_comparacao_e_nao_gera_log(cid):
    # D-18: K42.9 e K429 diferem de cid_norm só pelo ponto
    _, correcoes = normalizar_solicitacao(solicitacao(cid_principal=cid), MUNICIPIOS_OFICIAIS)

    assert correcoes == []


def test_cid_com_defeito_alem_do_ponto_gera_log():
    s, correcoes = normalizar_solicitacao(solicitacao(cid_principal="k42.9 "), MUNICIPIOS_OFICIAIS)

    assert s.cid_norm == "K429"
    assert correcoes == [Correcao("SOL-1", "cid_principal", "k42.9 ", "K429", "PRE-01")]


def test_nome_nunca_gera_log():
    _, correcoes = normalizar_solicitacao(solicitacao(nome_paciente="JUREMA QUADROS WEBER"), MUNICIPIOS_OFICIAIS)

    assert correcoes == []
