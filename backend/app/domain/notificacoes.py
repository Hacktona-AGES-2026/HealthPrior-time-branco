"""Notificações ao paciente (demo): o que dizer e quando vale a pena avisar. Funções puras.

Texto genérico de propósito: nada de classe, score ou posição exata (dado interno, e a classe só vale depois
de confirmada por um profissional, I-04). Posição só em "subiu" ou "desceu".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

POSICAO = "posicao"
SITUACAO = "situacao"
RECONTATO = "recontato"

PENDENTE, ENVIADA, FALHOU = "pendente", "enviada", "falhou"


@dataclass
class Notificacao:
    notificacao_id: str
    solicitacao_id: str
    motivo: str  # posicao | situacao | recontato
    texto: str
    canal: str  # simulado | twilio
    status: str = PENDENTE
    criada_em: datetime | None = None
    enviada_em: datetime | None = None
    tentativas: int = 0
    detalhe: str | None = None  # id externo (Twilio) ou o erro


def texto(motivo: str, solicitacao_id: str, subiu: bool | None = None) -> str:
    """Mensagem de demonstração: o prefixo diz de qual paciente seria (o destino real é o número da demo)."""
    prefixo = f"[DEMO {solicitacao_id}] HealthPrior: "
    if motivo == POSICAO:
        movimento = "subiu" if subiu else "desceu"
        return f"{prefixo}sua posicao na fila cirurgica mudou ({movimento}). Detalhes na unidade de saude."
    if motivo == SITUACAO:
        return f"{prefixo}sua situacao na fila cirurgica foi atualizada. Procure a unidade de saude."
    if motivo == RECONTATO:
        return f"{prefixo}faz tempo que nao temos noticias suas. Entre em contato com a unidade de saude."
    raise ValueError(f"motivo desconhecido: {motivo}")


def mudancas_de_posicao(antes: dict[str, int], depois: dict[str, int], minimo: int,
                        maximo: int) -> list[tuple[str, bool]]:
    """(solicitacao_id, subiu) de quem mudou `minimo` posições ou mais, as maiores mudanças primeiro, até `maximo`.

    Só quem estava nas duas filas: quem entrou ou saiu tem outro motivo (situação). Posição 1 é a melhor.
    """
    mudou = [(sid, depois[sid] - antes[sid]) for sid in antes if sid in depois
             and abs(depois[sid] - antes[sid]) >= minimo]
    mudou.sort(key=lambda par: (-abs(par[1]), par[0]))
    return [(sid, delta < 0) for sid, delta in mudou[:maximo]]
