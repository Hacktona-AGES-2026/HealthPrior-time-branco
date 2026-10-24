"""US-09 · GerarFila com repositórios, scorer e exportador falsos (sem banco)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from app.application.gerar_fila import GerarFila, ResultadoGeracao
from app.domain.enums import Classe, StatusFila
from app.domain.models import Evento, ResultadoScore, Solicitacao

REF = date(2026, 10, 23)


class SolicitacoesFalsas:
    def __init__(self, itens):
        self._itens = itens

    def listar(self, apenas_ativas=True):
        return [s for s in self._itens
                if not apenas_ativas or s.status_fila == StatusFila.ATIVA]


class EventosFalsos:
    def __init__(self, itens):
        self._itens = itens

    def listar_todos(self):
        return list(self._itens)


class ScorerFalso:
    versao_regras = "falso-1"

    def __init__(self, scores=None):
        self.scores = scores or {}

    def calcular(self, solicitacao, eventos):
        s = self.scores.get(solicitacao.solicitacao_id, 0.0)
        return ResultadoScore(Classe.C, 180, s, s, [], self.versao_regras)


class ExportadorFalso:
    def __init__(self):
        self.linhas = None
        self.caminho = None

    def exportar(self, linhas, caminho):
        self.linhas, self.caminho = linhas, caminho
        return caminho


def sol(sid, cid="K40.9", onco=False, **kw):
    base = dict(solicitacao_id=sid, paciente_id="P", procedimento_id="PR", cid_principal=cid,
                data_entrada_fila=date(2026, 1, 1), cid_norm=cid.replace(".", ""),
                oncologico=onco, intensidade_dor_eva=1, limitacao_funcional="nenhuma",
                justificativa_clinica="Quadro estavel.")
    base.update(kw)
    return Solicitacao(**base)


def montar(solicitacoes, eventos=(), scores=None):
    exportador = ExportadorFalso()
    caso = GerarFila(SolicitacoesFalsas(solicitacoes), EventosFalsos(eventos),
                     ScorerFalso(scores), exportador, REF)
    return caso, exportador


def test_suspensa_nao_sai_na_fila():
    suspensa = sol("S2", status_fila=StatusFila.SUSPENSA)
    caso, exp = montar([sol("S1"), suspensa])

    r = caso.executar(Path("x.csv"))

    assert [l.solicitacao_id for l in r.linhas] == ["S1"]
    assert [d["solicitacao_id"] for d in exp.linhas] == ["S1"]


def test_oncologico_fica_acima_de_nao_urgente_com_score_maior():
    caso, _ = montar([sol("NU"), sol("ON", cid="C18.7", onco=True)], scores={"NU": 99, "ON": 1})

    r = caso.executar(Path("x.csv"))

    assert [l.solicitacao_id for l in r.linhas] == ["ON", "NU"]
    assert [l.posicao for l in r.linhas] == [1, 2]


def test_eventos_sao_agrupados_por_solicitacao():
    piora = Evento("E1", "A", "P", date(2026, 5, 1), "consulta_reavaliacao", "piora")
    fora = Evento("E2", "ZZZ", "P", date(2026, 5, 1), "consulta_reavaliacao", "piora")
    caso, _ = montar([sol("A"), sol("B")], eventos=[piora, fora], scores={"A": 1, "B": 50})

    r = caso.executar(Path("x.csv"))

    camadas = {l.solicitacao_id: l.camada for l in r.linhas}
    assert camadas == {"A": 2, "B": 3}
    assert r.linhas[0].solicitacao_id == "A"


def test_resultado_total_e_por_camada():
    piora = Evento("E1", "U", "P", date(2026, 5, 1), "consulta_reavaliacao", "piora")
    caso, _ = montar([sol("O", cid="C18.7", onco=True), sol("U"), sol("N1"), sol("N2")],
                     eventos=[piora])

    r = caso.executar(Path("x.csv"))

    assert isinstance(r, ResultadoGeracao)
    assert r.total == 4
    assert r.por_camada == {1: 1, 2: 1, 3: 2}
    assert r.versao_regras == "falso-1"


def test_exportador_recebe_o_caminho_pedido():
    caso, exp = montar([sol("S1")])
    destino = Path("saida/fila.csv")

    r = caso.executar(destino)

    assert exp.caminho == destino
    assert r.caminho_csv == destino
