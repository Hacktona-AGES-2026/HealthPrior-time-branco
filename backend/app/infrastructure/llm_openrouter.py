"""Extrator de sinais de alarme por LLM via OpenRouter (modelo Jev, da TypeSafe).

Endpoint de decisões (/api/alpha/decisions): para cada frase do texto, o Jev escolhe qual ponto
do SWALIS ela descreve (ou "nenhum") com probabilidade. O LLM só APONTA e CITA a frase (I-05);
o domínio valida e as regras cruzam os pontos para decidir a classe (`domain/swalis.py`).
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
VERSAO_PROMPT = "pontos-v6-decisoes"
# Guarda no cache tudo a partir desta probabilidade; o domínio decide o que conta ou vai a revisar.
PROB_MINIMA = 0.4

# Jev é um modelo de DECISÕES: não escreve texto, responde perguntas com probabilidades.
# Por isso perguntamos frase a frase qual ponto do SWALIS ela descreve; a citação é a própria
# frase (literal por construção). Quem transforma pontos em classe são as regras do domínio.
# Descrições ancoradas na tabela SWALIS (data/referencias/swalis.csv), não nos textos do dataset.
CRITERIOS = {
    CategoriaSinal.OBSTRUCAO.value: "obstrução ou risco de estrangulamento AGORA: hérnia encarcerada, "
                                    "irredutível ou que não volta, suboclusão/obstrução intestinal, "
                                    "retenção urinária aguda",
    CategoriaSinal.RISCO_VIDA.value: "risco de vida se esperar: sangramento ativo ou com transfusão, "
                                     "sepse, colangite/icterícia, angina instável ou em repouso, síncope, "
                                     "insuficiência respiratória, compressão de via aérea",
    CategoriaSinal.PERDA_FUNCAO.value: "risco de perda IRREVERSÍVEL de órgão ou função se esperar: rim com "
                                       "hidronefrose e função caindo, glaucoma agudo, dano neurológico ou "
                                       "atrofia progressiva",
    CategoriaSinal.CANCER_CONFIRMADO.value: "câncer/neoplasia maligna DO PRÓPRIO PACIENTE confirmada "
                                            "por biópsia ou anatomopatológico",
    CategoriaSinal.SUSPEITA_MALIGNIDADE.value: "suspeita de câncer DO PRÓPRIO PACIENTE ainda não confirmada: perda de peso, "
                                               "crescimento rápido, linfonodo suspeito, marcador subindo",
    CategoriaSinal.DOR_INTENSA.value: "dor intensa, incapacitante ou em repouso",
    CategoriaSinal.SINTOMA_GRAVE.value: "incapacidade importante: acamado, dependente de terceiros, quedas "
                                        "de repetição, úlcera de pressão, não consegue andar",
    CategoriaSinal.SINTOMA_MODERADO.value: "dor ou limitação moderada: dor aos esforços, sintomas que "
                                           "atrapalham atividades, baixa visão por catarata",
    "nenhum": "nada disso: dado administrativo ou logístico (transporte, TFD, acompanhante, contato, "
              "documentos, agendamento), histórico, antecedente familiar (mãe, pai, irmã…), "
              "ou o achado está negado (sem, nega, nunca, ausência de, descarta)",
}

VERSAO_EVENTO = "evento-v1-decisoes"
PERGUNTA_EVENTO = ("Fila de cirurgia eletiva. O atendimento descrito é piora ou complicação da DOENÇA QUE "
                   "MOTIVOU A CIRURGIA (mesmo órgão/condição)? Não julgue gravidade, só a relação.")
CRITERIOS_EVENTO = {
    "relacionado": "piora, complicação ou sintoma da própria doença da cirurgia",
    "nao_relacionado": "outra condição, sem relação com a doença da cirurgia (ex.: descompensação de "
                       "diabetes, queda sem relação, outra doença)",
    "incerto": "não dá para saber pelo texto",
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
        return [SinalTexto(CategoriaSinal(b["categoria"]), b["termo"], b["trecho"], fonte, "llm",
                           b.get("confianca", 1.0))
                for b in brutos if b.get("categoria") in CategoriaSinal._value2member_map_]

    def _chamar(self, texto: str) -> list[dict]:
        lista = frases(texto)
        if not lista:
            return []
        perguntas = {
            f"frase_{i}": {
                "type": "choice",
                "instructions": "Texto clínico de fila de cirurgia eletiva. Não classifique o paciente. "
                                f'Qual achado clínico está PRESENTE nesta frase: "{frase}"?',
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
                sinais.append({"categoria": categoria, "termo": "jev", "trecho": frase,
                               "confianca": round(prob, 2)})
        return sinais

    # --- Relação de PS/internação com a cirurgia (camada 2 e piora na espera) ---------------

    def _chave_evento(self, estado: str) -> str:
        return hashlib.sha256(f"{self.modelo}|{VERSAO_EVENTO}|{estado}".encode()).hexdigest()

    def em_cache_evento(self, estado: str) -> bool:
        return self._chave_evento(estado) in self._cache

    def relacao_evento(self, estado: str) -> tuple[str, float] | None:
        """(escolha, probabilidade) do Jev: o atendimento é piora da doença da cirurgia?

        `estado` descreve a cirurgia e o atendimento. Sem cache e sem rede (ou `apenas_cache`): None,
        e quem chama mantém o evento contando (lado seguro).
        """
        chave = self._chave_evento(estado)
        bruto = self._cache.get(chave)
        if bruto is None:
            if not self._api_key or self._apenas_cache:
                return None
            try:
                resp = self._client.post(URL, headers={"Authorization": f"Bearer {self._api_key}"}, json={
                    "model": self.modelo, "state": estado,
                    "questions": {"relacao": {"type": "choice", "instructions": PERGUNTA_EVENTO,
                                              "criteria": CRITERIOS_EVENTO}}})
                resp.raise_for_status()
                r = resp.json()["answers"]["relacao"]
                escolha = r.get("choice")
                bruto = [{"escolha": escolha,
                          "p": round((r.get("probabilities") or {}).get(escolha, 0), 2)}]
            except (httpx.HTTPError, ValueError, KeyError) as e:
                log.warning("LLM falhou ao classificar evento (%s): %s", self.modelo, e)
                return None
            with self._lock:
                self._cache[chave] = bruto
        return bruto[0]["escolha"], bruto[0]["p"]

    def salvar_cache(self) -> None:
        with self._lock:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
