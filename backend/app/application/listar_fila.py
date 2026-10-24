"""US-20 · GET /fila: lê a fila publicada, junta cada linha à solicitação e pagina.

Só leitura: a ordem e a classe vêm da publicação (US-10); nenhuma regra de ranking aqui.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.enums import ClasseStatus
from app.domain.models import LinhaFila, Solicitacao
from app.domain.ports import FilaRepository, SolicitacaoRepository

PAGE_SIZE_MAXIMO = 200


@dataclass
class FiltroFila:
    camada: int | None = None
    procedimento_id: str | None = None
    especialidade: str | None = None
    busca: str | None = None
    page: int = 1
    page_size: int = 50


@dataclass
class ItemFilaVisao:
    posicao: int
    solicitacao_id: str
    camada: int
    classe: str
    classe_status: ClasseStatus
    pct_prazo_consumido: float
    dias_em_fila: int
    procedimento: str
    especialidade: str
    cid: str
    oncologico: bool
    editado_manualmente: bool
    alertas: list[str] = field(default_factory=list)
    resumo_justificativa: str = ""


@dataclass
class PaginaFila:
    versao_regras: str | None
    gerada_em: datetime | None
    publicada: bool
    total: int
    itens: list[ItemFilaVisao]


class ListarFila:
    def __init__(self, fila: FilaRepository, solicitacoes: SolicitacaoRepository):
        self._fila = fila
        self._solicitacoes = solicitacoes

    def executar(self, filtro: FiltroFila) -> PaginaFila:
        if filtro.page < 1 or filtro.page_size < 1:
            raise ValueError("page e page_size devem ser maiores ou iguais a 1")
        tamanho = min(filtro.page_size, PAGE_SIZE_MAXIMO)

        linhas = sorted(self._fila.obter_publicada(), key=lambda l: l.posicao)
        gerada_em = self._fila.publicada_em()
        if gerada_em is None and not linhas:
            return PaginaFila(None, None, False, 0, [])

        por_id = {s.solicitacao_id: s
                  for s in self._solicitacoes.listar(apenas_ativas=False)}
        pares = [(l, por_id[l.solicitacao_id]) for l in linhas
                 if l.solicitacao_id in por_id]

        filtrados = [(l, s) for l, s in pares if _casa(l, s, filtro)]
        inicio = (filtro.page - 1) * tamanho
        fatia = filtrados[inicio:inicio + tamanho]

        return PaginaFila(
            versao_regras=linhas[0].versao_regras if linhas else None,
            gerada_em=gerada_em,
            publicada=True,
            total=len(filtrados),
            itens=[_visao(l, s) for l, s in fatia],
        )


def _casa(linha: LinhaFila, s: Solicitacao, filtro: FiltroFila) -> bool:
    if filtro.camada is not None and linha.camada != filtro.camada:
        return False
    if filtro.procedimento_id is not None and s.procedimento_id != filtro.procedimento_id:
        return False
    if filtro.especialidade is not None and \
            (s.especialidade or "").casefold() != filtro.especialidade.casefold():
        return False
    if filtro.busca is not None:
        termo = filtro.busca.casefold()
        if termo not in s.solicitacao_id.casefold() and termo not in s.paciente_id.casefold():
            return False
    return True


def _visao(linha: LinhaFila, s: Solicitacao) -> ItemFilaVisao:
    return ItemFilaVisao(
        posicao=linha.posicao,
        solicitacao_id=linha.solicitacao_id,
        camada=linha.camada,
        classe=linha.classe,
        classe_status=s.classe_status,
        pct_prazo_consumido=linha.pct_prazo_consumido,
        dias_em_fila=linha.dias_em_fila,
        procedimento=s.procedimento or "",
        especialidade=s.especialidade or "",
        cid=s.cid_principal,
        oncologico=s.oncologico,
        editado_manualmente=linha.editado_manualmente,
        alertas=list(s.alertas),
        resumo_justificativa=linha.justificativa,
    )
