"""US-02 · Normalização (C-05, PRE-01..PRE-04).

Idempotente: recalcula as colunas *_norm e refaz o log dessas regras do zero, sem tocar nos
valores originais nem no log de outras regras. Não confirma a transação (ver UnidadeDeTrabalho).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from app.domain.ports import CorrecaoRepository, SolicitacaoRepository
from app.domain.preprocessing.municipios import MUNICIPIOS_OFICIAIS
from app.domain.preprocessing.normalizacao import REGRAS_NORMALIZACAO, normalizar_solicitacao


@dataclass
class ResumoNormalizacao:
    solicitacoes: int = 0
    correcoes: int = 0
    por_regra: dict[str, int] = field(default_factory=dict)


class Normalizar:
    def __init__(self, solicitacoes: SolicitacaoRepository, correcoes: CorrecaoRepository):
        self._solicitacoes = solicitacoes
        self._correcoes = correcoes

    def executar(self) -> ResumoNormalizacao:
        normalizadas, log = [], []
        for s in self._solicitacoes.listar(apenas_ativas=False):
            nova, correcoes = normalizar_solicitacao(s, MUNICIPIOS_OFICIAIS)
            normalizadas.append(nova)
            log.extend(correcoes)
        self._solicitacoes.salvar_normalizadas(normalizadas)
        self._correcoes.substituir(REGRAS_NORMALIZACAO, log)
        return ResumoNormalizacao(
            solicitacoes=len(normalizadas),
            correcoes=len(log),
            por_regra=dict(Counter(c.regra for c in log)),
        )
