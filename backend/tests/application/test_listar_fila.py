"""US-20 · ListarFila com repositórios falsos (sem banco)."""
from __future__ import annotations

from datetime import date, datetime

import pytest

from app.application.listar_fila import FiltroFila, ListarFila, PAGE_SIZE_MAXIMO
from app.domain.enums import ClasseStatus
from app.domain.models import LinhaFila, Solicitacao

AGORA = datetime(2026, 10, 24, 10, 0, 0)
VERSAO = "regras-1"


class FilaFalsa:
    def __init__(self, linhas=(), publicada_em=None):
        self._linhas = list(linhas)
        self._em = publicada_em

    def obter_publicada(self):
        return list(self._linhas)

    def publicada_em(self):
        return self._em


class SolicitacoesFalsas:
    def __init__(self, itens):
        self._itens = list(itens)
        self.apenas_ativas_usado = []

    def listar(self, apenas_ativas=True):
        self.apenas_ativas_usado.append(apenas_ativas)
        return list(self._itens)


def sol(sid, paciente="PAC-1", proc="PROC-1", esp="Urologia", cid="C61", onc=False, alertas=()):
    return Solicitacao(
        solicitacao_id=sid, paciente_id=paciente, procedimento_id=proc, cid_principal=cid,
        data_entrada_fila=date(2025, 1, 1), procedimento=f"Proc {proc}", especialidade=esp,
        oncologico=onc, alertas=list(alertas), classe_status=ClasseStatus.CONFIRMADA,
    )


def linha(sid, pos, camada=2, classe="B"):
    return LinhaFila(
        solicitacao_id=sid, posicao=pos, justificativa=f"just {sid}", camada=camada, classe=classe,
        pct_prazo_consumido=12.5, dias_em_fila=40, score_efetivo=1.0, editado_manualmente=False,
        versao_regras=VERSAO,
    )


def listar(linhas, solicitacoes, publicada_em=AGORA):
    return ListarFila(FilaFalsa(linhas, publicada_em), SolicitacoesFalsas(solicitacoes))


def test_sem_publicacao_nao_e_erro():
    pagina = listar([], [sol("SOL-1")], publicada_em=None).executar(FiltroFila())
    assert pagina.publicada is False
    assert pagina.itens == []
    assert pagina.total == 0
    assert pagina.versao_regras is None
    assert pagina.gerada_em is None


def test_junta_campos_da_solicitacao_e_da_linha():
    s = sol("SOL-1", cid="C18.7", onc=True, alertas=["contato_perdido"], esp="Cirurgia Oncologica")
    pagina = listar([linha("SOL-1", 1, camada=1, classe="A2")], [s]).executar(FiltroFila())
    assert pagina.publicada is True
    assert pagina.versao_regras == VERSAO
    assert pagina.gerada_em == AGORA
    assert pagina.total == 1
    item = pagina.itens[0]
    assert item.posicao == 1
    assert item.solicitacao_id == "SOL-1"
    assert item.camada == 1
    assert item.classe == "A2"
    assert item.classe_status == ClasseStatus.CONFIRMADA
    assert item.pct_prazo_consumido == 12.5
    assert item.dias_em_fila == 40
    assert item.procedimento == "Proc PROC-1"
    assert item.especialidade == "Cirurgia Oncologica"
    assert item.cid == "C18.7"
    assert item.oncologico is True
    assert item.editado_manualmente is False
    assert item.alertas == ["contato_perdido"]
    assert item.resumo_justificativa == "just SOL-1"


def test_busca_todas_as_solicitacoes_inclusive_inativas():
    repo = SolicitacoesFalsas([sol("SOL-1")])
    ListarFila(FilaFalsa([linha("SOL-1", 1)], AGORA), repo).executar(FiltroFila())
    assert repo.apenas_ativas_usado == [False]


def test_filtro_por_camada():
    linhas = [linha("SOL-1", 1, camada=1), linha("SOL-2", 2, camada=2), linha("SOL-3", 3, camada=2)]
    sols = [sol("SOL-1"), sol("SOL-2"), sol("SOL-3")]
    pagina = listar(linhas, sols).executar(FiltroFila(camada=2))
    assert [i.solicitacao_id for i in pagina.itens] == ["SOL-2", "SOL-3"]
    assert pagina.total == 2


