"""SWALIS por regras (SW-01..SW-04): implementa o contrato C-07 (`SwalisScorer`).

Sinais do texto: palavra-chave com negação (mudam a classe) + LLM opcional (só alertas, I-05).
O score dentro da classe continua sendo o % do prazo consumido, como no stub.
"""
from __future__ import annotations

from datetime import date

from app.config import settings
from app.domain.enums import PRAZO_MAXIMO_DIAS
from app.domain.models import Evento, Motivo, ResultadoScore, Solicitacao
from app.domain.ports import ExtratorSinais
from app.domain.swalis import (
    VERSAO_REGRAS,
    ClassificacaoSwalis,
    SinalTexto,
    classificar,
    alerta_redundante,
    coberto_por_palavra_chave,
    sinais_por_palavra_chave,
    validar_sinal_llm,
)

_FONTES = ("justificativa_clinica", "observacoes")


class SwalisRegras:
    def __init__(self, extrator: ExtratorSinais | None = None, ref_date: date | None = None):
        self.extrator = extrator
        self._ref = ref_date or settings.ref_date
        modelo = getattr(extrator, "modelo", None)
        self.versao_regras = f"{VERSAO_REGRAS}+llm:{modelo}" if modelo else VERSAO_REGRAS

    def sinais(self, solicitacao: Solicitacao) -> list[SinalTexto]:
        sinais: list[SinalTexto] = []
        for fonte in _FONTES:
            texto = getattr(solicitacao, fonte) or ""
            sinais += sinais_por_palavra_chave(texto, fonte)
            if self.extrator:
                # Só o que a palavra-chave não pegou, com trecho literal e não negado.
                sinais += [s for s in self.extrator.extrair(texto, fonte)
                           if validar_sinal_llm(s, texto) and not coberto_por_palavra_chave(s)
                           and not alerta_redundante(s, solicitacao.cid_principal)]
        return sinais

    def classificar(self, solicitacao: Solicitacao, eventos: list[Evento]) -> ClassificacaoSwalis:
        return classificar(solicitacao.cid_principal, solicitacao.intensidade_dor_eva,
                           solicitacao.limitacao_funcional, eventos, self.sinais(solicitacao))

    def alertas_llm(self, solicitacao: Solicitacao) -> list[SinalTexto]:
        return [s for s in self.sinais(solicitacao) if s.origem == "llm"]

    def calcular(self, solicitacao: Solicitacao, eventos: list[Evento]) -> ResultadoScore:
        sinais = self.sinais(solicitacao)
        c = classificar(solicitacao.cid_principal, solicitacao.intensidade_dor_eva,
                        solicitacao.limitacao_funcional, eventos, sinais)
        prazo = PRAZO_MAXIMO_DIAS[c.classe]
        pct = round(100 * (self._ref - solicitacao.data_entrada_fila).days / prazo, 1)
        motivos = [Motivo("eixo_progressao", f"progressão {c.progressao.nivel}: "
                          + "; ".join(c.progressao.motivos), "regra"),
                   Motivo("eixo_sintoma", f"sintoma {c.sintoma.nivel}: "
                          + "; ".join(c.sintoma.motivos), "regra")]
        motivos += [Motivo(s.categoria.value, s.trecho, s.fonte) for s in c.sinais]
        # Alertas do LLM: o regulador vê o trecho; a classe não muda por eles.
        motivos += [Motivo(f"alerta_llm:{s.categoria.value}", s.trecho, s.fonte)
                    for s in sinais if s.origem == "llm"]
        return ResultadoScore(c.classe, prazo, pct, pct, motivos, self.versao_regras)


def criar_swalis(apenas_cache: bool = True) -> SwalisRegras:
    """Composição a partir da configuração: LLM se habilitado e houver chave ou cache.

    `apenas_cache=True` (padrão, usado na geração da fila) não chama a rede: a saída é
    reproduzível. Só `extrair-sinais` chama o LLM e congela o cache.
    """
    if settings.llm_enabled and (settings.openrouter_api_key or settings.llm_cache_path.is_file()):
        from app.infrastructure.llm_openrouter import ExtratorSinaisLLM

        return SwalisRegras(ExtratorSinaisLLM(settings.openrouter_api_key, settings.llm_model,
                                              settings.llm_cache_path, apenas_cache=apenas_cache))
    return SwalisRegras()
