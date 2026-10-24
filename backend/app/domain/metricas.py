"""US-22 · Métricas "antes × depois". Python puro: sem I/O, sem relógio (a data de referência vem de fora)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median

from app.domain.cid import is_cid_urgente
from app.domain.models import Evento, Solicitacao
from app.domain.preprocessing.normalizacao import normalizar_prioridade
from app.domain.urgencia import _KW_ALARME, evento_e_piora

JANELA_PS_DIAS = 180
_RANK_PRIORIDADE = {"alta": 0, "media": 1, "baixa": 2}


def is_sem_urgencia_verificador(solicitacao: Solicitacao, eventos: list[Evento]) -> bool:
    """'Sem urgência clínica' exatamente como o verificador oficial define.

    Considera eventos de qualquer data (inclusive histórico e duplicados), como o verificador.
    """
    if solicitacao.oncologico or is_cid_urgente(solicitacao.cid_norm or solicitacao.cid_principal):
        return False
    if (solicitacao.intensidade_dor_eva or 0) > 3:
        return False
    if (solicitacao.limitacao_funcional or "nenhuma") not in ("nenhuma", "leve"):
        return False
    if any(evento_e_piora(e.tipo_evento, e.resultado) for e in eventos):
        return False
    # Espelho do verificador: termo de alarme SEM negação (a fila usa negação, D-122; o verificador não).
    return not _KW_ALARME.search((solicitacao.justificativa_clinica or "").lower())


def _rank_prioridade(s: Solicitacao) -> int:
    chave = s.prioridade_norm or normalizar_prioridade(s.prioridade_regulacao)
    return _RANK_PRIORIDADE.get(chave or "", 3)


def ordem_atual(solicitacoes: list[Solicitacao]) -> list[str]:
    """Ordem 'antes': prioridade manual (alta, média, baixa, vazio), entrada mais antiga, id."""
    ordenadas = sorted(solicitacoes,
                       key=lambda s: (_rank_prioridade(s), s.data_entrada_fila, s.solicitacao_id))
    return [s.solicitacao_id for s in ordenadas]


def com_ps_recente(eventos_por_solicitacao: dict[str, list[Evento]], ref_date: date) -> set[str]:
    """Solicitações com pronto-socorro ou internação nos últimos 180 dias até a ref_date."""
    limite = ref_date - timedelta(days=JANELA_PS_DIAS)
    return {
        sid for sid, evs in eventos_por_solicitacao.items()
        if any(e.tipo_evento in ("pronto_socorro", "internacao") and e.data_evento >= limite
               for e in evs)
    }


@dataclass
class IndicadoresFila:
    total: int
    violacoes_regra_ouro: int
    posicao_mediana_oncologicos: float | None
    pct_oncologicos_primeiro_terco: float
    pct_ps_recente_primeira_metade: float
    pct_sem_urgencia_ultimo_terco: float


def _pct(parte: int, todo: int) -> float:
    return round(100.0 * parte / todo, 1) if todo else 0.0


def calcular_indicadores(ordem: list[str], oncologicos: set[str], sem_urgencia: set[str],
                         ps_recente: set[str]) -> IndicadoresFila:
    n = len(ordem)
    pos = {sid: i for i, sid in enumerate(ordem, start=1)}
    pos_onco = sorted(pos[s] for s in oncologicos if s in pos)
    pos_calmos = [pos[s] for s in sem_urgencia if s in pos]
    pos_ps = [pos[s] for s in ps_recente if s in pos]
    violacoes = 0
    if pos_calmos:
        primeiro = min(pos_calmos)
        violacoes = sum(1 for p in pos_onco if p > primeiro)
    mediana = float(median(pos_onco)) if pos_onco else None
    return IndicadoresFila(
        total=n,
        violacoes_regra_ouro=violacoes,
        posicao_mediana_oncologicos=mediana,
        pct_oncologicos_primeiro_terco=_pct(sum(1 for p in pos_onco if p <= n / 3), len(pos_onco)),
        pct_ps_recente_primeira_metade=_pct(sum(1 for p in pos_ps if p <= n / 2), len(pos_ps)),
        pct_sem_urgencia_ultimo_terco=_pct(sum(1 for p in pos_calmos if p > 2 * n / 3),
                                           len(pos_calmos)),
    )
