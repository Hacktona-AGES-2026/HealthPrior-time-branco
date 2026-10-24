"""Extrator de sinais de alarme por LLM via OpenRouter (modelo Jev, da TypeSafe).

Endpoint de decisões (/api/alpha/decisions): para cada frase do texto, o Jev escolhe uma
categoria de alarme (ou "nenhum") com probabilidade. O LLM só APONTA a frase (I-05); o domínio
valida (`domain/swalis.py`) e o sinal vira alerta para o regulador, sem mudar a classe.
Respostas ficam em cache num JSON para a demo não depender de rede: mesma entrada
(modelo + versão das perguntas + texto) devolve sempre o mesmo resultado.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path

import httpx

from app.domain.swalis import CategoriaSinal, SinalTexto
from app.domain.texto import frases

log = logging.getLogger(__name__)

URL = "https://openrouter.ai/api/alpha/decisions"
VERSAO_PROMPT = "sinais-v2-decisoes"
# Probabilidade mínima da categoria para virar alerta (provisório, ajustável).
PROB_MINIMA = 0.7

# Jev é um modelo de DECISÕES: não escreve texto, responde perguntas com probabilidades.
# Por isso perguntamos frase a frase; a citação é a própria frase (literal por construção).
CRITERIOS = {
    CategoriaSinal.RISCO_VIDA.value: "obstrução, encarceramento, irredutibilidade, sangramento ativo, "
                                     "infecção grave, instabilidade cardíaca/respiratória, "
                                     "risco de perda de órgão ou função",
    CategoriaSinal.SUSPEITA_MALIGNIDADE.value: "perda de peso, crescimento rápido, linfonodo suspeito, "
                                               "marcador tumoral em alta",
    CategoriaSinal.SINTOMA_GRAVE.value: "paciente acamado, incapacitado, quedas, úlcera de pressão",
    "nenhum": "nenhum sinal de alarme presente, ou o sinal está negado (sem, nega, ausência de, descarta)",
}

class ExtratorSinaisLLM:
    def __init__(self, api_key: str, modelo: str, cache_path: Path,
                 client: httpx.Client | None = None, timeout: float = 60.0,
                 apenas_cache: bool = False):
        self._api_key = api_key
        self._apenas_cache = apenas_cache
        self.modelo = modelo
        self._cache_path = cache_path
        self._client = client or httpx.Client(timeout=timeout)
        self._lock = threading.Lock()
        self._cache: dict[str, list[dict]] = (
            json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.is_file() else {}
        )

    def _chave(self, texto: str) -> str:
        return hashlib.sha256(f"{self.modelo}|{VERSAO_PROMPT}|{texto}".encode()).hexdigest()

    def em_cache(self, texto: str) -> bool:
        return self._chave(texto) in self._cache

    def extrair(self, texto: str, fonte: str) -> list[SinalTexto]:
        """Sinais citados pelo LLM. Falha de rede/modelo vira lista vazia (a palavra-chave segue)."""
        if not texto.strip():
            return []
        chave = self._chave(texto)
        brutos = self._cache.get(chave)
        if brutos is None:
            if not self._api_key or self._apenas_cache:
                return []
            try:
                brutos = self._chamar(texto)
            except (httpx.HTTPError, ValueError, KeyError, IndexError) as e:
                log.warning("LLM falhou (%s): %s", self.modelo, e)
                return []
            with self._lock:
                self._cache[chave] = brutos
        return [SinalTexto(CategoriaSinal(b["categoria"]), b["termo"], b["trecho"], fonte, "llm")
                for b in brutos if b.get("categoria") in CategoriaSinal._value2member_map_]

    def _chamar(self, texto: str) -> list[dict]:
        lista = frases(texto)
        if not lista:
            return []
        perguntas = {
            f"frase_{i}": {
                "type": "choice",
                "instructions": "Texto clínico de fila de cirurgia eletiva. Não classifique o paciente. "
                                f'Qual sinal de alarme está PRESENTE nesta frase: "{frase}"?',
                "criteria": CRITERIOS,
            }
            for i, frase in enumerate(lista)
        }
        resp = self._client.post(URL, headers={"Authorization": f"Bearer {self._api_key}"},
                                 json={"model": self.modelo, "state": texto, "questions": perguntas})
        resp.raise_for_status()
        respostas = resp.json()["answers"]
        sinais = []
        for i, frase in enumerate(lista):
            r = respostas.get(f"frase_{i}") or {}
            categoria = r.get("choice")
            prob = (r.get("probabilities") or {}).get(categoria, 0)
            if categoria in CategoriaSinal._value2member_map_ and prob >= PROB_MINIMA:
                sinais.append({"categoria": categoria, "termo": f"jev p={prob:.2f}", "trecho": frase})
        return sinais

    def salvar_cache(self) -> None:
        with self._lock:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
