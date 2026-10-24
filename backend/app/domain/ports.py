"""Portas (interfaces) que a camada de aplicação usa. Implementações ficam em infrastructure/.

Regra de dependência: domain não importa nada de application, infrastructure ou api.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol

from app.domain.models import (
    Correcao,
    Decisao,
    Evento,
    LinhaFila,
    Pendencia,
    ResultadoScore,
    ResultadoSincronizacao,
    ResultadoTabela,
    Solicitacao,
)


class SolicitacaoRepository(Protocol):
    def obter(self, solicitacao_id: str) -> Solicitacao | None: ...
    def listar(self, apenas_ativas: bool = True) -> list[Solicitacao]: ...
    def salvar(self, solicitacao: Solicitacao) -> None: ...
    def salvar_varias(self, solicitacoes: list[Solicitacao]) -> None: ...
    def salvar_normalizadas(self, solicitacoes: list[Solicitacao]) -> None:
        """Grava só as colunas *_norm (US-02). Colunas originais e estado não são tocados."""
        ...
    def atualizar_status(self, solicitacoes: list[Solicitacao]) -> None:
        """Grava só `status_fila` e `motivo_status` (US-04); nenhuma coluna original muda."""
        ...
    def salvar_alertas(self, solicitacoes: list[Solicitacao]) -> None:
        """Grava só `alertas` (US-05); nenhuma coluna original muda."""
        ...
    def atualizar_flags(self, solicitacoes: list[Solicitacao]) -> None:
        """Grava só `oncologico` e `piora_recalculada` (US-03); nenhuma coluna original muda."""
        ...


class EventoRepository(Protocol):
    def listar_por_solicitacao(self, solicitacao_id: str) -> list[Evento]: ...
    def listar_todos(self) -> list[Evento]: ...
    def adicionar(self, evento: Evento) -> None: ...
    def salvar_varios(self, eventos: list[Evento]) -> None: ...
    def atualizar_marcas(self, eventos: list[Evento]) -> None:
        """Grava só `duplicado_de`, `historico` e `orfao` (US-03/04); nenhum evento é apagado."""
        ...


class UnidadeDeTrabalho(Protocol):
    """Transação compartilhada pelos repositórios: os casos de uso decidem quando confirmar."""

    def confirmar(self) -> None: ...
    def desfazer(self) -> None: ...


class CargaRepository(Protocol):
    def gravar(self, procedimentos: list[dict], solicitacoes: list[dict],
               eventos: list[dict]) -> dict[str, ResultadoTabela]:
        """Upsert por chave primária numa única transação: ou entra tudo, ou nada.

        Não confirma: quem chama usa a UnidadeDeTrabalho. Só as colunas originais do dataset
        são gravadas; o estado do sistema (classe_status, status_fila, *_norm…) não é sobrescrito.
        """
        ...


class PendenciaRepository(Protocol):
    def obter(self, pendencia_id: str) -> Pendencia | None: ...
    def listar(self, bloqueante: bool | None = None, regra: str | None = None,
               status: str | None = "aberta") -> list[Pendencia]: ...
    def salvar(self, pendencia: Pendencia) -> None: ...
    def chaves_abertas(self, regras: tuple[str, ...]) -> set[tuple[str, str]]:
        """(solicitacao_id, regra) das pendências abertas dessas `regras`."""
        ...
    def sincronizar(self, regras: tuple[str, ...], pendencias: list[Pendencia]) -> ResultadoSincronizacao:
        """Mantém as pendências automáticas dessas `regras` iguais às `pendencias` detectadas.

        Uma por (solicitação, regra). Abre as que faltam; atualiza a evidência das abertas; encerra
        (resolvida, por "sistema") as abertas que deixaram de valer. Nunca reabre nem altera as que
        uma pessoa já resolveu ou descartou, e nunca apaga.
        """
        ...


class DecisaoRepository(Protocol):
    def adicionar(self, decisao: Decisao) -> None: ...
    def listar_por_solicitacao(self, solicitacao_id: str) -> list[Decisao]: ...


class CorrecaoRepository(Protocol):
    def adicionar_varias(self, correcoes: list[Correcao]) -> None: ...
    def listar_por_solicitacao(self, solicitacao_id: str) -> list[Correcao]: ...
    def substituir(self, regras: tuple[str, ...], correcoes: list[Correcao]) -> None:
        """Apaga o log das `regras` e grava `correcoes`; o log de outras regras fica intacto."""
        ...


class FilaRepository(Protocol):
    def salvar_publicada(self, linhas: list[LinhaFila], versao_regras: str,
                         publicada_em: datetime) -> None: ...
    def obter_publicada(self) -> list[LinhaFila]: ...
    def publicada_em(self) -> datetime | None: ...


class SwalisScorer(Protocol):
    """Contrato do SWALIS (C-07). Implementação real virá do time do SWALIS; até lá, SwalisStub."""

    versao_regras: str

    def calcular(self, solicitacao: Solicitacao, eventos: list[Evento]) -> ResultadoScore: ...


class VerificadorFila(Protocol):
    def verificar(self, caminho_csv: Path) -> tuple[bool, str]:
        """Retorna (passou, saída do verificador)."""
        ...
