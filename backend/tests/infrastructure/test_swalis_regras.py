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
    ext = _extrator(tmp_path, lambda req: httpx.Response(200, json=_resposta_decisoes(["risco_vida"], 0.5)))
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


def test_llm_vira_alerta_sem_mudar_a_classe(tmp_path, dataset):
    sols, eventos = dataset
    s = next(s for s in sols if s.solicitacao_id == "SOL-2026-00239")
    texto = s.justificativa_clinica
    # Frase 0 de "Hernia inguinal bilateral redutivel, abaulamento aos esforcos. Sem sinais…"
    ext = _extrator(tmp_path, lambda req: httpx.Response(200, json=_resposta_decisoes(
        ["risco_vida", "nenhum"])))
    sem_llm = SwalisRegras().calcular(s, [])
    com_llm = SwalisRegras(ext).calcular(s, [])
    assert com_llm.classe_sistema is sem_llm.classe_sistema
    [alerta] = [m.evidencia for m in com_llm.motivos
                if m.sinal == "alerta_llm:risco_vida" and m.fonte == "justificativa_clinica"]
    assert alerta == "Hernia inguinal bilateral redutivel, abaulamento aos esforcos" and alerta in texto


def test_geracao_usa_so_cache(tmp_path):
    ext = ExtratorSinaisLLM("chave", "m", tmp_path / "c.json", apenas_cache=True,
                            client=httpx.Client(transport=httpx.MockTransport(lambda r: 1 / 0)))
    assert ext.extrair("texto sem cache", "observacoes") == []
