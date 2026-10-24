"""Portas (interfaces) que a camada de aplicação usa. Implementações ficam em infrastructure/.

Regra de dependência: domain não importa nada de application, infrastructure ou api.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.domain.models import (
    Correcao,
    Decisao,
    Evento,
    ItemFila,
    Pendencia,
    ResultadoScore,
    ResultadoTabela,
    Solicitacao,
)


class SolicitacaoRepository(Protocol):
    def obter(self, solicitacao_id: str) -> Solicitacao | None: ...
    def listar(self, apenas_ativas: bool = True) -> list[Solicitacao]: ...
    def salvar(self, solicitacao: Solicitacao) -> None: ...
    def salvar_varias(self, solicitacoes: list[Solicitacao]) -> None: ...


class EventoRepository(Protocol):
    def listar_por_solicitacao(self, solicitacao_id: str) -> list[Evento]: ...
    def listar_todos(self) -> list[Evento]: ...
    def adicionar(self, evento: Evento) -> None: ...
    def salvar_varios(self, eventos: list[Evento]) -> None: ...


class CargaRepository(Protocol):
    def gravar(self, procedimentos: list[dict], solicitacoes: list[dict],
               eventos: list[dict]) -> dict[str, ResultadoTabela]:
        """Upsert por chave primária numa única transação: ou entra tudo, ou nada.

        Só as colunas originais do dataset são gravadas; o estado do sistema
        (classe_status, status_fila…) nunca é sobrescrito numa recarga.
        """
        ...


class PendenciaRepository(Protocol):
    def obter(self, pendencia_id: str) -> Pendencia | None: ...
    def listar(self, bloqueante: bool | None = None, regra: str | None = None,
               status: str | None = "aberta") -> list[Pendencia]: ...
    def salvar(self, pendencia: Pendencia) -> None: ...


class DecisaoRepository(Protocol):
    def adicionar(self, decisao: Decisao) -> None: ...
    def listar_por_solicitacao(self, solicitacao_id: str) -> list[Decisao]: ...


class CorrecaoRepository(Protocol):
    def adicionar_varias(self, correcoes: list[Correcao]) -> None: ...
    def listar_por_solicitacao(self, solicitacao_id: str) -> list[Correcao]: ...


class FilaRepository(Protocol):
    def salvar_publicada(self, itens: list[ItemFila], versao_regras: str) -> None: ...
    def obter_publicada(self) -> list[ItemFila]: ...


class SwalisScorer(Protocol):
    """Contrato do SWALIS (C-07). Implementação real virá do time do SWALIS; até lá, SwalisStub."""

    versao_regras: str

    def calcular(self, solicitacao: Solicitacao, eventos: list[Evento]) -> ResultadoScore: ...


class VerificadorFila(Protocol):
    def verificar(self, caminho_csv: Path) -> tuple[bool, str]:
        """Retorna (passou, saída do verificador)."""
        ...
