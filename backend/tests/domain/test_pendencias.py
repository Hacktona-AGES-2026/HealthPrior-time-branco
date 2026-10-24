"""US-07: regras puras da resolução de pendências, sem banco."""
from datetime import date

import pytest

from app.domain.enums import ResolucaoPendencia as R
from app.domain.enums import StatusFila, StatusPendencia
from app.domain.errors import ObservacaoObrigatoriaError, ResolucaoInvalidaError
from app.domain.models import Correcao, Solicitacao
from app.domain.pendencias import RESOLUCOES_POR_REGRA, STATUS_DA_PENDENCIA, fundir, validar_resolucao


def solicitacao(sol_id, entrada, paciente="PAC-00151", proc="PROC003", **kw):
    return Solicitacao(solicitacao_id=sol_id, paciente_id=paciente, procedimento_id=proc,
                       cid_principal="K42.9", data_entrada_fila=entrada, **kw)


@pytest.mark.parametrize("regra, resolucao", [
    ("PRE-20", R.FUNDIR), ("PRE-20", R.REATIVAR), ("PRE-20", R.DESCARTAR),
    ("PRE-21", R.CONFIRMAR_SAIDA), ("PRE-22", R.CONFIRMAR_SAIDA), ("PRE-23", R.CONFIRMAR_SAIDA),
    ("PRE-25", R.CONFIRMAR_SAIDA), ("PRE-23", R.REATIVAR), ("PRE-25", R.DESCARTAR),
    ("PRE-24", R.DESCARTAR),
    ("PRE-10", R.REATIVAR), ("PRE-11", R.DESCARTAR), ("PRE-12", R.REATIVAR), ("PRE-13", R.DESCARTAR),
])
def test_resolucoes_aceitas(regra, resolucao):
    validar_resolucao(regra, resolucao, "Confirmado por telefone.")  # não levanta


@pytest.mark.parametrize("regra, resolucao", [
    ("PRE-20", R.CONFIRMAR_SAIDA),  # duplicata funde, não "confirma saída"
    ("PRE-23", R.FUNDIR),
    ("PRE-24", R.REATIVAR), ("PRE-24", R.CONFIRMAR_SAIDA), ("PRE-24", R.FUNDIR),
    ("PRE-10", R.CONFIRMAR_SAIDA), ("PRE-13", R.FUNDIR),
    ("PRE-99", R.DESCARTAR),  # regra desconhecida
])
def test_resolucoes_que_a_regra_nao_aceita(regra, resolucao):
    with pytest.raises(ResolucaoInvalidaError) as erro:
        validar_resolucao(regra, resolucao, "x")

    assert regra in erro.value.mensagem and erro.value.status_http == 422


@pytest.mark.parametrize("observacao", [None, "", "   "])
def test_confirmar_saida_exige_observacao(observacao):
    with pytest.raises(ObservacaoObrigatoriaError) as erro:
        validar_resolucao("PRE-23", R.CONFIRMAR_SAIDA, observacao)

    assert erro.value.codigo == "OBSERVACAO_OBRIGATORIA"


@pytest.mark.parametrize("regra, resolucao", [("PRE-20", R.FUNDIR), ("PRE-23", R.REATIVAR), ("PRE-24", R.DESCARTAR)])
def test_as_outras_resolucoes_nao_exigem_observacao(regra, resolucao):
    validar_resolucao(regra, resolucao, None)


def test_toda_regra_de_pendencia_tem_resolucao():
    esperadas = {"PRE-10", "PRE-11", "PRE-12", "PRE-13", "PRE-20", "PRE-21", "PRE-22", "PRE-23", "PRE-24", "PRE-25"}

    assert set(RESOLUCOES_POR_REGRA) == esperadas and all(RESOLUCOES_POR_REGRA.values())


def test_so_descartar_termina_como_descartada():
    assert STATUS_DA_PENDENCIA[R.DESCARTAR] == StatusPendencia.DESCARTADA
    assert {STATUS_DA_PENDENCIA[r] for r in (R.CONFIRMAR_SAIDA, R.FUNDIR, R.REATIVAR)} == {StatusPendencia.RESOLVIDA}


# --- fundir (PRE-20) ---

def test_fundir_mantendo_a_mais_antiga_nao_altera_data():
    # PAC-00151: SOL-2025-00290 (19/09/2025) e SOL-2025-00348 (19/10/2025)
    antiga, nova = solicitacao("SOL-2025-00290", date(2025, 9, 19)), solicitacao("SOL-2025-00348", date(2025, 10, 19))

    correcoes = fundir(permanece=antiga, removida=nova)

    assert correcoes == []
    assert antiga.data_entrada_fila == date(2025, 9, 19)
    assert (nova.status_fila, nova.motivo_status) == (StatusFila.REMOVIDA, "PRE-20")


def test_fundir_mantendo_a_mais_nova_herda_a_data_mais_antiga_e_registra():
    antiga, nova = solicitacao("SOL-2025-00290", date(2025, 9, 19)), solicitacao("SOL-2025-00348", date(2025, 10, 19))

    correcoes = fundir(permanece=nova, removida=antiga)

    assert nova.data_entrada_fila == date(2025, 9, 19)
    assert correcoes == [Correcao("SOL-2025-00348", "data_entrada_fila", "2025-10-19", "2025-09-19", "PRE-20")]
    assert (antiga.status_fila, antiga.motivo_status) == (StatusFila.REMOVIDA, "PRE-20")


@pytest.mark.parametrize("kw, trecho", [
    ({"paciente": "PAC-99999"}, "mesmo paciente"),
    ({"proc": "PROC999"}, "mesmo paciente"),
])
def test_fundir_so_o_mesmo_paciente_e_procedimento(kw, trecho):
    with pytest.raises(ResolucaoInvalidaError, match=trecho):
        fundir(solicitacao("SOL-A", date(2025, 1, 1)), solicitacao("SOL-B", date(2025, 2, 1), **kw))


def test_nao_funde_com_ela_mesma():
    s = solicitacao("SOL-A", date(2025, 1, 1))

    with pytest.raises(ResolucaoInvalidaError, match="ela mesma"):
        fundir(s, s)


def test_quem_permanece_nao_pode_estar_removida():
    ja_removida = solicitacao("SOL-A", date(2025, 1, 1), status_fila=StatusFila.REMOVIDA)

    with pytest.raises(ResolucaoInvalidaError, match="já foi removida"):
        fundir(ja_removida, solicitacao("SOL-B", date(2025, 2, 1)))
