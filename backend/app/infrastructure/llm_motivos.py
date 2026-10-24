"""Classificador de motivo por LLM (Jev via OpenRouter) para decisões com motivo `outro` (D-99).

Mesmo endpoint e padrão do `ExtratorSinaisLLM`: uma pergunta `choice` cujos critérios são os
motivos codificados (menos `outro`) mais "nenhum". O LLM só APONTA o motivo; quem agrupa e propõe
regra é o domínio. Sem chave, falha ou probabilidade baixa devolve None (o caso fica fora do
agrupamento). Respostas ficam em cache JSON: mesma entrada devolve sempre o mesmo resultado.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path

import httpx

from app.domain.enums import MotivoCodificado

log = logging.getLogger(__name__)

URL = "https://openrouter.ai/api/alpha/decisions"
VERSAO_PROMPT = "motivos-v1"
PROB_MINIMA = 0.5

CRITERIOS = {
    MotivoCodificado.PS_RECORRENTE.value: "idas repetidas ao pronto-socorro ou à emergência por causa da doença",
    MotivoCodificado.INTERNACAO_RELACIONADA.value: "internação hospitalar recente ligada à condição cirúrgica",
    MotivoCodificado.PROGRESSAO_IMAGEM.value: "exame de imagem mostra progressão ou piora do achado",
    MotivoCodificado.PIORA_FUNCIONAL.value: "piora funcional: perdeu autonomia, anda menos, dependente de terceiros, "
                                            "limitação nas atividades diárias",
    MotivoCodificado.DOR_INTENSA.value: "dor intensa, incapacitante ou em repouso",
    MotivoCodificado.BIOPSIA_POSITIVA.value: "biópsia ou anatomopatológico positivo para neoplasia",
    MotivoCodificado.SINAL_ALARME_TEXTO.value: "sinal de alarme descrito no texto: sangramento, obstrução, "
                                               "icterícia, encarceramento",
    MotivoCodificado.SUGESTAO_EXAGERADA.value: "a classe sugerida pelo sistema é exagerada para o quadro: "
                                               "caso estável, sem sintomas relevantes",
    MotivoCodificado.DADO_DESATUALIZADO.value: "informação do cadastro desatualizada ou incorreta (exame, "
                                               "dado clínico ou contato antigo)",
    "nenhum": "nenhum dos motivos acima, ou o texto é vago demais para saber",
}
_VALIDOS = {m.value for m in MotivoCodificado if m is not MotivoCodificado.OUTRO}


class ClassificadorMotivoLLM:
    def __init__(self, api_key: str, modelo: str, cache_path: Path,
                 client: httpx.Client | None = None, timeout: float = 60.0,
                 apenas_cache: bool = False):
        self._api_key = api_key
        self._apenas_cache = apenas_cache
        self.modelo = modelo
        self._cache_path = cache_path
        self._client = client or httpx.Client(timeout=timeout)
        self._lock = threading.Lock()
        self._cache: dict[str, str | None] = (
            json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.is_file() else {}
        )

    def _chave(self, texto: str) -> str:
        return hashlib.sha256(f"{self.modelo}|{VERSAO_PROMPT}|{texto}".encode()).hexdigest()

    def em_cache(self, texto: str) -> bool:
        return self._chave(texto) in self._cache

    def classificar(self, texto: str) -> MotivoCodificado | None:
        """Motivo codificado (nunca `outro`) ou None. Falha de rede/modelo vira None."""
        if not texto or not texto.strip():
            return None
        chave = self._chave(texto)
        if chave in self._cache:
            bruto = self._cache[chave]
        else:
            if not self._api_key or self._apenas_cache:
                return None
            try:
                bruto = self._chamar(texto)
            except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as e:
                log.warning("LLM falhou (%s): %s", self.modelo, e)
                return None
            with self._lock:
                self._cache[chave] = bruto
        return MotivoCodificado(bruto) if bruto in _VALIDOS else None

    def _chamar(self, texto: str) -> str | None:
        perguntas = {"motivo": {
            "type": "choice",
            "instructions": "Justificativa de um regulador que mudou ou manteve a classe de prioridade de "
                            f'um paciente na fila de cirurgia eletiva. Qual é o motivo? "{texto}"',
            "criteria": CRITERIOS,
        }}
        resp = self._client.post(URL, headers={"Authorization": f"Bearer {self._api_key}"},
                                 json={"model": self.modelo, "state": texto, "questions": perguntas})
        resp.raise_for_status()
        r = resp.json()["answers"].get("motivo") or {}
        escolha = r.get("choice")
        prob = (r.get("probabilities") or {}).get(escolha, 0)
        return escolha if escolha in _VALIDOS and prob >= PROB_MINIMA else None

    def salvar_cache(self) -> None:
        with self._lock:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
