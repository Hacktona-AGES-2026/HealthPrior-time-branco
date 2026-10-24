"""US-11 · agrupamento e tabela das exclusões."""
import pytest

from app.domain.enums import StatusFila
from app.domain.exclusoes import SEM_MOTIVO, agrupar_exclusoes, substituir_secao, tabela_markdown
from app.domain.models import Solicitacao


def sol(id_, status=StatusFila.ATIVA, motivo=None, onco=False):
    s = Solicitacao.__new__(Solicitacao)
    s.__dict__.update(solicitacao_id=id_, status_fila=status, motivo_status=motivo, oncologico=onco)
    return s


def test_ativas_nao_entram():
    assert agrupar_exclusoes([sol("A"), sol("B")]) == []


def test_agrupa_por_regra_com_contagem_e_ids_ordenados():
    grupos = agrupar_exclusoes([
        sol("S3", StatusFila.SUSPENSA, "PRE-23"), sol("S1", StatusFila.REMOVIDA, "PRE-20"),
        sol("S2", StatusFila.SUSPENSA, "PRE-23"), sol("S4"),
    ])
    assert [(g.regra, g.ids, g.quantidade) for g in grupos] == [("PRE-20", ("S1",), 1), ("PRE-23", ("S2", "S3"), 2)]
    assert (grupos[1].suspensas, grupos[1].removidas) == (2, 0)


def test_regra_mistura_suspensas_e_removidas_na_mesma_linha():
    (g,) = agrupar_exclusoes([sol("A", StatusFila.SUSPENSA, "PRE-22"), sol("B", StatusFila.REMOVIDA, "PRE-22")])
    assert (g.quantidade, g.suspensas, g.removidas) == (2, 1, 1)
    linha = tabela_markdown([g]).splitlines()[-1]
    assert "Operou pelo convênio (PRE-22) | 2 | A, B" in linha and "1 removida" in linha and "1 suspensa" in linha


def test_oncologica_fora_aparece_na_observacao():
    (g,) = agrupar_exclusoes([sol("O1", StatusFila.REMOVIDA, "PRE-21", onco=True)])
    assert g.oncologicas == ("O1",) and "oncológica: O1" in tabela_markdown([g])


def test_sem_motivo_nao_some():
    (g,) = agrupar_exclusoes([sol("X", StatusFila.SUSPENSA, None)])
    assert g.regra == SEM_MOTIVO and g.quantidade == 1


def test_tabela_vazia():
    assert "Nenhuma | 0" in tabela_markdown([])


def test_substitui_so_a_secao():
    doc = "# T\n\n## A\n\nx\n\n## Solicitações fora da fila\n\n> velho\n\n| a |\n\n## Premissas\n\ny\n"
    novo = substituir_secao(doc, "> novo\n\n| b |")
    assert "velho" not in novo and "| b |" in novo
    assert novo.startswith("# T\n\n## A\n\nx\n\n## Solicitações") and novo.endswith("\n## Premissas\n\ny\n")
    assert substituir_secao(novo, "> novo\n\n| b |") == novo  # idempotente


def test_secao_no_fim_do_documento_e_secao_ausente():
    assert substituir_secao("## Solicitações fora da fila\n\nvelho\n", "novo") == "## Solicitações fora da fila\n\nnovo\n"
    with pytest.raises(ValueError):
        substituir_secao("# sem seção\n", "x")
