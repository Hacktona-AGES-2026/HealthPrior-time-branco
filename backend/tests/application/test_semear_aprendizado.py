"""US-18 · Seed do aprendizado com fakes em memória."""
from collections import Counter
from datetime import date, datetime, timezone

from app.application.semear_aprendizado import PADROES, SemearAprendizado
from app.domain.aprendizado import ParametrosAprendizado, agrupar
from app.domain.cid import is_oncologico
from app.domain.enums import AcaoDecisao, MotivoCodificado
from app.domain.models import Solicitacao

REF = date(2026, 10, 23)


class Solicitacoes:
    def __init__(self, sols):
        self._s = sols

    def listar(self, apenas_ativas=True):
        return list(self._s)


class Decisoes:
    def __init__(self):
        self.itens = []

    def adicionar(self, d):
        self.itens.append(d)

    def listar_todas(self):
        return list(self.itens)


class Uow:
    confirmacoes = 0

    def confirmar(self):
        self.confirmacoes += 1


def _sol(i, proc, cid="K80", onco=False):
    return Solicitacao(solicitacao_id=f"S-{proc}-{i:02d}", paciente_id=f"P-{proc}-{i:02d}",
                       procedimento_id=proc, cid_principal=cid, cid_norm=cid, oncologico=onco,
                       data_entrada_fila=date(2025, 1, 1))


def _mundo():
    sols = []
    for p in PADROES:
        sols += [_sol(i, p.procedimento_id) for i in range(15)]
        # oncológicos: pela flag e pelo CID; nenhum pode ser usado
        sols += [_sol(90, p.procedimento_id, onco=True), _sol(91, p.procedimento_id, cid="C18.7")]
    return sols


def _rodar(decisoes=None):
    decisoes = decisoes or Decisoes()
    uow = Uow()
    n = SemearAprendizado(decisoes, Solicitacoes(_mundo()), uow, REF).executar()
    return n, decisoes, uow


def test_grava_33_decisoes_com_contagem_por_padrao():
    n, dec, uow = _rodar()
    assert n == 33 and uow.confirmacoes == 1
    assert [d.decisao_id for d in dec.itens][:2] == ["DEC-SEED-001", "DEC-SEED-002"]
    assert Counter(d.procedimento_id for d in dec.itens) == {
        "PROC004": 9, "PROC002": 9, "PROC018": 6, "PROC006": 4, "PROC001": 5}
    p1 = [d for d in dec.itens if d.procedimento_id == "PROC004"]
    assert Counter(d.acao for d in p1) == {AcaoDecisao.EDITAR: 8, AcaoDecisao.MANTER: 1}
    assert {d.regulador_id for d in p1} == {"reg-01", "reg-02", "reg-03", "reg-04"}
    p2 = [d for d in dec.itens if d.procedimento_id == "PROC002"]
    assert sum(d.motivo_codificado == MotivoCodificado.OUTRO for d in p2) == 2


def test_idempotente():
    _, dec, _ = _rodar()
    n2 = SemearAprendizado(dec, Solicitacoes(_mundo()), Uow(), REF).executar()
    assert n2 == 0 and len(dec.itens) == 33


def test_nao_usa_oncologico_nem_repete_paciente_no_padrao():
    sols = {s.solicitacao_id: s for s in _mundo()}
    _, dec, _ = _rodar()
    for d in dec.itens:
        s = sols[d.solicitacao_id]
        assert not s.oncologico and not is_oncologico(s.cid_norm)
    for proc in {d.procedimento_id for d in dec.itens}:
        pacientes = [sols[d.solicitacao_id].paciente_id for d in dec.itens if d.procedimento_id == proc]
        assert len(pacientes) == len(set(pacientes))


def test_datas_tz_aware_e_janela():
    _, dec, _ = _rodar()
    ref = datetime(2026, 10, 23, tzinfo=timezone.utc)
    for d in dec.itens:
        assert d.data.tzinfo is not None
        dias = (ref - d.data).days
        if d.procedimento_id == "PROC001":
            assert 119 <= dias <= 151
        else:
            assert 2 <= dias <= 60


def test_seed_produz_o_resultado_esperado_no_agrupamento():
    from app.domain.aprendizado import CasoAprendizado
    sols = {s.solicitacao_id: s for s in _mundo()}
    _, dec, _ = _rodar()
    casos = [CasoAprendizado(
        d.decisao_id, d.solicitacao_id, d.regulador_id, d.data, d.procedimento_id,
        d.motivo_codificado, d.classe_sugerida, d.classe_decidida, d.justificativa)
        for d in dec.itens if d.motivo_codificado != MotivoCodificado.OUTRO]
    r = agrupar(casos, datetime(2026, 10, 23, tzinfo=timezone.utc), ParametrosAprendizado(), {"PROC018"})
    por_id = {p.proposta_id: p for p in r}
    assert por_id["PROP-PROC004-ps_recorrente-C-B"].status == "pendente"
    assert por_id["PROP-PROC018-sugestao_exagerada-B-C"].status == "descartada"
    assert not any(p.procedimento_id in ("PROC006", "PROC001") for p in r)
