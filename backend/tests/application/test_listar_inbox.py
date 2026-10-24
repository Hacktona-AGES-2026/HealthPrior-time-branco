"""US-12 · ListarInbox com fakes (sem banco)."""
from __future__ import annotations

from datetime import date, datetime

from app.application.listar_inbox import ListarInbox
from app.domain.enums import Classe, ClasseStatus, StatusFila
from app.domain.models import Evento, LinhaFila, Motivo, ResultadoScore, Solicitacao

AGORA = datetime(2026, 10, 24, 10, 0, 0)


class FilaFalsa:
    def __init__(self, ids=(), publicada_em=AGORA):
        self._ids = list(ids)
        self._em = publicada_em

    def obter_publicada(self):
        return [LinhaFila(solicitacao_id=i, posicao=n, justificativa="", camada=2, classe="C",
                          pct_prazo_consumido=1.0, dias_em_fila=10 + n, score_efetivo=1.0,
                          editado_manualmente=False, versao_regras="r1")
                for n, i in enumerate(self._ids, start=1)]

    def publicada_em(self):
        return self._em if self._ids else None


class SolicitacoesFalsas:
    def __init__(self, itens):
        self._itens = list(itens)
        self.chamadas = 0

    def listar(self, apenas_ativas=True):
        self.chamadas += 1
        return [s for s in self._itens
                if not apenas_ativas or s.status_fila == StatusFila.ATIVA]


class EventosFalsos:
    def __init__(self, eventos=()):
        self._eventos = list(eventos)
        self.chamadas = 0

    def listar_todos(self):
        self.chamadas += 1
        return list(self._eventos)


class ScorerFalso:
    versao_regras = "r1"

    def __init__(self, classes, motivos=None):
        self._classes = classes
        self._motivos = motivos or {}
        self.vistos = {}

    def calcular(self, solicitacao, eventos):
        self.vistos[solicitacao.solicitacao_id] = eventos
        return ResultadoScore(self._classes[solicitacao.solicitacao_id], 60, 10.0, 1.0,
                              self._motivos.get(solicitacao.solicitacao_id, []), "r1")


def sol(sid, prioridade="baixa", status=ClasseStatus.SUGERIDA_NAO_CONFIRMADA, confirmada=None,
        ativa=True, **kw):
    return Solicitacao(
        solicitacao_id=sid, paciente_id="P-" + sid, procedimento_id="PR", cid_principal="K80",
        data_entrada_fila=date(2025, 1, 1), procedimento="Proc " + sid,
        prioridade_norm=prioridade, classe_status=status, classe_confirmada=confirmada,
        status_fila=StatusFila.ATIVA if ativa else StatusFila.SUSPENSA, **kw)


def caso(ids, sols, classes, eventos=(), motivos=None, publicada_em=AGORA):
    scorer = ScorerFalso(classes, motivos)
    return ListarInbox(FilaFalsa(ids, publicada_em), SolicitacoesFalsas(sols),
                       EventosFalsos(eventos), scorer), scorer


def test_sem_publicacao_vazio():
    uc, _ = caso([], [sol("S1")], {"S1": Classe.A1})
    r = uc.executar()
    assert r.total == 0 and r.itens == []


def test_so_ativos_na_fila_publicada():
    sols = [sol("S1"), sol("S2", ativa=False), sol("S3")]
    classes = {"S1": Classe.A1, "S2": Classe.A1, "S3": Classe.A1}
    uc, scorer = caso(["S1", "S2"], sols, classes)
    r = uc.executar()
    assert [i.solicitacao_id for i in r.itens] == ["S1"]
    assert set(scorer.vistos) == {"S1"}


def test_criterio_nunca_confirmado():
    sols = [sol("S1", "baixa"), sol("S2", "baixa"), sol("S3", "alta")]
    classes = {"S1": Classe.B, "S2": Classe.C, "S3": Classe.D}
    uc, _ = caso(["S1", "S2", "S3"], sols, classes)
    assert {i.solicitacao_id for i in uc.executar().itens} == {"S1", "S3"}


