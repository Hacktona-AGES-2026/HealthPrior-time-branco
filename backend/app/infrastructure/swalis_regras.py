"""SWALIS por pontos + regras (SW-01..SW-04): implementa o contrato C-07 (`SwalisScorer`).

Pontos do texto: palavra-chave com negação + Jev (frase citada, validada no domínio). As regras
de `domain/swalis.py` cruzam os pontos e decidem a classe; cada motivo diz de onde veio.
O score dentro da classe é o % do prazo consumido × fatores de comorbidade e idade/IRR
(domain/fatores.py), quando a tabela de IRR está disponível.
"""
from __future__ import annotations

from datetime import date

from app.config import settings
from app.domain.enums import PRAZO_MAXIMO_DIAS
from app.domain.fatores import calcular_fatores, chave_irr
from app.domain.models import Evento, Motivo, ResultadoScore, Solicitacao
from app.domain.ports import ExtratorSinais, TabelaIrr
from app.domain.swalis import (
    VERSAO_REGRAS,
    ClassificacaoSwalis,
    SinalTexto,
    classificar,
    sinais_por_palavra_chave,
    validar_sinal_llm,
)
from app.infrastructure.tabela_irr import TabelaIrrCsv

_FONTES = ("justificativa_clinica", "observacoes")
VERSAO_FATORES = "fatores-1"


class SwalisRegras:
    def __init__(self, extrator: ExtratorSinais | None = None, ref_date: date | None = None,
                 tabela_irr: TabelaIrr | None = None):
        self.extrator = extrator
        self._ref = ref_date or settings.ref_date
        # Com a tabela, o score ganha os fatores de comorbidade e idade (domain/fatores.py).
        self.tabela_irr = tabela_irr
        modelo = getattr(extrator, "modelo", None)
        self.versao_regras = f"{VERSAO_REGRAS}+llm:{modelo}" if modelo else VERSAO_REGRAS
        if tabela_irr is not None:
            self.versao_regras += f"+{VERSAO_FATORES}"

    def sinais(self, solicitacao: Solicitacao) -> list[SinalTexto]:
        sinais: list[SinalTexto] = []
        for fonte in _FONTES:
            texto = getattr(solicitacao, fonte) or ""
            sinais += sinais_por_palavra_chave(texto, fonte)
            if self.extrator:
                # Frase literal e não negada (o Jev já diz "nenhum" para negação; checamos de novo).
                sinais += [s for s in self.extrator.extrair(texto, fonte) if validar_sinal_llm(s, texto)]
        return sinais

    def classificar(self, solicitacao: Solicitacao, eventos: list[Evento]) -> ClassificacaoSwalis:
        return classificar(solicitacao.cid_principal, solicitacao.intensidade_dor_eva,
                           solicitacao.limitacao_funcional, eventos, self.sinais(solicitacao))

    def pontos_llm(self, solicitacao: Solicitacao) -> list[SinalTexto]:
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
        # Trilha de auditoria: todos os pontos achados, com origem (palavra-chave ou Jev p=…).
        motivos += [Motivo(f"ponto:{s.categoria.value}:{s.origem}", s.trecho, s.fonte,
                           ref=f"{s.confianca:.2f}") for s in c.sinais]
        # Pontos incertos do Jev: não mudam a classe, vão para o regulador revisar.
        motivos += [Motivo(f"revisar:{s.categoria.value}", s.trecho, s.fonte, ref=f"{s.confianca:.2f}")
                    for s in c.revisar]
        fator = 1.0
        if self.tabela_irr is not None:
            chave = chave_irr(solicitacao.cid_principal, solicitacao.idade)
            f = calcular_fatores(solicitacao.cid_principal, solicitacao.idade,
                                 solicitacao.comorbidades, solicitacao.cid_secundario,
                                 self.tabela_irr.consultar(*chave) if chave else None)
            fator = f.valor
            motivos += [Motivo("fator_comorbidade", f.comorbidade.descricao, "regra",
                               ref=f"{f.comorbidade.valor:.2f}"),
                        Motivo("fator_idade", f.idade.descricao, "regra", ref=f"{f.idade.valor:.3f}")]
        return ResultadoScore(c.classe, prazo, pct, round(pct * fator, 1), motivos,
                              self.versao_regras, fator)


def criar_swalis(apenas_cache: bool = True, ref_date: date | None = None) -> SwalisRegras:
    """Composição a partir da configuração: LLM se habilitado e houver chave ou cache.

    `apenas_cache=True` (padrão, usado na geração da fila) não chama a rede: a saída é
    reproduzível. Só `extrair-sinais` chama o LLM e congela o cache.
    `ref_date` é a data do % do prazo (padrão `HP_REF_DATE`); a atualização diária (US-16)
    passa a mesma data que dá ao `GerarFila`.
    """
    tabela = (TabelaIrrCsv(settings.irr_path)
              if settings.fatores_enabled and settings.irr_path.is_file() else None)
    if settings.llm_enabled and (settings.openrouter_api_key or settings.llm_cache_path.is_file()):
        from app.infrastructure.llm_openrouter import ExtratorSinaisLLM

        return SwalisRegras(ExtratorSinaisLLM(settings.openrouter_api_key, settings.llm_model,
                                              settings.llm_cache_path, apenas_cache=apenas_cache),
                            ref_date, tabela)
    return SwalisRegras(ref_date=ref_date, tabela_irr=tabela)
