"""US-17 · Recontato de quem está sem eventos (C-04, I-08): silêncio não é estabilidade. Puro.

Conta os dias desde o último evento (ou desde a entrada na fila, se não houve nenhum). Passou de N, vira
uma pendência não bloqueante para a equipe ligar ou mandar o ACS. Não mexe em classe, score nem posição.
"""
from __future__ import annotations

from datetime import date

from app.domain.models import Achado, Evento, Motivo, Solicitacao

REC_SEM_EVENTO = "REC-01"


def ultimo_evento_em(eventos: list[Evento], hoje: date) -> date | None:
    """Último evento que conta: não é duplicado nem órfão, e não é do futuro (relógio simulado, US-16)."""
    datas = [e.data_evento for e in eventos if e.duplicado_de is None and not e.orfao and e.data_evento <= hoje]
    return max(datas, default=None)


def dias_sem_evento(s: Solicitacao, eventos: list[Evento], hoje: date) -> tuple[int, date, str]:
    """(dias, data de referência, de onde veio): o último evento ou, sem ele, a entrada na fila."""
    ultimo = ultimo_evento_em(eventos, hoje)
    if ultimo is not None and ultimo >= s.data_entrada_fila:
        return (hoje - ultimo).days, ultimo, "último evento"
    return (hoje - s.data_entrada_fila).days, s.data_entrada_fila, "entrada na fila"


def detectar_recontato(s: Solicitacao, eventos: list[Evento], hoje: date, n_dias: int) -> Achado | None:
    dias, desde, origem = dias_sem_evento(s, eventos, hoje)
    if dias < n_dias:
        return None
    texto = (f"Sem evento há {dias} dias (desde o {origem}, {desde:%d/%m/%Y}); o limite é {n_dias}. "
             "Silêncio não é estabilidade: pode ser atendimento em outro serviço, barreira de acesso, "
             "telefone desatualizado, desistência ou óbito.")
    return Achado(
        regra=REC_SEM_EVENTO, bloqueante=False, titulo=f"Sem evento há {dias} dias",
        evidencias=[Motivo("sem_evento", texto, "solicitacao", ref=s.solicitacao_id, data=desde)],
        acao_sugerida="Ligar ou pedir visita do ACS; registrar o retorno como evento")