def test_criterio_confirmado():
    sols = [sol("S1", status=ClasseStatus.CONFIRMADA, confirmada=Classe.B),
            sol("S2", status=ClasseStatus.CONFIRMADA, confirmada=Classe.B)]
    classes = {"S1": Classe.C, "S2": Classe.B}
    uc, _ = caso(["S1", "S2"], sols, classes)
    r = uc.executar()
    assert [i.solicitacao_id for i in r.itens] == ["S1"]
    assert r.itens[0].classe_atual == Classe.B and r.itens[0].classe_sugerida == Classe.C


def test_ordem_grave_distancia_posicao():
    sols = [sol("S1", "baixa"), sol("S2", "baixa"), sol("S3", "baixa"), sol("S4", "baixa")]
    classes = {"S1": Classe.B, "S2": Classe.A1, "S3": Classe.A2, "S4": Classe.B}
    uc, _ = caso(["S1", "S2", "S3", "S4"], sols, classes)
    assert [i.solicitacao_id for i in uc.executar().itens] == ["S2", "S3", "S1", "S4"]
    assert uc.executar().total == 4


def test_busca_uma_vez_e_agrupa_eventos():
    ev = [Evento("E1", "S1", "P", date(2026, 1, 1), "ps"), Evento("E2", "S2", "P", date(2026, 1, 2), "ps")]
    sols = [sol("S1"), sol("S2")]
    uc, scorer = caso(["S1", "S2"], sols, {"S1": Classe.A1, "S2": Classe.A1}, eventos=ev)
    uc.executar()
    assert uc._solicitacoes.chamadas == 1 and uc._eventos.chamadas == 1
    assert [e.evento_id for e in scorer.vistos["S1"]] == ["E1"]
    assert [e.evento_id for e in scorer.vistos["S2"]] == ["E2"]


def test_evento_gatilho_e_editado_anteriormente():
    motivos = {"S1": [Motivo("a", "x", "justificativa_clinica", ref="J"),
                      Motivo("b", "y", "evento", ref="EVT-9"),
                      Motivo("c", "z", "evento", ref="EVT-10")],
               "S2": [Motivo("a", "x", "observacoes")]}
    em = datetime(2026, 5, 1, 9, 0)
    sols = [sol("S1", editado_por="reg-1", editado_em=em), sol("S2")]
    uc, _ = caso(["S1", "S2"], sols, {"S1": Classe.A1, "S2": Classe.A2}, motivos=motivos)
    s1, s2 = uc.executar().itens
    assert s1.evento_gatilho == "EVT-9"
    assert s1.editado_anteriormente == ("reg-1", em)
    assert s1.criado_em == AGORA and s1.camada == 2 and s1.dias_em_fila == 11
    assert len(s1.motivos) == 3
    assert s2.evento_gatilho is None and s2.editado_anteriormente is None


def test_sugestao_ja_avaliada_nao_volta_ao_inbox():
    # Regulador editou para B recusando a sugestão D: o paciente sai do inbox; volta se a
    # sugestão mudar (D-77).
    from app.domain.enums import AcaoDecisao
    from app.domain.models import Decisao

    class DecisoesFalsas:
        def __init__(self, sugerida):
            self.sugerida = sugerida

        def listar_por_solicitacao(self, sid):
            return [Decisao("DEC-1", sid, "R", AcaoDecisao.EDITAR, AGORA, self.sugerida, Classe.B)]

    s = sol("S1", status=ClasseStatus.CONFIRMADA, confirmada=Classe.B)
    uc, _ = caso(["S1"], [s], {"S1": Classe.D})
    assert uc.executar().total == 1  # sem log de decisões: entra
    uc._decisoes = DecisoesFalsas(Classe.D)
    assert uc.executar().total == 0  # a sugestão D já foi avaliada
    uc._decisoes = DecisoesFalsas(Classe.C)
    assert uc.executar().total == 1  # sugestão mudou desde a decisão


def test_inbox_traz_previa_de_aprovar_quando_tem_data():
    s = sol("S1")
    uc, _ = caso(["S1"], [s], {"S1": Classe.A1})
    assert uc.executar().itens[0].previa is None  # sem data de referência: sem prévia
    uc._ref_date = date(2026, 10, 23)
    p = uc.executar().itens[0].previa
    assert p is not None and p.classe is Classe.A1 and p.posicao_estimada == 1
