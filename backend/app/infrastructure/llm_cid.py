"""Sugestor de CID por LLM (PRE-12, D-125): lê o laudo e escolhe o código na tabela CID-10.

Modelo padrão `openai/gpt-6-luna` com `reasoning.effort = low`, via OpenRouter (chat completions
com tool calling): o modelo chama `buscar_cid` na tabela oficial e devolve CID + citação literal do
laudo. Medido nos 23 casos de câncer escondido do dataset: mediana 4,8 s, esforço médio deu o mesmo
CID e foi mais lento, o Pro levou ~22 s. O LLM só SUGERE (I-05): o domínio valida e o regulador decide.
Respostas ficam em cache num JSON, como as do Jev: a demo não depende de rede.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path

import httpx

from app.domain.models import SugestaoCid
from app.domain.ports import TabelaCid

log = logging.getLogger(__name__)

URL = "https://openrouter.ai/api/v1/chat/completions"
VERSAO_PROMPT = "cid-v1"
MAX_RODADAS = 5  # chamadas de ferramenta antes de desistir

SISTEMA = ("Você corrige o CID principal de uma solicitação cirúrgica a partir de um laudo novo "
           "(biópsia ou anatomopatológico). Use a ferramenta buscar_cid para achar o código na tabela "
           "CID-10 oficial; nunca invente código. Considere o procedimento e o CID atual para saber o "
           "órgão. Responda só com JSON: {\"cid\": \"X00.0\", \"descricao\": \"...\", "
           "\"citacao\": \"trecho copiado literalmente do laudo\", \"confianca\": 0.0-1.0}.")

FERRAMENTA = {"type": "function", "function": {
    "name": "buscar_cid",
    "description": "Busca códigos na tabela CID-10 do DATASUS por palavras da descrição (em português). "
                   "Devolve até 12 códigos com descrição.",
    "parameters": {"type": "object", "properties": {"consulta": {"type": "string"}},
                   "required": ["consulta"]}}}


class SugestorCidLLM:
    def __init__(self, api_key: str, modelo: str, esforco: str | None, cache_path: Path,
                 tabela: TabelaCid, client: httpx.Client | None = None, timeout: float = 60.0,
                 apenas_cache: bool = False):
        self._api_key = api_key
        self.modelo = modelo
        self._esforco = esforco
        self._cache_path = cache_path
        self._tabela = tabela
        self._client = client or httpx.Client(timeout=timeout)
        self._apenas_cache = apenas_cache
        self._lock = threading.Lock()
        self._cache: dict[str, dict] = (
            json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.is_file() else {}
        )

    def _chave(self, procedimento: str, cid_atual: str, cid_descricao: str, laudo: str) -> str:
        bruto = f"{self.modelo}|{self._esforco}|{VERSAO_PROMPT}|{procedimento}|{cid_atual}|{cid_descricao}|{laudo}"
        return hashlib.sha256(bruto.encode()).hexdigest()

    def sugerir(self, procedimento: str, cid_atual: str, cid_descricao: str,
                laudo: str) -> SugestaoCid | None:
        if not laudo.strip():
            return None
        chave = self._chave(procedimento, cid_atual, cid_descricao, laudo)
        bruto = self._cache.get(chave)
        if bruto is None:
            if not self._api_key or self._apenas_cache:
                return None
            try:
                bruto = self._chamar(procedimento, cid_atual, cid_descricao, laudo)
            except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as e:
                log.warning("Sugestão de CID falhou (%s): %s", self.modelo, e)
                return None
            with self._lock:
                self._cache[chave] = bruto
                self._salvar_cache()
        cid = str(bruto.get("cid") or "").strip().upper()
        if not cid:
            return None
        return SugestaoCid(cid=cid, descricao=str(bruto.get("descricao") or ""),
                           citacao=str(bruto.get("citacao") or ""),
                           confianca=float(bruto.get("confianca") or 0), modelo=self.modelo)

    def _chamar(self, procedimento: str, cid_atual: str, cid_descricao: str, laudo: str) -> dict:
        msgs: list[dict] = [
            {"role": "system", "content": SISTEMA},
            {"role": "user", "content": f"Procedimento: {procedimento}\nCID atual: {cid_atual} "
                                        f"({cid_descricao})\nLaudo: {laudo}"},
        ]
        for _ in range(MAX_RODADAS):
            corpo: dict = {"model": self.modelo, "messages": msgs, "tools": [FERRAMENTA]}
            if self._esforco:
                corpo["reasoning"] = {"effort": self._esforco}
            resp = self._client.post(URL, headers={"Authorization": f"Bearer {self._api_key}"}, json=corpo)
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            if not msg.get("tool_calls"):
                texto = (msg.get("content") or "").strip()
                return json.loads(texto[texto.find("{"):texto.rfind("}") + 1])
            msgs.append({"role": "assistant", "content": msg.get("content") or "",
                         "tool_calls": msg["tool_calls"]})
            for chamada in msg["tool_calls"]:
                consulta = json.loads(chamada["function"].get("arguments") or "{}").get("consulta", "")
                achados = [{"cid": c, "descricao": d} for c, d in self._tabela.buscar(consulta)]
                msgs.append({"role": "tool", "tool_call_id": chamada["id"],
                             "content": json.dumps(achados, ensure_ascii=False)})
        raise ValueError(f"sem resposta final em {MAX_RODADAS} rodadas")

    def _salvar_cache(self) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=1, sort_keys=True),
                                    encoding="utf-8")


def criar_sugestor_cid(apenas_cache: bool = False) -> SugestorCidLLM:
    """Composição a partir da configuração. Sem chave, só responde o que já estiver no cache."""
    from app.config import settings
    from app.infrastructure.tabela_cid import tabela_cid

    return SugestorCidLLM(settings.openrouter_api_key, settings.cid_llm_model,
                          settings.cid_llm_esforco or None, settings.cid_llm_cache_path,
                          tabela_cid(settings.data_dir), apenas_cache=apenas_cache)
