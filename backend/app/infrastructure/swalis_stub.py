"""SWALIS provisório (placeholder do contrato C-07) enquanto o SWALIS real não fica pronto.

NÃO é regra clínica: classe vem da prioridade manual normalizada e o score é o % do prazo.
Serve para destravar a trava (US-08), a entrega e o front. Troque pela implementação real
sem mudar quem consome (mesmo Protocol `SwalisScorer`).
"""
from __future__ import annotations

from datetime import date

from app.config import settings
from app.domain.enums import PRAZO_MAXIMO_DIAS, Classe
from app.domain.models import Evento, Motivo, ResultadoScore, Solicitacao

_CLASSE_POR_PRIORIDADE = {"alta": Classe.B, "media": Classe.C, "baixa": Classe.D}


class SwalisStub:
    versao_regras = "stub-0"

    def __init__(self, ref_date: date | None = None):
        self._ref = ref_date or settings.ref_date

    def calcular(self, solicitacao: Solicitacao, eventos: list[Evento]) -> ResultadoScore:
        classe = _CLASSE_POR_PRIORIDADE.get(solicitacao.prioridade_norm or "", Classe.D)
        if solicitacao.oncologico:
            classe = Classe.A2
        prazo = PRAZO_MAXIMO_DIAS[classe]
        dias = (self._ref - solicitacao.data_entrada_fila).days
        pct = round(100 * dias / prazo, 1)
        return ResultadoScore(
            classe_sistema=classe,
            prazo_dias=prazo,
            pct_prazo_consumido=pct,
            score_sistema=pct,
            motivos=[Motivo(sinal="stub", evidencia="Classe provisória (SWALIS stub)", fonte="stub")],
            versao_regras=self.versao_regras,
        )