def test_filtro_especialidade_sem_diferenciar_maiusculas():
    linhas = [linha("SOL-1", 1), linha("SOL-2", 2)]
    sols = [sol("SOL-1", esp="Urologia"), sol("SOL-2", esp="Cirurgia Geral")]
    pagina = listar(linhas, sols).executar(FiltroFila(especialidade="UROLOGIA"))
    assert [i.solicitacao_id for i in pagina.itens] == ["SOL-1"]


def test_filtro_procedimento_id():
    linhas = [linha("SOL-1", 1), linha("SOL-2", 2)]
    sols = [sol("SOL-1", proc="P-1"), sol("SOL-2", proc="P-2")]
    pagina = listar(linhas, sols).executar(FiltroFila(procedimento_id="P-2"))
    assert [i.solicitacao_id for i in pagina.itens] == ["SOL-2"]


def test_busca_por_parte_do_id_e_do_paciente():
    linhas = [linha("SOL-2023-00010", 1), linha("SOL-2025-00149", 2)]
    sols = [sol("SOL-2023-00010", paciente="PAC-AA"), sol("SOL-2025-00149", paciente="PAC-BB")]
    por_id = listar(linhas, sols).executar(FiltroFila(busca="2025-001"))
    assert [i.solicitacao_id for i in por_id.itens] == ["SOL-2025-00149"]
    por_paciente = listar(linhas, sols).executar(FiltroFila(busca="pac-aa"))
    assert [i.solicitacao_id for i in por_paciente.itens] == ["SOL-2023-00010"]


def test_paginacao_total_pagina_e_ordem_por_posicao():
    # Linhas entregues fora de ordem: a página deve sair ordenada por posição.
    linhas = [linha(f"SOL-{n}", n) for n in (3, 1, 5, 2, 4)]
    sols = [sol(f"SOL-{n}") for n in range(1, 6)]
    caso = listar(linhas, sols)

    pagina2 = caso.executar(FiltroFila(page=2, page_size=2))
    assert pagina2.total == 5
    assert [i.posicao for i in pagina2.itens] == [3, 4]

    pagina3 = caso.executar(FiltroFila(page=3, page_size=2))
    assert [i.posicao for i in pagina3.itens] == [5]

    pagina_vazia = caso.executar(FiltroFila(page=9, page_size=2))
    assert pagina_vazia.itens == []
    assert pagina_vazia.total == 5


def test_total_conta_apos_filtro_e_antes_de_paginar():
    linhas = [linha(f"SOL-{n}", n, camada=1 if n % 2 else 2) for n in range(1, 7)]
    sols = [sol(f"SOL-{n}") for n in range(1, 7)]
    pagina = listar(linhas, sols).executar(FiltroFila(camada=1, page=2, page_size=2))
    assert pagina.total == 3
    assert [i.posicao for i in pagina.itens] == [5]


def test_linha_sem_solicitacao_e_ignorada():
    linhas = [linha("SOL-1", 1), linha("SOL-FANTASMA", 2), linha("SOL-3", 3)]
    sols = [sol("SOL-1"), sol("SOL-3")]
    pagina = listar(linhas, sols).executar(FiltroFila())
    assert pagina.total == 2
    assert [i.solicitacao_id for i in pagina.itens] == ["SOL-1", "SOL-3"]


def test_page_size_acima_do_maximo_e_limitado():
    total = PAGE_SIZE_MAXIMO + 50
    linhas = [linha(f"SOL-{n}", n) for n in range(1, total + 1)]
    sols = [sol(f"SOL-{n}") for n in range(1, total + 1)]
    pagina = listar(linhas, sols).executar(FiltroFila(page_size=500))
    assert len(pagina.itens) == PAGE_SIZE_MAXIMO
    assert pagina.total == total


@pytest.mark.parametrize("filtro", [FiltroFila(page=0), FiltroFila(page_size=0)])
def test_paginacao_invalida_levanta_valueerror(filtro):
    with pytest.raises(ValueError):
        listar([linha("SOL-1", 1)], [sol("SOL-1")]).executar(filtro)
