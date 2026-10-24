"""Caso de uso: montar a fila priorizada (camadas + score) a partir das solicitações."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Protocol

from app.domain.cid import is_oncologico
from app.domain.enums import PRAZO_MAXIMO_DIAS, Classe, StatusFila
from app.domain.models import Evento, ItemRanking, LinhaFila, ResultadoScore, Solicitacao
from app.domain.ranking import ordenar_fila
from app.domain.urgencia import (
    SinaisUrgencia,
    is_urgente,
    motivos_sintomas,
    motivos_urgencia,
    tem_biopsia_positiva,
    tem_evento_de_piora_na_espera,
)

__all__ = ["LinhaFila", "Scorer", "linhas_para_dicts", "montar_fila", "montar_justificativa"]


class Scorer(Protocol):
    versao_regras: str

    def calcular(self, solicitacao: Solicitacao, eventos: list[Evento]) -> ResultadoScore: ...


def _texto_motivo(codigo: str, sol: Solicitacao) -> str:
    textos = {
        "cid_complicacao": f"CID de complicação {sol.cid_principal}",
        "evento_piora": "evento de piora durante a espera",
        "biopsia_positiva": "biópsia positiva com CID não oncológico — revisar CID",
        "sinal_alarme": "sinal de alarme na justificativa clínica",
        "dor": f"dor EVA {sol.intensidade_dor_eva}",
        "limitacao": f"limitação funcional {sol.limitacao_funcional}",
    }
    return textos[codigo]


def montar_justificativa(
    camada: int,
    solicitacao: Solicitacao,
    motivos: list[str],
    classe: str,
    prazo_dias: int,
    versao_regras: str,
    dias_em_fila: int,
    pct_prazo: float,
    editado_manualmente: bool = False,
    sintomas: list[str] | None = None,
) -> str:
    """Gera a justificativa legível em português para uma linha da fila."""
    if camada == 1:
        base = f"Camada 1: oncológico pelo CID {solicitacao.cid_principal}."
    elif camada == 2:
        lista = "; ".join(_texto_motivo(m, solicitacao) for m in motivos)
        base = f"Camada 2: urgente ({lista})."
    else:
        base = "Camada 3: sem sinais clínicos de urgência."
    if sintomas:
        base += " Sintomas: " + "; ".join(_texto_motivo(s, solicitacao) for s in sintomas) + "."
    texto = (f"{base} Classe {classe} (prazo {prazo_dias} dias, regras {versao_regras}); "
             f"{dias_em_fila} dias em fila, {pct_prazo:g}% do prazo.")
    if editado_manualmente:
        texto += " Editado manualmente pelo regulador."
    return texto


def montar_fila(
    solicitacoes: list[Solicitacao],
    eventos_por_solicitacao: dict[str, list[Evento]],
    scorer: Scorer,
    ref_date: date,
) -> list[LinhaFila]:
    """Calcula score, camada e posição de cada solicitação ativa."""
    contexto: dict[str, tuple[Solicitacao, ResultadoScore, list[str], list[str], float, Classe]] = {}
    itens: list[ItemRanking] = []
    for sol in solicitacoes:
        if sol.status_fila != StatusFila.ATIVA:
            continue
        eventos = eventos_por_solicitacao.get(sol.solicitacao_id, [])
        res = scorer.calcular(sol, eventos)
        score = sol.score_medico if sol.score_medico is not None else res.score_sistema
        classe = sol.classe_medico if sol.classe_medico is not None else res.classe_sistema
        sinais = SinaisUrgencia(
            cid_norm=sol.cid_norm,
            intensidade_dor_eva=sol.intensidade_dor_eva,
            limitacao_funcional=sol.limitacao_funcional,
            tem_evento_de_piora=tem_evento_de_piora_na_espera(eventos, sol.data_entrada_fila),
            justificativa_clinica=sol.justificativa_clinica,
            tem_biopsia_positiva=tem_biopsia_positiva(eventos),
        )
        # I-09: o CID manda. Se o `oncologico` gravado estiver desatualizado (flags não
        # recalculadas), um câncer não pode cair fora da camada 1.
        oncologico = sol.oncologico or is_oncologico(sol.cid_principal)
        itens.append(ItemRanking(sol.solicitacao_id, oncologico, is_urgente(sinais),
                                 score, sol.data_entrada_fila))
        contexto[sol.solicitacao_id] = (sol, res, motivos_urgencia(sinais),
                                        motivos_sintomas(sinais), score, classe)

    linhas: list[LinhaFila] = []
    for item in ordenar_fila(itens):
        sol, res, motivos, sintomas, score, classe = contexto[item.solicitacao_id]
        classe_txt = classe.value if isinstance(classe, Classe) else str(classe)
        prazo = PRAZO_MAXIMO_DIAS[classe] if isinstance(classe, Classe) else res.prazo_dias
        dias = (ref_date - sol.data_entrada_fila).days
        # Classe editada pelo regulador: o % do prazo acompanha o prazo da classe decidida.
        pct = round(100 * dias / prazo, 1) if sol.classe_medico is not None else res.pct_prazo_consumido
        camada = int(item.camada)
        linhas.append(LinhaFila(
            solicitacao_id=sol.solicitacao_id,
            posicao=item.posicao,
            justificativa=montar_justificativa(camada, sol, motivos, classe_txt, prazo,
                                               res.versao_regras, dias,
                                               pct, sol.editado_manualmente,
                                               sintomas=sintomas),
            camada=camada,
            classe=classe_txt,
            pct_prazo_consumido=pct,
            dias_em_fila=dias,
            score_efetivo=score,
            editado_manualmente=sol.editado_manualmente,
            versao_regras=res.versao_regras,
        ))
    return linhas


def linhas_para_dicts(linhas: list[LinhaFila]) -> list[dict]:
    """Converte as linhas para dicts na ordem de colunas esperada pelo exportador."""
    return [asdict(l) for l in linhas]
