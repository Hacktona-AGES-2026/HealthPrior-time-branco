"""Importar novas solicitações por CSV (uma linha ou várias).

Valida tudo antes de gravar (tudo ou nada) e segue o mesmo caminho da carga inicial: normalização, flags,
inconsistências e bloqueantes, na mesma transação; só então republica a fila (I-07). A solicitação que já
existe é ignorada, nunca sobrescrita (I-10). A classe sugerida de uma entrada nova passa pelo inbox como qualquer
outra (C-08). Não mexe em procedimentos nem em eventos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from app.domain.enums import StatusFila
from app.domain.importacao import ErroLinha, LeituraCsv
from app.domain.ports import ProcedimentoRepository, SolicitacaoRepository


@dataclass
class ResultadoImportacao:
    lidas: int = 0
    novas: int = 0
    ja_existentes: list[str] = field(default_factory=list)
    erros: list[ErroLinha] = field(default_factory=list)
    novas_ids: list[str] = field(default_factory=list)
    suspensas: int = 0  # entraram já com pendência bloqueante (PRE-20..25)
    fila_publicada: bool | None = None  # None: não republicou (nada novo, ou `publicar=False`)
    total_fila: int | None = None


class ImportarSolicitacoes:
    def __init__(self, solicitacoes: SolicitacaoRepository, procedimentos: ProcedimentoRepository,
                 ler: Callable[[str, dict, date], LeituraCsv],
                 gravar: Callable[[list[dict]], None], publicar: Callable[[], object], hoje: date):
        # `ler` e `gravar` vêm da infraestrutura: leitura do CSV e a carga em si (mesma transação).
        self._solicitacoes, self._procedimentos = solicitacoes, procedimentos
        self._ler, self._gravar, self._publicar, self._hoje = ler, gravar, publicar, hoje

    def executar(self, texto: str, publicar: bool = True) -> ResultadoImportacao:
        leitura = self._ler(texto, self._procedimentos.mapa(), self._hoje)
        r = ResultadoImportacao(lidas=leitura.lidas, erros=list(leitura.erros))
        if r.erros:
            return r  # tudo ou nada: nada foi gravado
        existentes = {s.solicitacao_id for s in self._solicitacoes.listar(apenas_ativas=False)}
        novas = [x for x in leitura.registros if x["solicitacao_id"] not in existentes]
        r.ja_existentes = sorted(x["solicitacao_id"] for x in leitura.registros if x["solicitacao_id"] in existentes)
        if not novas:
            return r
        self._gravar(novas)
        r.novas = len(novas)
        r.novas_ids = [x["solicitacao_id"] for x in novas][:50]
        for x in novas:
            s = self._solicitacoes.obter(x["solicitacao_id"])
            r.suspensas += bool(s and s.status_fila == StatusFila.SUSPENSA)
        if publicar:
            try:
                res = self._publicar()
                r.fila_publicada, r.total_fila = res.publicada, res.total
            except Exception:  # a importação já valeu; a fila anterior segue publicada
                r.fila_publicada = False
        return r
