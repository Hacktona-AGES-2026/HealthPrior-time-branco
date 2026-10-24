"""Classificador de motivo (D-95) com httpx.MockTransport: sem rede."""
import httpx

from app.domain.enums import MotivoCodificado
from app.infrastructure.llm_motivos import ClassificadorMotivoLLM


def _cliente(escolha="piora_funcional", prob=0.9, chamadas=None, status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        if chamadas is not None:
            chamadas.append(request)
        if status != 200:
            return httpx.Response(status)
        return httpx.Response(200, json={"answers": {"motivo": {
            "choice": escolha, "probabilities": {escolha: prob}}}})
    return httpx.Client(transport=httpx.MockTransport(handler))


def _clf(tmp_path, api_key="k", **kw):
    return ClassificadorMotivoLLM(api_key, "m", tmp_path / "c.json", client=_cliente(**kw))


def test_acerto_devolve_o_motivo(tmp_path):
    assert _clf(tmp_path).classificar("ele piorou muito") == MotivoCodificado.PIORA_FUNCIONAL


def test_envia_pergunta_choice_sem_outro_e_com_nenhum(tmp_path):
    chamadas = []
    ClassificadorMotivoLLM("k", "m", tmp_path / "c.json",
                           client=_cliente(chamadas=chamadas)).classificar("texto")
    corpo = __import__("json").loads(chamadas[0].content)
    pergunta = corpo["questions"]["motivo"]
    assert pergunta["type"] == "choice"
    assert "outro" not in pergunta["criteria"] and "nenhum" in pergunta["criteria"]
    assert chamadas[0].headers["authorization"] == "Bearer k"


def test_cache_evita_segunda_chamada_e_persiste(tmp_path):
    chamadas = []
    clf = ClassificadorMotivoLLM("k", "m", tmp_path / "c.json", client=_cliente(chamadas=chamadas))
    assert clf.classificar("x") == clf.classificar("x") == MotivoCodificado.PIORA_FUNCIONAL
    assert len(chamadas) == 1
    clf.salvar_cache()
    novo = ClassificadorMotivoLLM("", "m", tmp_path / "c.json")  # sem chave: só cache
    assert novo.classificar("x") == MotivoCodificado.PIORA_FUNCIONAL


def test_sem_chave_devolve_none(tmp_path):
    assert _clf(tmp_path, api_key="").classificar("qualquer") is None


def test_probabilidade_baixa_devolve_none(tmp_path):
    assert _clf(tmp_path, prob=0.3).classificar("vago") is None


def test_nenhum_e_outro_devolvem_none(tmp_path):
    assert _clf(tmp_path, escolha="nenhum").classificar("a") is None
    assert _clf(tmp_path, escolha="outro").classificar("b") is None


def test_falha_de_rede_devolve_none_e_nao_cacheia(tmp_path):
    clf = _clf(tmp_path, status=500)
    assert clf.classificar("x") is None and not clf.em_cache("x")


def test_texto_vazio_devolve_none(tmp_path):
    assert _clf(tmp_path).classificar("  ") is None
