"""PRE-12 · Cliente do LLM de CID (D-117), sem rede: transporte HTTP falso do httpx."""
import json

import httpx

from app.infrastructure.llm_cid import SugestorCidLLM


class TabelaFalsa:
    def __init__(self):
        self.consultas = []

    def descricao(self, cid):
        return "Neoplasia maligna do cólon, não especificado" if cid.replace(".", "") == "C189" else None

    def buscar(self, consulta, limite=12):
        self.consultas.append(consulta)
        return [("C18.9", "Neoplasia maligna do cólon, não especificado")]


def _resposta_ferramenta():
    return {"choices": [{"message": {"content": "", "tool_calls": [{
        "id": "t1", "type": "function",
        "function": {"name": "buscar_cid", "arguments": json.dumps({"consulta": "neoplasia maligna colon"})}}]}}]}


def _resposta_final():
    final = {"cid": "c18.9", "descricao": "Neoplasia maligna do cólon", "citacao": "carcinoma papilifero",
             "confianca": 0.85}
    return {"choices": [{"message": {"content": "```json\n" + json.dumps(final) + "\n```"}}]}


def _sugestor(tmp_path, respostas, pedidos, **kw):
    def responder(req):
        pedidos.append(json.loads(req.content))
        return httpx.Response(200, json=respostas.pop(0))
    return SugestorCidLLM(kw.pop("chave", "sk-teste"), "openai/gpt-6-luna", "low", tmp_path / "cache.json",
                          TabelaFalsa(), client=httpx.Client(transport=httpx.MockTransport(responder)), **kw)


def test_chama_a_ferramenta_e_devolve_a_sugestao(tmp_path):
    pedidos = []
    s = _sugestor(tmp_path, [_resposta_ferramenta(), _resposta_final()], pedidos)

    r = s.sugerir("Colectomia", "D37.4", "Neoplasia de comportamento incerto", "Biopsia: carcinoma papilifero.")

    assert (r.cid, r.citacao, r.confianca, r.modelo) == ("C18.9", "carcinoma papilifero", 0.85, "openai/gpt-6-luna")
    assert len(pedidos) == 2
    assert pedidos[0]["reasoning"] == {"effort": "low"} and pedidos[0]["tools"][0]["function"]["name"] == "buscar_cid"
    # o resultado da busca na tabela volta para o modelo como mensagem de ferramenta
    assert pedidos[1]["messages"][-1]["role"] == "tool" and "C18.9" in pedidos[1]["messages"][-1]["content"]


def test_segunda_vez_vem_do_cache_sem_rede(tmp_path):
    pedidos = []
    s = _sugestor(tmp_path, [_resposta_ferramenta(), _resposta_final()], pedidos)
    s.sugerir("Colectomia", "D37.4", "x", "Biopsia: carcinoma papilifero.")

    outro = _sugestor(tmp_path, [], pedidos, apenas_cache=True)  # lê o cache gravado em disco
    r = outro.sugerir("Colectomia", "D37.4", "x", "Biopsia: carcinoma papilifero.")

    assert r.cid == "C18.9" and len(pedidos) == 2


def test_sem_chave_ou_so_cache_nao_chama(tmp_path):
    pedidos = []
    assert _sugestor(tmp_path, [], pedidos, chave="").sugerir("Colectomia", "D37.4", "x", "laudo") is None
    assert _sugestor(tmp_path, [], pedidos, apenas_cache=True).sugerir("Colectomia", "D37.4", "x", "laudo") is None
    assert pedidos == []


def test_falha_http_vira_none(tmp_path):
    def falhar(req):
        return httpx.Response(500, json={"erro": "x"})
    s = SugestorCidLLM("sk", "m", "low", tmp_path / "c.json", TabelaFalsa(),
                       client=httpx.Client(transport=httpx.MockTransport(falhar)))

    assert s.sugerir("Colectomia", "D37.4", "x", "laudo") is None
    assert not (tmp_path / "c.json").exists()  # falha não entra no cache
