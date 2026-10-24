import json
from collections import Counter

import httpx
import pytest

from app.config import settings
from app.domain.enums import Classe
from app.infrastructure.csv_source import carregar_do_csv
from app.infrastructure.llm_openrouter import ExtratorSinaisLLM
from app.infrastructure.swalis_regras import SwalisRegras


def _resposta_decisoes(escolhas, prob=0.95):
    """Formato do /api/alpha/decisions: uma resposta `choice` por frase (frase_0, frase_1…)."""
    return {"answers": {f"frase_{i}": {"type": "choice", "choice": c,
                                        "probabilities": {c: prob, "nenhum": 1 - prob}}
                        for i, c in enumerate(escolhas)}}


def _extrator(tmp_path, handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return ExtratorSinaisLLM("chave-falsa", "typesafe/jev-1.14", tmp_path / "cache.json", client=client)


def test_llm_extrai_e_cacheia(tmp_path):
    chamadas = []

    def handler(req):
        chamadas.append(json.loads(req.content))
        return httpx.Response(200, json=_resposta_decisoes(["risco_vida"]))

    ext = _extrator(tmp_path, handler)
    [s] = ext.extrair("Hernia irredutivel ha 3 dias.", "observacoes")
    assert (s.categoria.value, s.origem, s.fonte) == ("risco_vida", "llm", "observacoes")
    assert s.trecho == "Hernia irredutivel ha 3 dias"  # a citação é a própria frase
    ext.extrair("Hernia irredutivel ha 3 dias.", "observacoes")
    assert len(chamadas) == 1  # segunda vez veio do cache
    assert chamadas[0]["model"] == "typesafe/jev-1.14"
    assert chamadas[0]["questions"]["frase_0"]["type"] == "choice"
    ext.salvar_cache()
    # Cache em disco: funciona sem chave e sem rede (demo offline).
    offline = ExtratorSinaisLLM("", "typesafe/jev-1.14", tmp_path / "cache.json",
                                client=httpx.Client(transport=httpx.MockTransport(lambda r: 1 / 0)))
    assert offline.extrair("Hernia irredutivel ha 3 dias.", "observacoes")


def test_falha_do_llm_nao_derruba(tmp_path):
    ext = _extrator(tmp_path, lambda req: httpx.Response(500))
    assert ext.extrair("qualquer texto", "observacoes") == []


def test_probabilidade_baixa_e_ignorada(tmp_path):
    ext = _extrator(tmp_path, lambda req: httpx.Response(200, json=_resposta_decisoes(["risco_vida"], 0.3)))
    assert ext.extrair("Dor leve.", "observacoes") == []


def test_frase_negada_apontada_pelo_llm_e_descartada(tmp_path):
    ext = _extrator(tmp_path, lambda req: httpx.Response(200, json=_resposta_decisoes(
        ["nenhum", "risco_vida"])))
    sol = carregar_do_csv(settings.data_dir)[0]
    s = next(s for s in sol if s.solicitacao_id == "SOL-2026-00239")  # hérnia com negação
    c = SwalisRegras(ext).classificar(s, [])
    assert c.progressao.nivel == 0 and not c.sinais


@pytest.fixture(scope="module")
def dataset():
    return carregar_do_csv(settings.data_dir)


def test_dataset_inteiro_sem_llm(dataset):
    sols, eventos = dataset
    swalis = SwalisRegras()
    classes = {s.solicitacao_id: swalis.calcular(s, eventos.get(s.solicitacao_id, []))
               for s in sols}
    assert len(classes) == 941
    # Regra de ouro na classe: nenhum C* abaixo de B.
    for s in sols:
        if s.oncologico:
            assert classes[s.solicitacao_id].classe_sistema in (Classe.A1, Classe.A2, Classe.B)
    contagem = Counter(r.classe_sistema for r in classes.values())
    assert all(contagem[c] > 0 for c in Classe)
    r = classes["SOL-2025-00048"]
    assert r.classe_sistema is Classe.A2 and r.motivos[0].sinal == "eixo_progressao"


def test_ponto_do_jev_entra_na_classe_com_trilha(tmp_path, dataset):
    sols, _ = dataset
    s = next(s for s in sols if s.solicitacao_id == "SOL-2026-00239")  # hérnia redutível, classe C
    # Frase 0 "Hernia inguinal bilateral redutivel, abaulamento aos esforcos" → obstrução (forçado)
    ext = _extrator(tmp_path, lambda req: httpx.Response(200, json=_resposta_decisoes(
        ["obstrucao", "nenhum"])))
    sem_llm = SwalisRegras().calcular(s, [])
    com_llm = SwalisRegras(ext).calcular(s, [])
    assert sem_llm.classe_sistema is Classe.C and com_llm.classe_sistema is Classe.A1
    [ponto] = [m for m in com_llm.motivos
               if m.sinal == "ponto:obstrucao:llm" and m.fonte == "justificativa_clinica"]
    assert ponto.evidencia == "Hernia inguinal bilateral redutivel, abaulamento aos esforcos"
    assert ponto.ref == "0.95"


def test_ponto_incerto_aparece_como_revisar(tmp_path, dataset):
    sols, _ = dataset
    s = next(s for s in sols if s.solicitacao_id == "SOL-2026-00239")
    ext = _extrator(tmp_path, lambda req: httpx.Response(200, json=_resposta_decisoes(
        ["risco_vida", "nenhum"], prob=0.5)))
    r = SwalisRegras(ext).calcular(s, [])
    assert r.classe_sistema is Classe.C
    assert any(m.sinal == "revisar:risco_vida" for m in r.motivos)


def test_geracao_usa_so_cache(tmp_path):
    ext = ExtratorSinaisLLM("chave", "m", tmp_path / "c.json", apenas_cache=True,
                            client=httpx.Client(transport=httpx.MockTransport(lambda r: 1 / 0)))
    assert ext.extrair("texto sem cache", "observacoes") == []


class _TabelaFalsa:
    def __init__(self, celulas):
        self.celulas = celulas

    def consultar(self, cid_3, faixa_idade):
        return self.celulas.get((cid_3, faixa_idade))


def _sol_fatores(**kw):
    from datetime import date

    from app.domain.models import Solicitacao
    base = dict(solicitacao_id="S1", paciente_id="P", procedimento_id="PR", cid_principal="C18.7",
                data_entrada_fila=date(2026, 9, 23), idade=75, comorbidades="ICC; DRC",
                intensidade_dor_eva=4, limitacao_funcional="leve")
    base.update(kw)
    return Solicitacao(**base)


def test_fatores_multiplicam_o_score_e_ficam_na_trilha():
    from datetime import date

    from app.domain.fatores import CelulaIrr
    tabela = _TabelaFalsa({("C18", "70-79"): CelulaIrr(4.0, 17966)})
    sem = SwalisRegras(ref_date=date(2026, 10, 23)).calcular(_sol_fatores(), [])
    com = SwalisRegras(ref_date=date(2026, 10, 23), tabela_irr=tabela).calcular(_sol_fatores(), [])
    assert sem.fator_contexto == 1.0 and sem.score_sistema == sem.pct_prazo_consumido
    # Charlson 3 (ICC 1 + DRC 2) -> 1,10; IRR 4 -> 1,15
    assert com.fator_contexto == pytest.approx(1.10 * 1.15)
    assert com.pct_prazo_consumido == sem.pct_prazo_consumido  # o % do prazo não muda
    assert com.score_sistema == round(sem.pct_prazo_consumido * 1.10 * 1.15, 1)
    assert {m.sinal for m in com.motivos} >= {"fator_comorbidade", "fator_idade"}
    assert com.classe_sistema == sem.classe_sistema  # fator não muda a classe
    assert com.versao_regras.endswith("+fatores-1")


def test_tabela_irr_csv_do_repo():
    from app.infrastructure.tabela_irr import TabelaIrrCsv
    celula = TabelaIrrCsv(settings.irr_path).consultar("C18", "70-79")
    assert celula is not None and celula.obitos == 17966 and celula.irr == pytest.approx(5.92, abs=0.01)


class _RelacaoFalsa:
    modelo = "falso"

    def __init__(self, resposta):
        self.resposta = resposta

    def relacao_evento(self, estado):
        return self.resposta

    def extrair(self, texto, fonte):
        return []


@pytest.mark.parametrize("resposta,marca", [
    (("nao_relacionado", 0.99), True),
    (("nao_relacionado", 0.85), False),   # abaixo de 0,9: continua contando (lado seguro)
    (("relacionado", 1.0), False),
    (None, False),                         # sem cache/rede: continua contando
])
def test_ps_sem_relacao_so_com_jev_muito_seguro(dataset, resposta, marca):
    from datetime import date
    from app.domain.models import Evento
    sols, _ = dataset
    s = next(x for x in sols if x.solicitacao_id == "SOL-2025-00045")
    ps = Evento("E1", s.solicitacao_id, s.paciente_id, date(2026, 10, 1), "pronto_socorro",
                "atendido_liberado", None, "Atendimento em PS por hiperglicemia (glicemia 380).")
    r = SwalisRegras(_RelacaoFalsa(resposta)).calcular(s, [ps])
    assert ps.sem_relacao is marca
    assert any(m.sinal == "evento_sem_relacao" for m in r.motivos) is marca


def test_camada_e_classe_leem_o_mesmo_ps_sem_relacao(dataset):
    # montar_fila: o scorer anota o PS antes da urgência; camada e "piora na espera" ficam coerentes.
    import copy
    from datetime import date
    from app.application.montar_fila import montar_fila
    from app.domain.models import Evento
    sols, eventos = copy.deepcopy(dataset)
    s = next(x for x in sols if x.solicitacao_id == "SOL-2025-00045")
    ps = Evento("E-PS", s.solicitacao_id, s.paciente_id, date(2026, 10, 1), "pronto_socorro",
                "atendido_liberado", None, "Atendimento em PS por hiperglicemia (glicemia 380).")
    eventos[s.solicitacao_id] = [ps]
    linha = next(l for l in montar_fila(sols, eventos, SwalisRegras(_RelacaoFalsa(("nao_relacionado", 1.0))),
                                        settings.ref_date) if l.solicitacao_id == s.solicitacao_id)
    assert linha.camada == 3 and "piora na espera" not in linha.justificativa
    assert "sem relação com a cirurgia" in linha.justificativa
