"""Portas (interfaces) que a camada de aplicação usa. Implementações ficam em infrastructure/.

Regra de dependência: domain não importa nada de application, infrastructure ou api.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from app.domain.fatores import CelulaIrr
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
from app.domain.swalis import SinalTexto


class SolicitacaoRepository(Protocol):
    def obter(self, solicitacao_id: str) -> Solicitacao | None: ...
    def listar(self, apenas_ativas: bool = True) -> list[Solicitacao]: ...
    def salvar(self, solicitacao: Solicitacao) -> None: ...
    def salvar_varias(self, solicitacoes: list[Solicitacao]) -> None: ...
    def salvar_normalizadas(self, solicitacoes: list[Solicitacao]) -> None:
        """Grava só as colunas *_norm (US-02). Colunas originais e estado não são tocados."""
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
        """Grava só `duplicado_de` e `historico` (US-03); nenhum evento é apagado."""
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
    def listar_por_solicitacao(self, solicitacao_id: str) -> list[Pendencia]:
        """Todas as pendências da solicitação, de qualquer status (US-21), por aberta_em."""
        ...
    def salvar(self, pendencia: Pendencia) -> None: ...
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
                         publicada_em: datetime, data_referencia: date) -> None: ...
    def obter_publicada(self) -> list[LinhaFila]: ...
    def publicada_em(self) -> datetime | None: ...
    def data_referencia(self) -> date | None: ...


class SwalisScorer(Protocol):
    """Contrato do SWALIS (C-07). Implementação: SwalisRegras (infrastructure/swalis_regras.py)."""

    versao_regras: str

    def calcular(self, solicitacao: Solicitacao, eventos: list[Evento]) -> ResultadoScore: ...


class TabelaIrr(Protocol):
    """Tabela nacional de mortalidade SIM/IBGE por CID-3 × faixa etária (domain/fatores.py)."""

    def consultar(self, cid_3: str, faixa_idade: str) -> CelulaIrr | None: ...


class ExtratorSinais(Protocol):
    """Extrai sinais de alarme do texto clínico citando o trecho (ex.: LLM). Nunca decide classe (I-05)."""

    def extrair(self, texto: str, fonte: str) -> list[SinalTexto]: ...


class VerificadorFila(Protocol):
    def verificar(self, caminho_csv: Path) -> tuple[bool, str]:
        """Retorna (passou, saída do verificador)."""
        ...
